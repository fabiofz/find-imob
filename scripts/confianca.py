from bs4 import BeautifulSoup
import requests
import hashlib
import re
import json
from utils.funcs import *
from utils.variables import *

json_data = pegar_json(GERAL_JSON)
ids = json_data["ids"]
dados = json_data["dados"]

url = "https://www.imobiliariaconfianca.com.br/index.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")
imoveis = []

divs = soup.find_all("div", class_="trend-item")

pg = 1
for div in divs:
    titulo = div.select_one("h4 a").get_text(strip=True)
    if not titulo or not any(tipo in titulo.lower() for tipo in IMOVEIS_ACEITOS):
        continue

    preco = limpar_preco(div.select_one(".entry-author .theme").get_text(strip=True))

    preco_num = preco_para_float(preco)
    if preco_num is None or not (2000 <= preco_num <= 4500):
        continue

    link = f"https://www.imobiliariaconfianca.com.br/{div.select_one('a[href]')['href']}"

    _id = f"{titulo}{preco}{link}"
    _id = hashlib.md5(_id.encode()).hexdigest()

    if _id not in ids:
        imov = {
            "id": _id,
            "titulo": titulo,
            "preco": preco,
            "link": link,
            "pagina": pg
        }
        imoveis.append(imov)
        dados.append(imov)

salvar_json(dados, GERAL_JSON)

dados_sem_id = [
    {k: v for k, v in item.items() if k != "id"}
    for item in imoveis
]
gerar_excel(dados_sem_id, f"{PATH_GD}{EXCEL_FINAL}")
