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

url = f"https://www.spacoimoveis.com/imoveis/para-alugar/sobrado+casa+apartamento/pindamonhangaba?preco-de-locacao={int(PRECO_MIN)}~{int(PRECO_MAX)}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")
imoveis = []

divs = soup.select(".card-listing")

pg = 1
for div in divs:
    a_tag = div.select_one("a[href]")
    link = a_tag["href"] if a_tag else None

    base_url = f"https://{urlparse(url).netloc}"
    if link :
        link = base_url + link

    titulo = div.select_one(".card-title").get_text(strip=True)
    subtitulo = div.select_one(".card-text").get_text(strip=True)
    titulo = f'{subtitulo} - {titulo}'

    preco = limpar_preco(div.select_one(".location").get_text(strip=True))

    if not imovel_atende_filtros(titulo, preco, link, "pindamonhangaba"):
        continue

    _id = titulo+preco+link
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
