"""Executa todos os coletores e resume eventuais falhas."""

import subprocess
import sys
import os
import time
from collections import deque
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / "scripts"
COLETORES_PINDAMONHANGABA = {
    "casabella", "castor", "confianca", "delta_imoveis", "derrico", "domus",
    "hamilton", "moraes_pereira", "palacete", "pindense", "rodrigoderrico",
    "spaco", "visao", "wilson",
}


def main():
    cidades = {
        cidade.strip().casefold()
        for cidade in os.environ.get(
            "FINDIMOB_CIDADES", "pindamonhangaba,tremembe,taubate"
        ).split(",")
        if cidade.strip()
    }
    scripts = sorted(
        path.stem
        for path in SCRIPTS_DIR.glob("*.py")
        if path.name != "__init__.py"
    )
    if not scripts:
        print("Nenhum coletor encontrado em scripts/.")
        return 1

    falhas = []
    for script in scripts:
        if script in COLETORES_PINDAMONHANGABA and "pindamonhangaba" not in cidades:
            print(f"Ignorando {script}: Pindamonhangaba não está selecionada.", flush=True)
            continue
        modulo = f"scripts.{script}"
        comando = [sys.executable, "-m", modulo]
        inicio = time.monotonic()
        saida = deque(maxlen=500)
        processo = None
        print(f"\n=== Iniciando {modulo} ===", flush=True)
        try:
            ambiente = os.environ.copy()
            ambiente["PYTHONUNBUFFERED"] = "1"
            processo = subprocess.Popen(
                comando,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=ambiente,
            )
            for linha in processo.stdout:
                saida.append(linha.rstrip())
                print(linha, end="", flush=True)
            codigo = processo.wait()
        except Exception as erro:
            codigo = 1
            detalhe_execucao = f"Erro ao executar {modulo}: {erro}"
            saida.append(detalhe_execucao)
            print(detalhe_execucao, flush=True)
            if processo is not None and processo.poll() is None:
                try:
                    processo.kill()
                    processo.wait()
                except OSError as erro_parada:
                    print(f"Não foi possível encerrar {modulo}: {erro_parada}", flush=True)

        duracao = time.monotonic() - inicio
        if codigo:
            falhas.append((modulo, codigo))
            detalhe = f"Falha em {modulo} (código {codigo}, {duracao:.1f}s)."
            print(detalhe, flush=True)
            try:
                with (ROOT / "logs_erros.txt").open("a", encoding="utf-8") as arquivo:
                    arquivo.write(f"\n{'=' * 78}\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {detalhe}\n")
                    arquivo.write("\n".join(saida))
                    arquivo.write("\n")
            except OSError as erro_log:
                print(f"Não foi possível registrar logs_erros.txt: {erro_log}", flush=True)
        else:
            print(f"Concluído {modulo} em {duracao:.1f}s.", flush=True)

    if falhas:
        print("\nColetores com falha:")
        for modulo, codigo in falhas:
            print(f"- {modulo}: código {codigo}")
        return 1
    print(f"\nColeta concluída: {len(scripts)} coletores executados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
