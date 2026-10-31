#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 nao foi encontrado; nao foi possivel localizar os processos do Find Imob." >&2
    exit 1
fi

python3 - "$ROOT" <<'PY'
import os
import signal
import sys
import time

root = os.path.realpath(sys.argv[1])
expected_python = os.path.realpath(os.path.join(root, ".venv", "bin", "python"))


def find_app_processes():
    found = []
    try:
        entries = os.listdir("/proc")
    except OSError as exc:
        print(f"Nao foi possivel consultar /proc: {exc}", file=sys.stderr)
        return found
    for entry in entries:
        if not entry.isdigit():
            continue
        proc = f"/proc/{entry}"
        try:
            cwd = os.path.realpath(os.readlink(os.path.join(proc, "cwd")))
            with open(os.path.join(proc, "cmdline"), "rb") as stream:
                argv = [part.decode(errors="replace") for part in stream.read().split(b"\0") if part]
            if cwd != root or not argv:
                continue
            executable = argv[0]
            if not os.path.isabs(executable):
                executable = os.path.join(cwd, executable)
            if os.path.realpath(executable) != expected_python:
                continue
            is_proxy = len(argv) > 1 and argv[1] == "serve_local.py"
            is_streamlit = (
                len(argv) > 4
                and argv[1:4] == ["-m", "streamlit", "run"]
                and argv[4] == "app.py"
                and "--server.port" in argv
                and argv[argv.index("--server.port") + 1:argv.index("--server.port") + 2] == ["8502"]
                and "--server.address" in argv
                and argv[argv.index("--server.address") + 1:argv.index("--server.address") + 2] == ["127.0.0.1"]
            )
            if is_proxy or is_streamlit:
                found.append((int(entry), "proxy" if is_proxy else "Streamlit"))
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError, ValueError):
            continue
    return found


processes = find_app_processes()
if not processes:
    print("O Find Imob nao esta rodando nesta pasta.")
    raise SystemExit(0)

for pid, role in processes:
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Encerrando Find Imob ({role}, PID {pid})...")
    except ProcessLookupError:
        pass

for _ in range(80):
    remaining = {pid for pid, _ in find_app_processes()}
    if not remaining:
        print("Find Imob encerrado; as portas foram liberadas.")
        raise SystemExit(0)
    time.sleep(0.1)

for pid, role in find_app_processes():
    try:
        os.kill(pid, signal.SIGKILL)
        print(f"Processo ainda ativo; encerramento forcado ({role}, PID {pid}).")
    except ProcessLookupError:
        pass
print("Find Imob encerrado.")
PY
