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

url = "https://www.castorimoveis.com.br/lista-imoveis.php?tipo-negocio=aluguel"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")
imoveis = []

divs = soup.select(".house")

pg = 1
for div in divs:
    titulo = div.find("h5").get_text(strip=True)
    
    link = div.find("a", href=True)["href"]

    base_url = f"https://{urlparse(url).netloc}/"
    if link :
        link = base_url + link

    preco = limpar_preco(div.find("div", class_="pt-price").get_text(strip=True))
    preco_num = preco_para_float(preco)
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
