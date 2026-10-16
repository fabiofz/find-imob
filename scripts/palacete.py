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

html = requests.get("https://www.palaceteimobiliaria.com.br/imoveis/para-alugar/apartamento+casa+sobrado/sao-paulo-pindamonhangaba-sp?precolocacao=1500--4000&mobilia=n%C3%A3o&muncep_id=7001&search_name=Pindamonhangaba&localidade=SP&toggle_map=true&propertySubtypes=55&propertySubtypes=64&propertySubtypes=50&propertySubtypes=120&propertySubtypes=350&propertySubtypes=346&propertySubtypes=19&propertySubtypes=320&propertySubtypes=321&propertySubtypes=325&propertySubtypes=169&order=mais_relevantes").content
soup = BeautifulSoup(html, "html.parser")
imoveis = []

divs = soup.find_all("li", class_="Imoveis_cardDisplay__e0Dc8")

pg = 1
for div in divs:
    tag_link = div.find("a")
    link = tag_link["href"] if tag_link else None

    img = div.find("img")
    titulo = img.get("alt") if img else None

    preco = None
    for div_preco in div.select("div.ImovelCardInfo_sizeOfPrices__SyQDF div"):
        spans = div_preco.find_all("span")
        
        if len(spans) >= 2 and "Aluguel" in spans[0].get_text(strip=True):
            preco = limpar_preco(spans[1].get_text(strip=True))
            break

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