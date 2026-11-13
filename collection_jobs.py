"""Detached collection jobs and durable progress independent of Streamlit sessions."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


ROOT = Path(__file__).resolve().parent
RUNNING = {'queued', 'running', 'enriching', 'finalizing'}


@contextmanager
def launch_lock(root):
    folder = Path(root) / '.collection_jobs'
    folder.mkdir(mode=0o700, exist_ok=True)
    with (folder / 'launch.lock').open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            handle.write(b'0'); handle.flush(); handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def write_json(path, data):
    # Job progress belongs to the local worker, even when catalogue data is online.
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    temporary.chmod(0o600)
    temporary.replace(path)


def process_alive(pid):
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        stat = Path(f'/proc/{pid}/stat')
        return not stat.exists() or stat.read_text().rsplit(')', 1)[-1].strip().split()[0] != 'Z'
    except (OSError, ValueError):
        return False


def read_job(job_id, root=ROOT):
    if not job_id or any(c not in '0123456789abcdef' for c in str(job_id)):
        return {}
    path = Path(root) / '.collection_jobs' / f'{job_id}.json'
    state = read_json(path)
    if state.get('status') in RUNNING:
        starting = state['status'] == 'queued' and time.time() - state.get('created_at', 0) < 30
        if not starting and not process_alive(state.get('pid')):
            state.update(status='interrupted', message='A execução foi interrompida. Os anúncios já salvos foram preservados.')
            write_json(path, state)
    return state


def read_active(root=ROOT):
    pointer = read_json(Path(root) / '.execucao_ativa.json')
    if pointer.get('job_id'):
        return read_job(pointer['job_id'], root)
    if pointer:
        # Older UI-bound collectors cannot be resumed after their process died.
        alive = process_alive(pointer.get('pid'))
        return {**pointer, 'status': 'running' if alive else 'interrupted',
                'legacy': True, 'message': 'Esta coleta foi iniciada pela versão anterior.'}
    return {}


def start_collection(label, kind, identifier, parameters, root=ROOT):
    root = Path(root)
    with launch_lock(root):
        active = read_active(root)
        if active.get('status') in RUNNING:
            return active, False
        job_id = uuid.uuid4().hex
        state = {'id': job_id, 'rotulo': label, 'tipo': kind, 'identificador': identifier,
                 'parametros': parameters, 'status': 'queued', 'created_at': time.time(),
                 'log': ['Preparando coleta em segundo plano…']}
        path = root / '.collection_jobs' / f'{job_id}.json'
        write_json(path, state)
        environment = os.environ.copy()
        environment['PYTHONUNBUFFERED'] = '1'
        try:
            with path.with_suffix('.worker.log').open('ab') as output:
                process = subprocess.Popen(
                    [sys.executable, str(ROOT / 'collection_worker.py'), str(path)],
                    cwd=root, env=environment, stdin=subprocess.DEVNULL,
                    stdout=output, stderr=subprocess.STDOUT,
                    start_new_session=os.name != 'nt', close_fds=True,
                )
            # The worker owns its state; the launcher only writes this pointer.
            write_json(root / '.execucao_ativa.json', {'job_id': job_id})
        except Exception as error:
            state.update(status='failed', message=str(error))
            write_json(path, state)
            raise
        return {**state, 'pid': process.pid}, True
