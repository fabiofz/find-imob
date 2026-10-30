#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi

if ! .venv/bin/python -c 'import streamlit' >/dev/null 2>&1; then
    .venv/bin/python -m pip install -r requirements.txt
fi

if .venv/bin/python -c 'import socket,sys; s=socket.socket(); ocupado=s.connect_ex(("127.0.0.1",8501)) == 0; s.close(); sys.exit(0 if ocupado else 1)'; then
    echo "O painel já está rodando em http://localhost:8501"
    exit 0
fi

exec .venv/bin/python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
