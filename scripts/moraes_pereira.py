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

url = "https://www.moraesepereiraimoveis.com.br/imoveis/para-alugar/apartamento+casa+sobrado/pindamonhangaba?preco-de-locacao=2000~4500"
html = requests.get(url).content
soup = BeautifulSoup(html, "html.parser")
imoveis = []

divs = soup.find_all("div", class_="col-sm-12 col-lg-6 box-align")

pg = 1
for div in divs:
    link = div.find("a", href=True)["href"]
    base_url = f"https://{urlparse(url).netloc}"
    if link and link.startswith("/"):
        link = base_url + link

    h2 = div.find("h2", class_="card-title").get_text(strip=True)
    h3 = div.find("h3", class_="card-text").get_text(strip=True)
    titulo = f"{h3} - {h2}"

    preco = limpar_preco(div.find("span", class_="h-money location").get_text(strip=True))

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

with open(GERAL_JSON, "w", encoding="utf-8") as f:
    json.dump(dados, f, ensure_ascii=False, indent=2)

dados_sem_id = [
    {k: v for k, v in item.items() if k != "id"}
    for item in imoveis
]
gerar_excel(dados_sem_id, f"{PATH_GD}{EXCEL_FINAL}")