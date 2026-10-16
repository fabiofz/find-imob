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

html = requests.get("https://derricoimoveis.com.br/imoveis/aluguel").content
soup = BeautifulSoup(html, "html.parser")
imoveis = []

pagination = soup.find("div", class_="pagination")
if pagination is None:
    print("Elemento de paginação não encontrado!")
    print(soup.title)
    print(soup.get_text(" ", strip=True)[:500])
    raise SystemExit(1)
    
pages = pagination.find_all("a", class_="PageNumber")
numeros = []

for p in pages:
    label = p.get("aria-label")
    if label and label.isdigit():
        numeros.append(int(label))

for pg in range(1, int(max(numeros)) + 1):
    html = requests.get(f"https://derricoimoveis.com.br/imoveis/aluguel?pg={pg}").content
    soup = BeautifulSoup(html, "html.parser")

    divs = soup.find_all("div", class_="ImovelItem")

    for div in divs:
        tag_titulo = div.find("a", class_="Title")
        titulo = tag_titulo.get_text(strip=True) if tag_titulo else None

        if not titulo or not any(tipo in titulo.lower() for tipo in IMOVEIS_ACEITOS):
            continue

        tag_preco = div.select_one(".ImovelValor .value")
        preco = tag_preco.get_text(strip=True) if tag_preco else None

        preco_num = preco_para_float(preco)
        if preco_num is None or not (2000 <= preco_num <= 4000):
            continue

        link = tag_titulo["href"] if tag_titulo else None

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