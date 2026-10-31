#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi

if ! .venv/bin/python -c 'import streamlit, PIL' >/dev/null 2>&1; then
    .venv/bin/python -m pip install -r requirements.txt
fi

./ensure_local_tls.sh

if .venv/bin/python -c 'import socket,sys; s=socket.socket(); ocupado=s.connect_ex(("127.0.0.1",8501)) == 0; s.close(); sys.exit(0 if ocupado else 1)'; then
    echo "A porta 8501 ja esta em uso. Verifique se o proxy local do Find Imob esta ativo."
    exit 1
fi
if .venv/bin/python -c 'import socket,sys; s=socket.socket(); ocupado=s.connect_ex(("127.0.0.1",8502)) == 0; s.close(); sys.exit(0 if ocupado else 1)'; then
    echo "A porta interna 8502 ja esta em uso. Encerre a execucao antiga antes de iniciar."
    exit 1
fi

exec .venv/bin/python serve_local.py
