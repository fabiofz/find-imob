"""Coletores configurados para portais que compartilham o mesmo HTML."""

import hashlib
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from utils.funcs import gerar_excel, pegar_json, preco_para_float, salvar_json, limpar_preco
from utils.variables import EXCEL_FINAL, GERAL_JSON, PATH_GD


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# Estes portais usam cartões .imovelcard com a mesma estrutura de título,
# preço e link. As URLs continuam separadas para manter seus filtros.
PORTAIS_CARD = {
    "Erida Vieira": {"urls": [
        "https://eridavieira.com.br/imovel/locacao/casa/pindamonhangaba/?&vmi=1500&vma=4500",
        "https://eridavieira.com.br/imovel/locacao/apartamento/pindamonhangaba/?&vmi=1500&vma=4500",
        "https://eridavieira.com.br/imovel/locacao/casa-em-condominio/pindamonhangaba/?&vmi=1500&vma=4500",
    ]},
    "Palazzo Reale": {"urls": [
        "https://www.palazzorealeimoveis.com.br/imovel/locacao/casa/pindamonhangaba/?&vmi=1500&vma=4500",
        "https://www.palazzorealeimoveis.com.br/imovel/locacao/apartamento/pindamonhangaba/?&vmi=1500&vma=4500",
        "https://www.palazzorealeimoveis.com.br/imovel/locacao/sobrado/pindamonhangaba/?&vmi=1500&vma=4500",
    ]},
    "DNA": {"urls": [
        f"https://www.imoveisdna.com.br/imovel/locacao/{tipo}/{cidade}/?&vmi=1500&vma=4500"
        for cidade in ("pindamonhangaba", "taubate")
        for tipo in ("apartamento", "casa", "casa-em-condominio", "sobrado", "casa-terrea")
    ]},
    "Nova Cabana": {"urls": [
        "https://www.novacabana.com.br/imovel/locacao/casa/?&vmi=1500&vma=4500",
        "https://www.novacabana.com.br/imovel/locacao/apartamento/?&vmi=1500&vma=4500",
        "https://www.novacabana.com.br/imovel/locacao/casa-em-condominio/?&vmi=1500&vma=4500",
    ]},
    "Edifficatho": {"urls": [
        f"https://www.edifficatho.com.br/imovel/locacao/{tipo}/pindamonhangaba/?&vmi=2000&vma=4500"
        for tipo in ("apartamento", "casa", "sobrado", "casa-em-condominio")
    ]},
    "Simob": {"paginado": True, "urls": [
        "https://www.simobsolucoesimobiliarias.com.br/imovel/locacao/apartamento/pindamonhangaba/?&vmi=2000&vma=4500",
        "https://www.simobsolucoesimobiliarias.com.br/imovel/locacao/casa/pindamonhangaba/?&vmi=2000&vma=4500",
    ]},
}

PORTAIS_TAILWIND = {
    "012 Imóveis": {
        "url": "https://012imoveis.com.br/busca?finalidade=Aluguel&tipo=Apartamento%2CCasa%2CCasa+em+Condom%C3%ADnio%2CSobrado",
        "preco_min": 2000,
        "preco_max": 4500,
        "preco_seletor": "span.text-lg.font-medium.leading-8",
        "preco_indice": 1,
    },
    "Júlio Estefano": {
        "url": "https://pindamonhangaba.estefanoconsultoria.com.br/busca?finalidade=Aluguel&tipo=Apartamento%2CCasa%2CCasa+em+Condom%C3%ADnio%2CCobertura&cidade=Pindamonhangaba&min=1500.00&max=2000.00",
        "preco_min": None,
        "preco_max": None,
        "preco_seletor": "span.text-lg.font-medium.leading-8",
        "preco_indice": 0,
    },
}


def buscar(session, url):
    resposta = session.get(url, headers=HEADERS, timeout=30)
    resposta.raise_for_status()
    return BeautifulSoup(resposta.text, "html.parser")


