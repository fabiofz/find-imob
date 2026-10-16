import subprocess
import time
import os
from utils.variables import *

arquivo = f"{PATH_GD}{EXCEL_FINAL}"

# if os.path.exists(arquivo):
#     os.remove(arquivo)
#     print(f"Arquivo removido: {arquivo}")

pasta_scripts = "scripts"

scripts = [
    f.replace(".py", "")
    for f in os.listdir(pasta_scripts)
    if f.endswith(".py") and f != "__init__.py"
]

for script in scripts:
    modulo = f"{pasta_scripts}.{script}"
    print(f"Executando {modulo}...")

    result = subprocess.run(
        ["python3", "-m", modulo],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print(f"Erro ao executar {modulo}")
        print(result.stderr)
        break