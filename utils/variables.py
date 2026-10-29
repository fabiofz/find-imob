from datetime import datetime
import os

data_hoje = datetime.now().strftime("%Y-%m-%d-%H")

IMOVEIS_ACEITOS = ["casa", "casa-terrea", "sobrado", "duplex", "apartamento"]
GERAL_JSON = "geral.json"
PATH_GD = os.path.join(
    os.environ.get("IMOVEIS_OUTPUT_DIR", "/mnt/g/Meu Drive/Aluguel/"), ""
)
EXCEL_FINAL = f"imoveis_{data_hoje}.xlsx"
