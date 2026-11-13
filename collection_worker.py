"""Background worker: collection, previews and finalization outlive browser windows."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
import os
from pathlib import Path
import sys
import threading
import time
from zoneinfo import ZoneInfo

import cloud_store
from collection_jobs import read_json, write_json
from property_previews import chave_anuncio, buscar_metadados_preview

TZ = ZoneInfo('America/Sao_Paulo')


class Progress:
    def __init__(self, path, state):
        self.path, self.state = Path(path), state
        self.lines = deque(state.get('log', []), maxlen=500)
        self.lock = threading.RLock()
        self.partial = False
        self.pending = ''
        self.last_save = 0

    def write(self, text):
        with self.lock:
            self.pending += text
            while '\n' in self.pending:
                line, self.pending = self.pending.split('\n', 1)
                if line:
                    self.partial |= '[COLETA_PARCIAL]' in line or 'coleta parcial' in line.lower() or 'Coletores com falha:' in line
                    self.lines.append(f'[{datetime.now(TZ):%H:%M:%S}] {line}')
            if time.monotonic() - self.last_save > 1:
                self.save()
        return len(text)

    def flush(self):
        pass

    def save(self, **values):
        with self.lock:
            self.state.update(values, log=list(self.lines), heartbeat=time.time())
            write_json(self.path, self.state)
            self.last_save = time.monotonic()


def enrich(root, before, progress):
    catalogue = cloud_store.read_catalogue(root / 'geral.json')
    selected = [item for item in catalogue if chave_anuncio(item) not in before
                and item.get('link', '').startswith(('https://', 'http://'))]
    if not selected:
        return
    progress.save(status='enriching')
    print(f'Buscando fotos e descrições de {len(selected)} anúncio(s)…')
    changed = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        tasks = {executor.submit(buscar_metadados_preview, item['link']): item for item in selected}
        for index, task in enumerate(as_completed(tasks), 1):
            item = tasks[task]
            try:
                metadata = task.result() or {}
                item.update(preview_titulo=metadata.get('titulo', ''), descricao=metadata.get('descricao', ''),
                            imagem=metadata.get('imagem', ''), imagem_validada=bool(metadata.get('imagem_validada')),
                            preview_consultado=metadata.get('consultado') or datetime.now(TZ).isoformat())
                changed.append(item)
            except Exception as error:
                print(f'[COLETA_PARCIAL] Foto de um anúncio: {error}')
            if index % 5 == 0 or index == len(selected):
                # Local storage replaces the list; cloud storage upserts only changes.
                import database
                cloud_store.save_catalogue(changed if database.is_cloud() else catalogue, root / 'geral.json')
                print(f'[FOTOS] Consultados {index} de {len(selected)} anúncio(s).')


def collect(state):
    import runner
    if state['tipo'] == 'all':
        return runner.main()
    failures = []
    runner._run_collector('catalog_collectors' if state['tipo'] == 'catalog' else state['identificador'],
                          os.environ.copy(), failures,
                          portal=state['identificador'] if state['tipo'] == 'catalog' else None)
    return 1 if failures else 0


def finalize(root, state, before):
    catalogue = cloud_store.read_catalogue(root / 'geral.json')
    new_keys = {chave_anuncio(item) for item in catalogue} - before
    def mark(current):
        visible = new_keys - set(current.get('excluidos', []))
        return {**current, 'novos': sorted(set(current.get('novos', [])) | visible),
                'coletado_em': {**current.get('coletado_em', {}), **{key: state['inicio'] for key in visible}}}
    if new_keys:
        updated = cloud_store.update_json(root / '.anuncios_estado.json', {}, mark)
        if new_keys - set(updated.get('excluidos', [])):
            cloud_store.update_json(root / '.resultados_notificacao.json', {}, lambda current: {**current, 'pendente': True})
    record = {key: state[key] for key in ('id', 'inicio', 'rotulo', 'resultado', 'codigo', 'duracao')}
    record['log'] = state['log'][-120:]
    cloud_store.update_json(root / '.execucoes.json', [], lambda current: (
        [item for item in current if item.get('id') != record['id']] + [record])[-300:])
    return len(new_keys)


def run_job(path, collector=None, enricher=None):
    path = Path(path)
    root = path.parent.parent
    state = read_json(path)
    progress = Progress(path, state)
    started = time.monotonic()
    state.update(pid=os.getpid(), inicio=datetime.now(TZ).isoformat(), status='running')
    parameters = state['parametros']
    for name, value in {'FINDIMOB_PRECO_MIN': parameters['preco_min'], 'FINDIMOB_PRECO_MAX': parameters['preco_max'],
                        'FINDIMOB_TIPOS': ','.join(parameters['tipos']), 'FINDIMOB_CIDADES': ','.join(parameters['cidades'])}.items():
        os.environ[name] = str(value)
    stopped = threading.Event()
    def heartbeat():
        while not stopped.wait(2):
            try:
                progress.save()
            except OSError:
                pass
    progress.save()
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    code = 1
    try:
        with redirect_stdout(progress), redirect_stderr(progress):
            with cloud_store.collection_lock() as acquired:
                if not acquired:
                    raise RuntimeError('Já existe outra coleta em andamento.')
                before = {chave_anuncio(item) for item in cloud_store.read_catalogue(root / 'geral.json')}
                try:
                    code = (collector or collect)(state)
                except Exception as error:
                    print(f'[COLETA_PARCIAL] Falha na coleta: {error}')
                try:
                    (enricher or enrich)(root, before, progress)
                except Exception as error:
                    print(f'[COLETA_PARCIAL] Falha ao buscar fotos: {error}')
                result = 'parcial' if progress.partial else 'sucesso' if code == 0 else 'falha'
                progress.save(status='finalizing', codigo=code, resultado=result, duracao=round(time.monotonic()-started, 1))
                try:
                    total = finalize(root, state, before)
                except Exception as error:
                    print(f'[COLETA_PARCIAL] Falha ao finalizar: {error}')
                    result, total = 'parcial', 0
                if code or result != 'sucesso':
                    try:
                        from utils.funcs import registrar_erro_coleta
                        registrar_erro_coleta(state['rotulo'], '\n'.join(state['log'][-120:]))
                    except Exception as error:
                        print(f'Não foi possível salvar o log de erros: {error}')
                print('Coleta encerrada. Os resultados já estão disponíveis.')
                progress.save(status='completed', resultado=result, novos=total)
    except Exception as error:
        progress.write(f'Falha ao iniciar a coleta: {error}\n')
        progress.save(status='failed', codigo=1, resultado='falha', message=str(error))
    finally:
        stopped.set()
        thread.join(timeout=3)
    return state.get('codigo', code)


if __name__ == '__main__':
    raise SystemExit(run_job(sys.argv[1]))
