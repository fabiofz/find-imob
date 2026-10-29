from bs4 import BeautifulSoup
import requests
import hashlib
import os
import json
import re
from urllib.parse import urljoin

from utils.funcs import *
from utils.variables import *


URL = (
    "https://www.domusimoveis.com/imoveis/para-alugar/"
    "apartamento+casa+sobrado/sao-paulo-pindamonhangaba-sp"
    "?precolocacao=2000--4500&muncep_id=7001"
    "&search_name=Pindamonhangaba&localidade=SP&toggle_map=true"
    "&propertySubtypes=321&propertySubtypes=325&propertySubtypes=169"
    "&propertySubtypes=93&propertySubtypes=64&propertySubtypes=84"
    "&propertySubtypes=120&propertySubtypes=350&propertySubtypes=346"
    "&propertySubtypes=19&propertySubtypes=320&propertySubtypes=106"
    "&propertySubtypes=55&order=mais_relevantes"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def texto(elemento):
    return elemento.get_text(" ", strip=True) if elemento else None


def primeiro_seletor(elemento, seletores):
    for seletor in seletores:
        encontrado = elemento.select_one(seletor)
        if encontrado:
            return encontrado
    return None


def encontrar_cards(soup):
    # Os nomes de classe do site parecem ser gerados pelo frontend.
    # Mantemos o seletor original e incluímos alternativas menos específicas.
    seletores = (
        "div.Imoveis_cardDisplay__e0Dc8",
        'div[class*="Imoveis_cardDisplay"]',
        'div[class*="cardDisplay"]',
    )
    for seletor in seletores:
        cards = soup.select(seletor)
        if cards:
            return cards
    return []


def extrair_imovel(card, pagina=1):
    link_tag = primeiro_seletor(card, [
        'a[href*="/imovel"]',
        "a[href]",
    ])
    if not link_tag or not link_tag.get("href"):
        return None

    link = urljoin("https://www.domusimoveis.com", link_tag["href"])

    tipo_tag = primeiro_seletor(card, [
        'span[class*="colorOfTypePropertie"]',
        'span[class*="TypePropertie"]',
    ])
    nome_tag = primeiro_seletor(card, [
        'span[class*="colorOfTitleCondominium"]',
        'span[class*="TitleCondominium"]',
    ])
    preco_tag = primeiro_seletor(card, [
        'span[class*="sizeOfPriceSale"]',
        'span[class*="PriceSale"]',
        '[class*="price"]',
        '[class*="Price"]',
    ])

    tipo = texto(tipo_tag)
    nome = texto(nome_tag)

    # Se o site alterar os nomes das classes, usa o texto do link como fallback.
    if not nome:
        nome = texto(link_tag)
    if not tipo:
        tipo = ""

    titulo = f"{tipo} - {nome}".strip(" -") if nome else None
    preco = limpar_preco(texto(preco_tag))
    if not titulo or not preco:
        return None
    return {
        "titulo": titulo,
        "preco": preco,
        "link": link,
        "pagina": pagina,
    }


def executar():
    estado = pegar_json(GERAL_JSON)
    ids = estado["ids"]
    dados = estado["dados"]

    resposta = requests.get(URL, headers=HEADERS, timeout=30)
    resposta.raise_for_status()
    soup = BeautifulSoup(resposta.text, "html.parser")
    cards = encontrar_cards(soup)
    if not cards:
        titulo_pagina = texto(soup.title) or "(sem título)"
        raise RuntimeError(
            f"Domus: nenhum anúncio encontrado; página recebida: {titulo_pagina}"
        )

    novos = []
    for card in cards:
        item = extrair_imovel(card)
        if not item:
            continue
        identificador = hashlib.md5(
            f"{item['titulo']}{item['preco']}{item['link']}".encode("utf-8")
        ).hexdigest()
        if identificador in ids:
            continue
        item["id"] = identificador
        ids.add(identificador)
        novos.append(item)
        dados.append(item)

    if not novos:
        print(f"Domus: {len(cards)} anúncios verificados, nenhum novo.")
        return

    salvar_json(dados, GERAL_JSON)
    exportar = [{k: v for k, v in item.items() if k != "id"} for item in novos]
    gerar_excel(exportar, os.path.join(PATH_GD, EXCEL_FINAL))
    print(f"Domus: {len(novos)} anúncio(s) novo(s).")


if __name__ == "__main__":
    executar()
