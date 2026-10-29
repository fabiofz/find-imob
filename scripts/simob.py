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
    "https://www.simobsolucoesimobiliarias.com.br/imovel/locacao/apartamento/pindamonhangaba/?&vmi=2000&vma=4500",
    "https://www.simobsolucoesimobiliarias.com.br/imovel/locacao/casa/pindamonhangaba/?&vmi=2000&vma=4500",
]
imoveis = []

for url in urls :
    url_pagina = f"{url}&pag=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }

    resp = requests.get(url_pagina, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    numeros = []
    for a in soup.select(".lipagina-btn-paginacao-atual"):
        label = a.get_text(strip=True)
        if label and label.isdigit():
            numeros.append(int(label)) 

    for pg in range(1, int(max(numeros)) + 1):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }

        resp = requests.get(f"{url}&pag={pg}", headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")

        divs = soup.select(".imovelcard")

        for div in divs:
            a = div.select_one("a.imovelcard__img")
            if a == None :
                break

            link = a.get("href")
            base_url = f"https://{urlparse(url).netloc}"
            if link and link.startswith("/"):
                link = base_url + link

            titulo = a.get("title")
            preco = limpar_preco(div.select_one(".imovelcard__valor__valor").get_text(strip=True))

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
