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

url = "https://www.visaoconsultoriadeimoveis.com.br/imoveis/para-alugar/casa+sobrado/pindamonhangaba?preco-de-locacao=1000~4000"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

resp = requests.get(url, headers=headers)
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