def criar_registro(titulo, preco, link, pagina, ids):
    if not titulo or not preco or not link:
        return None
    identificador = hashlib.md5(f"{titulo}{preco}{link}".encode("utf-8")).hexdigest()
    if identificador in ids:
        return None
    ids.add(identificador)
    return {
        "id": identificador,
        "titulo": titulo,
        "preco": preco,
        "link": link,
        "pagina": pagina,
    }


def coletar_card_portal(session, config, ids):
    novos = []
    paginas_verificadas = 0
    paginado = config.get("paginado", False)
    for url in config["urls"]:
        primeira_url = f"{url}&pag=1" if paginado else url
        soup = buscar(session, primeira_url)
        total_paginas = 1
        if paginado:
            numeros = [
                int(a.get_text(strip=True))
                for a in soup.select(".lipagina-btn-paginacao-atual")
                if a.get_text(strip=True).isdigit()
            ]
            total_paginas = max(numeros, default=1)

        for pagina in range(1, total_paginas + 1):
            if pagina > 1:
                soup = buscar(session, f"{url}&pag={pagina}")
            paginas_verificadas += 1
            for card in soup.select(".imovelcard"):
                ancora = card.select_one("a.imovelcard__img")
                preco_tag = card.select_one(".imovelcard__valor__valor")
                if not ancora or not preco_tag:
                    continue
                titulo = ancora.get("title")
                preco = limpar_preco(preco_tag.get_text(" ", strip=True))
                link = urljoin(url, ancora.get("href", ""))
                registro = criar_registro(titulo, preco, link, pagina, ids)
                if registro:
                    novos.append(registro)
    return novos, paginas_verificadas


def coletar_tailwind(session, nome, config, ids):
    soup = buscar(session, config["url"])
    novos = []
    cards = soup.select("a.flex.flex-col.bg-white.rounded-xl.h-full.relative")
    for card in cards:
        titulo_tag = card.select_one(".line-clamp-1")
        precos = card.select(config["preco_seletor"])
        indice = config["preco_indice"]
        if not titulo_tag or len(precos) <= indice:
            continue
        preco = limpar_preco(precos[indice].get_text(" ", strip=True))
        valor = preco_para_float(preco)
        if config["preco_min"] is not None and (
            valor is None or valor < config["preco_min"] or valor > config["preco_max"]
        ):
            continue
        link = urljoin(config["url"], card.get("href", ""))
        registro = criar_registro(
            titulo_tag.get_text(" ", strip=True), preco, link, 1, ids
        )
        if registro:
            novos.append(registro)
    return novos, 1


def main():
    estado = pegar_json(GERAL_JSON)
    ids, dados = estado["ids"], estado["dados"]
    novos_total = []
    falhas = []
    with requests.Session() as session:
        for nome, config in PORTAIS_CARD.items():
            try:
                novos, paginas = coletar_card_portal(session, config, ids)
                for item in novos:
                    dados.append(item)
                novos_total.extend(novos)
                print(f"{nome}: {len(novos)} novo(s), {paginas} página(s).")
            except requests.RequestException as erro:
                falhas.append((nome, erro))
                print(f"{nome}: falha na consulta: {erro}")

        for nome, config in PORTAIS_TAILWIND.items():
            try:
                novos, paginas = coletar_tailwind(session, nome, config, ids)
                for item in novos:
                    dados.append(item)
                novos_total.extend(novos)
                print(f"{nome}: {len(novos)} novo(s), {paginas} página(s).")
            except requests.RequestException as erro:
                falhas.append((nome, erro))
                print(f"{nome}: falha na consulta: {erro}")

    if novos_total:
        salvar_json(dados, GERAL_JSON)
        exportar = [
            {chave: valor for chave, valor in item.items() if chave != "id"}
            for item in novos_total
        ]
        gerar_excel(exportar, f"{PATH_GD}{EXCEL_FINAL}")
    if falhas:
        raise RuntimeError(f"Falharam {len(falhas)} portal(is) do coletor genérico.")


if __name__ == "__main__":
    main()
