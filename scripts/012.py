from bs4 import BeautifulSoup
import requests
import hashlib
import re
import json
from utils.funcs import *
from utils.variables import *
from urllib.parse import urlparse

json_data = pegar_json(GERAL_JSON)
ids = json_data["ids"]
dados = json_data["dados"]

url = "https://012imoveis.com.br/busca?finalidade=Aluguel&tipo=Apartamento%2CCasa%2CCasa+em+Condom%C3%ADnio%2CSobrado"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")
imoveis = []

divs = soup.find_all("a", class_="flex flex-col bg-white rounded-xl h-full relative")

pg = 1
for div in divs:
    link = div["href"]
    base_url = f"https://{urlparse(url).netloc}"
    if link :
        link = base_url + link

    titulo = div.select_one(".line-clamp-1").get_text(strip=True)

    precos = div.select("span.text-lg.font-medium.leading-8")
    if len(precos) > 1 :
        preco = limpar_preco(precos[1].get_text(" ", strip=True))

    preco_num = preco_para_float(preco)
    if preco_num is None or not (2000 <= preco_num <= 4000):
        continue

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

with open(GERAL_JSON, "w", encoding="utf-8") as f:
    json.dump(dados, f, ensure_ascii=False, indent=2)

dados_sem_id = [
    {k: v for k, v in item.items() if k != "id"}
    for item in imoveis
]
gerar_excel(dados_sem_id, f"{PATH_GD}{EXCEL_FINAL}")