from utils.collection_errors import continue_on_error
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import requests
import hashlib
import json
import math
import re
import sys

from utils.funcs import *
from utils.variables import *

BASE_URL = "https://derricoimoveis.com.br/imoveis/aluguel"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}
TIMEOUT = 25


def get_soup(session, url):
    """Baixa uma página e falha claramente em caso de erro HTTP/rede."""
    response = session.get(url, timeout=TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.title.get_text(" ", strip=True) if soup.title else "sem título"
    if not soup.get_text(" ", strip=True):
        raise RuntimeError(f"A página veio vazia: {url}")
    return soup, response.url, title


def find_cards(soup):
    """Aceita o seletor antigo e algumas variações comuns do HTML."""
    selectors = [
        "div.ImovelItem",
        "[class~='ImovelItem']",
        "div[class*='ImovelItem']",
    ]
    for selector in selectors:
        cards = soup.select(selector)
        if cards:
            return cards

    # Fallback: encontra links de título e sobe até um contêiner de anúncio.
    cards = []
    seen = set()
    for title_link in soup.select("a.Title, a[class*='Title']"):
        parent = title_link
        for _ in range(6):
            if parent is None:
                break
            classes = " ".join(parent.get("class", []))
            if any(token.lower() in classes.lower() for token in ("imovel", "property", "listing", "card")):
                marker = id(parent)
                if marker not in seen:
                    cards.append(parent)
                    seen.add(marker)
                break
            parent = parent.parent
    return cards


def get_title_link(card):
    link = card.select_one("a.Title, a[class*='Title']")
    if link is None:
        # Fallback para links que contenham o texto do anúncio.
        for candidate in card.select("a[href]"):
            label = candidate.get_text(" ", strip=True)
            if len(label) > 12 and "whatsapp" not in label.lower():
                link = candidate
                break
    if link is None:
        return None, None

    title = link.get_text(" ", strip=True)
    href = link.get("href")
    return title or None, urljoin(BASE_URL, href) if href else None


def get_price(card):
    selectors = [
        ".ImovelValor .value",
        ".ImovelValor",
        ".value",
        "[class*='Valor'] .value",
        "[class*='valor'] .value",
    ]
    for selector in selectors:
        tag = card.select_one(selector)
        if tag:
            text = tag.get_text(" ", strip=True)
            match = re.search(r"R\$\s*[\d.]+(?:,\d{2})?", text)
            if match:
                return limpar_preco(match.group(0))

    # O tema do site também pode exibir o preço sem o seletor conhecido.
    match = re.search(r"R\$\s*[\d.]+(?:,\d{2})?", card.get_text(" ", strip=True))
    return limpar_preco(match.group(0)) if match else None


def executar():
    estado = pegar_json(GERAL_JSON)
    ids = estado["ids"]
    dados = estado["dados"]
    with requests.Session() as session:
        soup, _, titulo_pagina = get_soup(session, BASE_URL)
        cards = find_cards(soup)
        if not cards:
            raise RuntimeError(
                f"D'Errico: nenhum anúncio encontrado; página recebida: {titulo_pagina}"
            )

        novos = []
        for card in cards:
            with continue_on_error('derrico: anúncio'):
                titulo, link = get_title_link(card)
                preco = get_price(card)
                if not titulo or not link or not preco:
                    continue
                if not imovel_atende_filtros(titulo, preco, link, "pindamonhangaba"):
                    continue

                identificador = hashlib.md5(
                    f"{titulo}{preco}{link}".encode("utf-8")
                ).hexdigest()
                if identificador in ids:
                    continue

                item = {
                    "id": identificador,
                    "titulo": titulo,
                    "preco": preco,
                    "link": link,
                    "pagina": 1,
                }
                ids.add(identificador)
                dados.append(item)
                novos.append(item)

    if not novos:
        print(f"D'Errico: {len(cards)} anúncios verificados, nenhum novo.")
        return

    salvar_json(dados, GERAL_JSON)
    print(f"D'Errico: {len(novos)} anúncio(s) novo(s).")


if __name__ == "__main__":
    executar()
