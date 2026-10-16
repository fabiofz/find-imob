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

url = "https://www.domusimoveis.com/imoveis/para-alugar/apartamento+casa+sobrado/sao-paulo-pindamonhangaba-sp?precolocacao=2000--4000&muncep_id=7001&search_name=Pindamonhangaba&localidade=SP&toggle_map=true&propertySubtypes=321&propertySubtypes=325&propertySubtypes=169&propertySubtypes=93&propertySubtypes=64&propertySubtypes=84&propertySubtypes=120&propertySubtypes=350&propertySubtypes=346&propertySubtypes=19&propertySubtypes=320&propertySubtypes=106&propertySubtypes=55&order=mais_relevantes"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")
imoveis = []

divs = soup.select(".Imoveis_cardDisplay__e0Dc8")

pg = 1
for div in divs:
    link = div.find("a", href=True)["href"]

    tipo = div.find("span", class_="ImovelCardInfo_colorOfTypePropertie__OWVB6").get_text(strip=True)
    nome = div.find("span", class_="ImovelCardInfo_colorOfTitleCondominium__IfTu_").get_text(strip=True)
    titulo = f"{tipo} - {nome}"

    preco = limpar_preco(div.find("span", class_="ImovelCardInfo_sizeOfPriceSale__KE1ms").get_text(strip=True))

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