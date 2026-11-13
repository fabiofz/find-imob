from utils.collection_errors import continue_on_error
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

url = f"https://www.imobiliariapindense.com.br/buscar?order=most_relevant&direction=desc&availability=rent&search_type=properties_map&property_type=Apartamento&property_type=Casa&property_type=Sobrado&value_max={int(PRECO_MAX)}&value_min={int(PRECO_MIN)}"
html = requests.get(url, timeout=(5, 20)).content
soup = BeautifulSoup(html, "html.parser")
imoveis = []

divs = soup.find_all("imobzi-property-card")

pg = 1
for div in divs:
    with continue_on_error('pindense: anúncio'):
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

        if not imovel_atende_filtros(titulo, preco, link, "pindamonhangaba"):
            continue

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

salvar_json(dados, GERAL_JSON)
