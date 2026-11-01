#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi

# Reparar uma instalação incompleta do pip antes de tentar instalar dependências.
if ! .venv/bin/python -c 'from pip._internal.cli.main import main' >/dev/null 2>&1; then
    echo "Reparando o pip do ambiente virtual..."
    .venv/bin/python - <<'PY_BOOTSTRAP'
import ensurepip
import shutil
import site
import subprocess
import sys
import zipfile
from pathlib import Path

venv_root = Path(sys.prefix).resolve()
site_packages = Path(site.getsitepackages()[0]).resolve()
if not site_packages.is_relative_to(venv_root):
    raise SystemExit("O caminho do pip nao esta dentro do ambiente virtual.")

pip_package = site_packages / "pip"
if pip_package.is_symlink():
    pip_package.unlink()
else:
    shutil.rmtree(pip_package, ignore_errors=True)
for metadata in site_packages.glob("pip-*.dist-info"):
    if metadata.is_symlink():
        metadata.unlink()
    else:
        shutil.rmtree(metadata, ignore_errors=True)

bundled = Path(ensurepip.__file__).resolve().parent / "_bundled"
wheels = sorted(bundled.glob("pip-*.whl")) if bundled.is_dir() else []
if wheels:
    with zipfile.ZipFile(wheels[-1]) as wheel:
        wheel.extractall(site_packages)
else:
    # Algumas distribuicoes Ubuntu removem os wheels do ensurepip, mas mantem
    # o pip do sistema instalado pelo apt. Copie-o para o venv como fallback.
    system_python = Path(sys.base_prefix) / "bin" / "python3"
    result = subprocess.run(
        [str(system_python), "-c", "import pip; print(pip.__file__)"],
        check=False, capture_output=True, text=True,
    )
    if result.returncode:
        raise SystemExit("Nao foi encontrada uma copia local do pip para restauracao.")
    system_pip = Path(result.stdout.strip()).resolve().parent
    system_site = system_pip.parent
    shutil.copytree(system_pip, site_packages / "pip")
    metadata = sorted(system_site.glob("pip-*.dist-info"))
    if not metadata:
        shutil.rmtree(site_packages / "pip", ignore_errors=True)
        raise SystemExit("O pip do sistema nao possui os metadados necessarios.")
    for item in metadata:
        shutil.copytree(item, site_packages / item.name)
PY_BOOTSTRAP
fi

if ! .venv/bin/python -c 'from pip._internal.cli.main import main' >/dev/null 2>&1; then
    echo "Nao foi possivel restaurar o pip do ambiente virtual." >&2
    exit 1
fi

if ! .venv/bin/python -c 'import streamlit, PIL, requests, bs4, typing_extensions' >/dev/null 2>&1; then
    echo "Instalando ou reparando as dependencias do app..."
    .venv/bin/python -m pip install --force-reinstall -r requirements.txt
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
