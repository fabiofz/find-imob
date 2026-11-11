"""Run configured collectors with live progress and bounded execution time."""

import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from queue import Empty, Queue
from utils.funcs import registrar_erro_coleta

ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / "scripts"
COLETORES_PINDAMONHANGABA = {
    "casabella", "castor", "confianca", "delta_imoveis", "derrico", "domus",
    "hamilton", "moraes_pereira", "palacete", "pindense", "rodrigoderrico",
    "spaco", "visao", "wilson",
}
SCRIPT_TIMEOUT_SECONDS = max(30, int(os.environ.get("FINDIMOB_COLLECTOR_TIMEOUT", "90")))
HEARTBEAT_SECONDS = 10


def _stop_process(process):
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except OSError:
        pass
    try:
        process.wait(timeout=4)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        if os.name == "nt":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        pass
    try:
        process.wait(timeout=4)
    except subprocess.TimeoutExpired:
        pass


def _run_collector(module, environment, falhas, portal=None):
    command = [sys.executable, "-m", f"scripts.{module}"]
    label = f"scripts.{module}" + (f" [{portal}]" if portal else "")
    if portal:
        command.extend(["--portal", portal])
    started = time.monotonic()
    output = deque(maxlen=500)
    lines = Queue()
    process = None
    timed_out = False

    print(f"\n=== Iniciando {label} ===", flush=True)
    try:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=environment,
            start_new_session=(os.name != "nt"),
        )

        def forward_output():
            try:
                for line in process.stdout:
                    lines.put(line)
            finally:
                lines.put(None)

        reader = threading.Thread(target=forward_output, daemon=True)
        reader.start()
        reader_done = False
        next_heartbeat = started + HEARTBEAT_SECONDS

        while not reader_done:
            try:
                line = lines.get(timeout=1)
            except Empty:
                line = ""

            if line is None:
                reader_done = True
            elif line:
                clean_line = line.rstrip()
                output.append(clean_line)
                print(line, end="", flush=True)

            now = time.monotonic()
            elapsed = now - started
            if process.poll() is None and elapsed >= SCRIPT_TIMEOUT_SECONDS:
                timed_out = True
                print(
                    f"[TIMEOUT] {label} excedeu {SCRIPT_TIMEOUT_SECONDS}s; "
                    "encerrando este coletor e continuando os demais.",
                    flush=True,
                )
                _stop_process(process)
                break

            if process.poll() is None and now >= next_heartbeat:
                print(
                    f"[AGUARDANDO] {label} continua executando "
                    f"ha {int(elapsed)}s.",
                    flush=True,
                )
                next_heartbeat = now + HEARTBEAT_SECONDS

        code = process.wait()
        if timed_out:
            code = 124
    except Exception as error:
        code = 1
        detail = f"Erro ao executar {label}: {error}"
        output.append(detail)
        print(detail, flush=True)
        if process is not None:
            _stop_process(process)

    duration = time.monotonic() - started
    if code:
        falhas.append((label, code))
        detail = f"Falha em {label} (codigo {code}, {duration:.1f}s)."
        print(detail, flush=True)
        try:
            registrar_erro_coleta(detail, "\n".join(output))
        except Exception as error:
            print(f"Nao foi possivel registrar o erro da coleta: {error}", flush=True)
    else:
        print(f"Concluido {label} em {duration:.1f}s.", flush=True)


def main():
    cities = {
        city.strip().casefold()
        for city in os.environ.get(
            "FINDIMOB_CIDADES", "pindamonhangaba,tremembe,taubate,sao-jose-dos-campos"
        ).split(",")
        if city.strip()
    }
    scripts = sorted(
        path.stem
        for path in SCRIPTS_DIR.glob("*.py")
        if path.name != "__init__.py"
    )
    if not scripts:
        print("Nenhum coletor encontrado em scripts/.")
        return 1

    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    failures = []
    for script in scripts:
        if script in COLETORES_PINDAMONHANGABA and "pindamonhangaba" not in cities:
            print(f"Ignorando scripts.{script}: Pindamonhangaba nao esta selecionada.", flush=True)
            continue
        if script == "catalog_collectors":
            from scripts.catalog_collectors import (
                PORTAIS_CARD, PORTAIS_TAILWIND, PORTAIS_LOCAIS, PORTAIS_INDISPONIVEIS,
            )
            # Each agency has its own time budget. The old shared 90-second
            # budget killed the whole catalogue before reaching later agencies.
            for portal in (*PORTAIS_CARD, *PORTAIS_TAILWIND, *PORTAIS_LOCAIS):
                if portal in PORTAIS_INDISPONIVEIS:
                    print(f"[INDISPONÍVEL] {portal}: {PORTAIS_INDISPONIVEIS[portal]}", flush=True)
                    continue
                _run_collector(script, environment, failures, portal=portal)
        else:
            _run_collector(script, environment, failures)

    if failures:
        print("\nColetores com falha:")
        for module, code in failures:
            print(f"- {module}: codigo {code}")
        return 1
    print("\nColeta concluída: todos os coletores selecionados foram executados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
