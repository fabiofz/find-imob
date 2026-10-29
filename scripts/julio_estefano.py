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

url = "https://pindamonhangaba.estefanoconsultoria.com.br/busca?finalidade=Aluguel&tipo=Apartamento%2CCasa%2CCasa+em+Condom%C3%ADnio%2CCobertura&cidade=Pindamonhangaba&min=1500.00&max=2000.00"
html = requests.get(url).content
soup = BeautifulSoup(html, "html.parser")
imoveis = []

divs = soup.find_all("a", class_="flex flex-col bg-white rounded-xl h-full relative")

pg = 1
for div in divs:
    link = div["href"]
    base_url = f"https://{urlparse(url).netloc}"
    if link and link.startswith("/"):
        link = base_url + link
    
    titulo = div.find("span", class_="text-base font-bold leading-5 line-clamp-1").get_text(strip=True)
    preco = limpar_preco(div.find("span", class_="text-lg font-medium leading-8").get_text(strip=True))

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
