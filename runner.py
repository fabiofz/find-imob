"""Executa todos os coletores e resume eventuais falhas."""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / "scripts"


def main():
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
        modulo = f"scripts.{script}"
        print(f"\n=== Executando {modulo} ===", flush=True)
        resultado = subprocess.run(
            [sys.executable, "-m", modulo],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if resultado.stdout:
            print(resultado.stdout.rstrip())
        if resultado.stderr:
            print(resultado.stderr.rstrip(), file=sys.stderr)
        if resultado.returncode:
            falhas.append((modulo, resultado.returncode))
            print(f"Falha em {modulo} (código {resultado.returncode}).")

    if falhas:
        print("\nColetores com falha:")
        for modulo, codigo in falhas:
            print(f"- {modulo}: código {codigo}")
        return 1
    print(f"\nColeta concluída: {len(scripts)} coletores executados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
