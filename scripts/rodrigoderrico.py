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

urls = [
    "https://www.rodrigoderrico.com.br/locacao-casas-opc1-padrao.html",
    "https://www.rodrigoderrico.com.br/locacao-casas-opc1-condominio.html",
    "https://www.rodrigoderrico.com.br/locacao-apartamentos.html",
]
imoveis = []

for url in urls :
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }

    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    divs = soup.select("ul.properties_list li")

    pg = 1
    for div in divs:
        preco = None
        for h3 in div.select("h3"):
            texto = h3.get_text(strip=True)
            if texto.startswith("Valor:"):
                preco = texto.replace("Valor:", "").strip()

        titulo = None
        for h3 in div.select("h3"):
            texto = h3.get_text(strip=True)
            if texto.startswith("Bairro:"):
                titulo = texto.replace("Bairro:", "").strip()

        link_tag = div.select_one('a[href]')
        link = link_tag["href"] if link_tag else None

        if preco == None :
            break

        base_url = f"https://{urlparse(url).netloc}/"
        if link :
            link = base_url + link

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

dados_sem_id = [
    {k: v for k, v in item.items() if k != "id"}
    for item in imoveis
]
gerar_excel(dados_sem_id, f"{PATH_GD}{EXCEL_FINAL}")
