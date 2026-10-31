from bs4 import BeautifulSoup
import hashlib
import json
import re
from urllib.parse import urljoin

import requests

from utils.funcs import *
from utils.variables import *


URL = (
    "https://www.palaceteimobiliaria.com.br/imoveis/para-alugar/"
    "apartamento+casa+sobrado/sao-paulo-pindamonhangaba-sp"
    f"?precolocacao={int(PRECO_MIN)}--{int(PRECO_MAX)}&mobilia=n%C3%A3o&muncep_id=7001"
    "&search_name=Pindamonhangaba&localidade=SP&toggle_map=true"
    "&propertySubtypes=55&propertySubtypes=64&propertySubtypes=50"
    "&propertySubtypes=120&propertySubtypes=350&propertySubtypes=346"
    "&propertySubtypes=19&propertySubtypes=320&propertySubtypes=321"
    "&propertySubtypes=325&propertySubtypes=169&order=mais_relevantes"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def texto_do(elemento):
    return elemento.get_text(" ", strip=True) if elemento else None


def encontrar_cards(soup):
    # A classe principal pode ser aplicada a div ou li conforme a versão do site.
    seletores = (
        "li.Imoveis_cardDisplay__e0Dc8",
        "div.Imoveis_cardDisplay__e0Dc8",
        "[class*='Imoveis_cardDisplay']",
    )
    cards = []
    vistos = set()
    for seletor in seletores:
        for card in soup.select(seletor):
            identidade = str(card)
            if identidade not in vistos:
                vistos.add(identidade)
                cards.append(card)
        if cards:
            break
    return cards


def extrair_preco(card):
    # Primeiro tenta o seletor usado no script original.
    for bloco in card.select(
        "div.ImovelCardInfo_sizeOfPrices__SyQDF div, "
        "[class*='sizeOfPrices'] div"
    ):
        spans = bloco.find_all("span")
        if len(spans) >= 2 and "aluguel" in texto_do(spans[0]).lower():
            valor = limpar_preco(texto_do(spans[1]))
            if valor:
                return valor

    # Alternativa: localizar textos que indiquem o valor do aluguel.
    for elemento in card.find_all(["span", "div", "p"]):
        conteudo = texto_do(elemento) or ""
        if re.search(r"aluguel", conteudo, re.IGNORECASE):
            match = re.search(
                r"R\$\s*[\d.]+(?:,\d{2})?",
                conteudo,
                re.IGNORECASE,
            )
            if match:
                valor = limpar_preco(match.group(0))
                if valor:
                    return valor
    return None


def extrair_titulo(card):
    # Mantém a preferência original pelo alt da imagem.
    img = card.find("img", alt=True)
    titulo = (img.get("alt") or "").strip() if img else ""
    if titulo:
        return titulo

    for seletor in (
        "[class*='colorOfTitleCondominium']",
        "[class*='Title']",
        "h2",
        "h3",
    ):
        elemento = card.select_one(seletor)
        titulo = texto_do(elemento)
        if titulo:
            return titulo
    return None


def executar():
    json_data = pegar_json(GERAL_JSON)
    ids = set(json_data.get("ids", []))
    dados = json_data.get("dados", [])
    if not isinstance(dados, list):
        raise ValueError("O campo 'dados' do JSON precisa ser uma lista.")

    try:
        resposta = requests.get(URL, headers=HEADERS, timeout=30)
        resposta.raise_for_status()
    except requests.RequestException as erro:
        raise RuntimeError(f"Falha ao acessar o site da Palacete: {erro}") from erro

    soup = BeautifulSoup(resposta.text, "html.parser")
    cards = encontrar_cards(soup)

    if not cards:
        titulo_pagina = texto_do(soup.title) or "(sem título)"
        trecho = soup.get_text(" ", strip=True)[:400]
        raise RuntimeError(
            "Nenhum card de imóvel foi encontrado no HTML recebido. "
            f"Título da página: {titulo_pagina}. Conteúdo inicial: {trecho}"
        )

    imoveis = []
    pg = 1
    incompletos = 0
    fora_dos_filtros = 0
    duplicados = 0

    for card in cards:
        tag_link = card.find("a", href=True)
        link = urljoin(URL, tag_link["href"]) if tag_link else None
        titulo = extrair_titulo(card)
        preco = extrair_preco(card)

        # Não concatena valores ausentes: isso causava TypeError.
        if not titulo or not link or not preco:
            incompletos += 1
            continue
        if not imovel_atende_filtros(titulo, preco, link, "pindamonhangaba"):
            fora_dos_filtros += 1
            continue

        chave = f"{titulo}|{preco}|{link}"
        _id = hashlib.md5(chave.encode("utf-8")).hexdigest()

        if _id in ids:
            duplicados += 1
            continue

        imov = {
            "id": _id,
            "titulo": titulo,
            "preco": preco,
            "link": link,
            "pagina": pg,
        }
        imoveis.append(imov)
        dados.append(imov)
        ids.add(_id)

    # Se nenhum anúncio foi extraído, não altera o JSON nem gera planilha vazia.
    if not imoveis:
        print(
            f"Palacete: {len(cards)} cards verificados; sem anúncios novos "
            f"({incompletos} incompletos, {fora_dos_filtros} fora dos filtros, "
            f"{duplicados} duplicados)."
        )
        return

    salvar_json(dados, GERAL_JSON)

    print(f"Palacete: {len(imoveis)} novo(s) imóvel(is) adicionado(s).")


if __name__ == "__main__":
    executar()
