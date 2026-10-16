from datetime import datetime

data_hoje = datetime.now().strftime("%Y-%m-%d-%H")

IMOVEIS_ACEITOS = ["casa", "casa-terrea", "sobrado", "duplex", "apartamento"]
GERAL_JSON = "geral.json"
PATH_GD = "/mnt/g/Meu Drive/Aluguel/"
EXCEL_FINAL = f"imoveis_{data_hoje}.xlsx"