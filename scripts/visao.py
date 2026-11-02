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

url = f"https://www.visaoconsultoriadeimoveis.com.br/imoveis/para-alugar/casa+sobrado/pindamonhangaba?preco-de-locacao={int(PRECO_MIN)}~{int(PRECO_MAX)}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

resp = requests.get(url, headers=headers, timeout=(5, 20))
soup = BeautifulSoup(resp.text, "html.parser")
imoveis = []

divs = soup.find_all("a", class_="card-with-buttons")

pg = 1
for div in divs:
    link = div["href"]
    base_url = f"https://{urlparse(url).netloc}"
    if link :
        link = base_url + link

    titulo = div.select_one(".card-with-buttons__heading").get_text(strip=True)

    preco = None
    for bloco in div.select(".card-with-buttons__value-container"):
        titulo_preco = bloco.select_one(".card-with-buttons__value-title").get_text(strip=True)
        if "Aluguel" in titulo_preco:
            preco = limpar_preco(bloco.select_one(".card-with-buttons__value").get_text(strip=True))

    if not imovel_atende_filtros(titulo, preco, link, "pindamonhangaba"):
        continue
    _id = titulo + preco + link
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
