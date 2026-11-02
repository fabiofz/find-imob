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

imoveis = []
url = f"https://www.hnegocios.com/imoveis/alugar/pindamonhangaba/pag-1"
html = requests.get(url, timeout=(5, 20)).content
soup = BeautifulSoup(html, "html.parser")

numeros = []
for a in soup.select(".pagina-btn"):
    label = a.get_text(strip=True)
    if label and label.isdigit():
        numeros.append(int(label)) 

if len(numeros) == 0 :
    numeros.append(1)

for pg in range(1, int(max(numeros)) + 1):
    url = f"https://www.hnegocios.com/imoveis/alugar/pindamonhangaba/pag-{pg}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }

    resp = requests.get(url, headers=headers, timeout=(5, 20))
    soup = BeautifulSoup(resp.text, "html.parser")

    divs = soup.find_all("div", class_="box")

    for div in divs:
        titulo_tag = div.select_one(".titulo-imovel")
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else None

        if not titulo:
            continue

        link_tag = div.select_one('a[href*="/imovel/"]')
        link = link_tag["href"] if link_tag else None

        preco = 0
        for span in div.select(".precos"):
            texto = span.get_text(" ", strip=True)

            if "Aluguel" in texto:
                b = span.select_one("b")
                preco = b.get_text(strip=True) if b else None
                break
        preco = limpar_preco(preco)
        
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
