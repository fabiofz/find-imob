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

    resp = requests.get(url, headers=headers, timeout=(5, 20))
    soup = BeautifulSoup(resp.text, "html.parser")
    imoveis = []

    divs = soup.select(".rtcl_location-pindamonhangaba-sp")

    pg = 1
    for div in divs:
        link = div.find("a", href=True)["href"]
        titulo = div.find("h3", class_="listing-title").get_text(strip=True)
        preco = limpar_preco(div.find("div", class_="listing-price").get_text(strip=True))

        if not imovel_atende_filtros(titulo, preco, link, "pindamonhangaba"):
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

salvar_json(dados, GERAL_JSON)
