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

url = "https://www.novafreitas.com.br/pesquisa-de-imoveis/?busca_free=&locacao_venda=L&valor_loc_min_input=1500&valor_loc_max_input=4000&valor_ven_min_input=0&valor_ven_max_input=0&id_cidade%5B%5D=86&id_tipo_imovel%5B%5D=1&id_tipo_imovel%5B%5D=3&id_tipo_imovel%5B%5D=157&id_tipo_imovel%5B%5D=183&id_tipo_imovel%5B%5D=125&id_tipo_imovel%5B%5D=10&id_tipo_imovel%5B%5D=38&id_tipo_imovel%5B%5D=12&id_tipo_imovel%5B%5D=80&id_tipo_imovel%5B%5D=13&dormitorio=&garagem=&finalidade=residencial&a_min=&a_max=&area_tipo=&vmi=&vma=&ordem=4"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")
imoveis = []

divs = soup.select(".muda_card1")

pg = 1
for div in divs:
    link = div.select_one(".carousel-cell")["href"]
    base_url = f"https://{urlparse(url).netloc}/"
    if link :
        link = base_url + link

    titulo = div.select_one(".card-titulo h2").get_text(strip=True)
    valores = div.select(".card-valores div")
    preco_num = limpar_preco(valores[0].get_text(strip=True))
    preco_q = preco_num.split("R$ ")

    preco = f"R$ {preco_q[1]}"
    if len(preco_q) > 2 :
        preco = f"R$ {preco_q[2]}"

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

with open(GERAL_JSON, "w", encoding="utf-8") as f:
    json.dump(dados, f, ensure_ascii=False, indent=2)

dados_sem_id = [
    {k: v for k, v in item.items() if k != "id"}
    for item in imoveis
]
gerar_excel(dados_sem_id, f"{PATH_GD}{EXCEL_FINAL}")