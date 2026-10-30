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

imoveis = []
for im in IMOVEIS_ACEITOS :
    url = f"https://www.casabellaimoveispinda.com.br/busca-de-imoveis/?location=pindamonhangaba&type={im}&status=aluguel"
    html = requests.get(url).content
    soup = BeautifulSoup(html, "html.parser")

    numeros = []
    for a in soup.select(".rh_pagination a.rh_pagination__btn"):
        label = a.get_text(strip=True)
        if label and label.isdigit():
            numeros.append(int(label)) 

    if len(numeros) == 0 :
        numeros.append(1)

    for pg in range(1, int(max(numeros)) + 1):
        url = f"https://www.casabellaimoveispinda.com.br/busca-de-imoveis/page/{pg}/?location=pindamonhangaba&type={im}&status=aluguel"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }

        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")

        divs = soup.find_all("article", class_="rh_list_card")

        for div in divs:
            link = div.select_one("h3 a")["href"]
            titulo = div.select_one("h3 a").get_text(strip=True)
            texto_preco = div.select_one(".price").get_text(" ", strip=True)

            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', texto_preco)

            preco = sum(br_to_float(v) for v in valores)
            if not imovel_atende_filtros(titulo, preco, link, "pindamonhangaba"):
                continue

            _id = f"{titulo}{preco}{link}"
            _id = hashlib.md5(_id.encode()).hexdigest()

            if _id not in ids:
                imov = {
                    "id": _id,
                    "titulo": titulo,
                    "preco": f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
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
