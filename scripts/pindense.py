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

url = "https://www.imobiliariapindense.com.br/buscar?order=most_relevant&direction=desc&availability=rent&search_type=properties_map&property_type=Apartamento&property_type=Casa&property_type=Sobrado&value_max=4500&value_min=1500"
html = requests.get(url).content
soup = BeautifulSoup(html, "html.parser")
imoveis = []

divs = soup.find_all("imobzi-property-card")

pg = 1
for div in divs:
    titulo = div.select_one(".property-title").get_text(strip=True)

    aluguel = None
    total = None
    preco = 0
    for h in div.select("mat-card-content h3.color-title"):
        texto = h.get_text(" ", strip=True)
        
        if "/total" in texto:
            preco = limpar_preco(texto.strip())
            break

    a_tag = div.select_one("swiper-slide a[href]")
    link = a_tag["href"] if a_tag else None

    base_url = f"https://{urlparse(url).netloc}"
    if link and link.startswith("/"):
        link = base_url + link

    _id = f"{titulo}+{preco}+{link}"
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