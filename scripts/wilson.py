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

url = f"https://wilsonimoveisvale.com.br/alugar/sp/pindamonhangaba/apartamento_casa/valor-{int(PRECO_MIN)}_{int(PRECO_MAX)}/ordem-valor/resultado-crescente/quantidade-12/"
html = requests.get(url, timeout=(5, 20)).content
soup = BeautifulSoup(html, "html.parser")
imoveis = []

divs = soup.find_all("div", class_="link_resultado")

pg = 1
for div in divs:
    with continue_on_error('wilson: anúncio'):
        local = div.select_one(".final_card span").get_text(strip=True)
        titulo = div.select_one(".titulo_novo").get_text(strip=True)
        titulo = f'{titulo} - {local}'

        preco = None
        for bloco in div.select(".valor_novo"):
            tipo = bloco.select_one("small").get_text(strip=True)
        
            if "LOCAÇÃO" in tipo.upper():
                preco = bloco.select_one("h5").get_text(strip=True)
                break

        link_tag = div.select_one("a.botao_ver_mais")
        if not link_tag:
            link_tag = div.select_one("a.foto_imovel")
        link = link_tag["href"] if link_tag else None

        base_url = f"https://{urlparse(url).netloc}"
        if link :
            link = base_url + link

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
