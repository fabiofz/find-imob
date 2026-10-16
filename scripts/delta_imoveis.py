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

urls = [
    "https://deltaimoveispinda.com.br/casas-para-locacao/",
    "https://deltaimoveispinda.com.br/sobrados-para-locacao/",
    "https://deltaimoveispinda.com.br/apartamento-para-locacao/"
]

for url in urls :
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
    }

    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    imoveis = []

    divs = soup.select(".rtcl_location-pindamonhangaba-sp")

    pg = 1
    for div in divs:
        link = div.find("a", href=True)["href"]
        titulo = div.find("h3", class_="listing-title").get_text(strip=True)
        preco = limpar_preco(div.find("div", class_="listing-price").get_text(strip=True))

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