"""Coletores configurados para portais que compartilham o mesmo HTML."""

import hashlib
import re
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

from utils.funcs import pegar_json, preco_para_float, salvar_json, limpar_preco
from utils.variables import (
    CIDADES_BUSCA, GERAL_JSON, PRECO_MAX, PRECO_MIN,
    TIPOS_BUSCA, imovel_atende_filtros, normalizar_filtro,
)


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
        "preco_min": None,
        "preco_max": None,
        "preco_seletor": "span.text-lg.font-medium.leading-8",
        "preco_indice": 1,
    },
    "Júlio Estefano": {
        "url": "https://pindamonhangaba.estefanoconsultoria.com.br/busca?finalidade=Aluguel&tipo=Apartamento%2CCasa%2CCasa+em+Condom%C3%ADnio%2CCobertura&cidade=Pindamonhangaba&min=1500.00&max=4500.00",
        "preco_min": None,
        "preco_max": None,
        "preco_seletor": "span.text-lg.font-medium.leading-8",
        "preco_indice": 0,
        "cidade": "pindamonhangaba",
    },
}

# Portais com estruturas próprias; a extração tolera variações de markup entre cards.
PORTAIS_LOCAIS = {
    "Taubaté Imóveis": "taubateimoveis",
    "Jeremias Rodrigues": "jeremiasrodrigues",
    "Única Imóveis": "unicaimoveistaubate",
    "Márcio Santos": "marciosantosimoveis",
    "Imobiliária São Paulo": "imobiliariasp",
    "Unidas Imóveis": "unidasimoveistaubate",
    "Personal Consultoria": "personalimob",
    "Rio Center Imóveis": "imobiliariariocenter",
    "Imobiliária Inovare": "imobiliariainovare",
    "Gomes Nova Opção": "gomesnovaopcaoimoveis",
    "D'Casa Imóveis": "dcasaimoveis",
    "Vista Bela Imóveis": "vistabelaimoveis",
    "Aloisio Imóveis": "aloisioimoveis",
    "Félix Imóveis Especiais": "feliximoveisespeciais",
    "Impera Imóveis": "imperaimoveis",
}

SLUG_CIDADE = {
    "pindamonhangaba": "pindamonhangaba",
    "tremembe": "tremembe",
    "taubate": "taubate",
}
CIDADE_FIXA_PORTAL = {
    "Imobiliária São Paulo": "pindamonhangaba",
    "Unidas Imóveis": "taubate",
    "Personal Consultoria": "taubate",
    "Rio Center Imóveis": "taubate",
    "D'Casa Imóveis": "tremembe",
    "Vista Bela Imóveis": "taubate",
    "Aloisio Imóveis": "taubate",
    "Félix Imóveis Especiais": "taubate",
}


def urls_portal_local(nome):
    """Monta consultas por cidade e tipo a partir dos filtros atuais."""
    urls = []
    for cidade in CIDADES_BUSCA:
        slug = SLUG_CIDADE.get(cidade)
        if not slug:
            continue
        if nome == "Taubaté Imóveis":
            # Este portal anuncia Taubaté e Tremembé; Pindamonhangaba não
            # possui rota própria. A listagem é geral e a cidade vem no cartão.
            if cidade not in {"taubate", "tremembe"}:
                continue
            categorias = set()
            for tipo in TIPOS_BUSCA:
                if tipo in {"comercial", "galpao"}:
                    continue
                if tipo == "apartamento":
                    categorias.add("apartamento")
                elif tipo in {"comercial", "galpao"}:
                    categorias.add("sala" if tipo == "comercial" else "galpao")
                elif tipo in {"terreno", "chacara"}:
                    categorias.add(tipo)
                else:
                    categorias.add("casa")
            urls.extend(
                f"https://www.taubateimoveis.com.br/imoveis/para-alugar/{tipo}"
                for tipo in sorted(categorias)
            )
        elif nome == "Jeremias Rodrigues":
            urls.append(f"https://jeremiasrodrigues.com.br/aluguel/sp/{slug}/")
        elif nome == "Única Imóveis":
            urls.append("https://www.unicaimoveistaubate.com.br/imoveis/para-alugar")
        elif nome == "Márcio Santos":
            categorias = set()
            for tipo in TIPOS_BUSCA:
                if tipo in {"comercial", "galpao"}:
                    continue
                if tipo == "apartamento":
                    categorias.add("apartamentos")
                elif tipo in {"comercial", "galpao"}:
                    categorias.add("comerciais")
                elif tipo == "terreno":
                    categorias.add("terrenos")
                elif tipo == "chacara":
                    categorias.add("chacaras")
                else:
                    categorias.add("casas")
            urls.extend(
                f"https://marciosantosimoveis.com.br/alugar/{slug}-sp/{tipo}"
                for tipo in sorted(categorias)
            )
        elif nome == "Imobiliária São Paulo" and cidade == "pindamonhangaba":
            # O site destaca imóveis para locação na página inicial e usa detalhes
            # estáveis em /imovel/{slug}/{código}.
            urls.append("https://www.imobiliariasp.com.br/")
        elif nome == "Unidas Imóveis" and cidade == "taubate":
            urls.append("https://www.unidasimoveistaubate.com.br/imoveis/para-alugar")
        elif nome == "Personal Consultoria" and cidade == "taubate":
            urls.append("https://personalimob.com.br/imoveis-locacao")
        elif nome == "Rio Center Imóveis" and cidade == "taubate":
            urls.append("https://www.imobiliariariocenter.com.br/imoveis/para-alugar")
        elif nome == "Imobiliária Inovare" and cidade in {"pindamonhangaba", "taubate"}:
            urls.append("https://www.imobiliariainovare.com.br/imovel/locacao")
        elif nome == "Impera Imóveis":
            categorias = set()
            for tipo in TIPOS_BUSCA:
                if tipo in {"comercial", "galpao"}:
                    continue
                if tipo == "apartamento":
                    categorias.add("apartamentos")
                elif tipo == "terreno":
                    categorias.add("terrenos")
                elif tipo == "chacara":
                    categorias.add("rural")
                else:
                    categorias.add("casas")
            urls.extend(
                f"https://www.imperaimoveis.com.br/imoveis/{categoria}/locacao/{slug}"
                for categoria in sorted(categorias)
            )
        elif nome == "Gomes Nova Opção":
            urls.append("https://gomesnovaopcaoimoveis.com.br/imoveis-locacao")
        elif nome == "D'Casa Imóveis" and cidade == "tremembe":
            urls.append("https://www.dcasaimoveis.com.br/imoveis/para-alugar/tremembe")
        elif nome == "Vista Bela Imóveis" and cidade == "taubate":
            urls.append("https://vistabelaimoveis.com.br/")
        elif nome == "Aloisio Imóveis" and cidade == "taubate":
            urls.append("https://www.aloisioimoveis.com.br/imoveis/para-alugar/taubate")
        elif nome == "Félix Imóveis Especiais" and cidade == "taubate":
            urls.append("https://www.feliximoveisespeciais.com/imoveis/para-alugar")
    return list(dict.fromkeys(urls))


def _cidade_no_texto(texto):
    normalizado = normalizar_filtro(texto)
    for slug, nome in (("pindamonhangaba", "Pindamonhangaba"), ("tremembe", "Tremembé"), ("taubate", "Taubaté")):
        if normalizar_filtro(nome) in normalizado or slug in normalizado:
            return slug
    return None


def _preco_card(texto):
    # Prioriza valor associado a aluguel/locação para evitar preço de venda ou condomínio.
    texto = " ".join(texto.split())
    padrao_valor = r"R\$\s*[\d.]+(?:,\d{2})?"
    candidatos = list(re.finditer(padrao_valor, texto, flags=re.I))
    if not candidatos:
        return None
    for match in candidatos:
        contexto = texto[max(0, match.start() - 50):match.start()].casefold()
        if any(palavra in contexto for palavra in ("aluguel", "locação", "locacao", "mensal")):
            return limpar_preco(match.group())
    return limpar_preco(candidatos[0].group())


def coletar_portal_local(session, nome, ids):
    novos = []
    paginas = 0
    urls = urls_portal_local(nome)
    for url in urls:
        urls_pagina = [url]
        if nome == "Jeremias Rodrigues":
            urls_pagina = [url, *(f"{url}?page={n}" for n in range(2, 11))]
        elif nome == "Imobiliária Inovare":
            urls_pagina = [url, f"{url}/?pag=2"]
        elif nome == "Personal Consultoria":
            urls_pagina = [url, *(f"{url}?start={n}" for n in range(40, 561, 40))]
        vistos_na_url = set()
        links_pagina_anterior = None
        for pagina_url in urls_pagina:
            try:
                if nome == "Personal Consultoria":
                    soup = buscar(session, pagina_url, timeout=45, retries=1)
                elif nome == "Jeremias Rodrigues":
                    # O portal pode demorar em páginas além das primeiras. Tenta
                    # novamente e, se uma página posterior continuar indisponível,
                    # preserva o que já foi coletado e segue para as demais imobs.
                    soup = buscar(session, pagina_url, timeout=20, retries=1)
                else:
                    soup = buscar(session, pagina_url)
            except requests.RequestException as erro:
                if nome == "Jeremias Rodrigues" and "page=" in pagina_url:
                    print(
                        f"[WARN] Jeremias Rodrigues: página {pagina_url} indisponível "
                        f"após nova tentativa ({erro}); mantendo os resultados parciais.",
                        flush=True,
                    )
                    break
                raise
            paginas += 1
            encontrados = 0
            marcador_link = "/imoveis-locacao/" if nome == "Gomes Nova Opção" else "/imovel/"
            links_da_pagina = {
                urljoin(pagina_url, ancora.get("href", ""))
                for ancora in soup.select("a[href]")
                if marcador_link in ancora.get("href", "").casefold()
            }
            if nome == "Personal Consultoria" and links_da_pagina == links_pagina_anterior:
                break
            links_pagina_anterior = links_da_pagina
            if nome == "Personal Consultoria" and not links_da_pagina:
                break
            for ancora in soup.select("a[href]"):
                href = ancora.get("href", "")
                marcador_link = "/imoveis-locacao/" if nome == "Gomes Nova Opção" else "/imovel/"
                if marcador_link not in href.casefold():
                    continue
                link = urljoin(pagina_url, href)
                if link in vistos_na_url:
                    continue
                vistos_na_url.add(link)
                # Escolhe o menor ancestral que contenha título e preço, limitado para
                # evitar capturar texto de toda a página como se fosse um cartão.
                candidatos = []
                no = ancora
                for _ in range(7):
                    if no is None:
                        break
                    texto = no.get_text(" ", strip=True)
                    if len(texto) >= 15 and _preco_card(texto):
                        candidatos.append((len(texto), no, texto))
                    no = no.parent
                if not candidatos:
                    continue
                _, card, texto = min(candidatos, key=lambda item: item[0])
                titulo_tag = card.select_one("h1, h2, h3, h4, [class*=title], [class*=titulo]")
                titulo = (titulo_tag.get_text(" ", strip=True) if titulo_tag else ancora.get_text(" ", strip=True))
                if not titulo or len(titulo) < 4:
                    titulo = card.get("title", "")
                preco = _preco_card(texto)
                cidade = _cidade_no_texto(texto)
                # Consultas segregadas têm cidade conhecida; os catálogos gerais
                # precisam informar a cidade no próprio cartão.
                path_cidade = next((slug for slug in SLUG_CIDADE if f"/{slug}" in urlparse(url).path), None)
                cidade = cidade or path_cidade or CIDADE_FIXA_PORTAL.get(nome)
                if nome == "Única Imóveis" and cidade is None:
                    continue
                if not imovel_atende_filtros(f"{titulo} {texto}", preco, link, cidade):
                    continue
                registro = criar_registro(titulo, preco, link, paginas, ids)
                if registro:
                    novos.append(registro)
                    encontrados += 1
            # Nas páginas paginadas da Jeremias, termina no primeiro resultado vazio.
            if nome == "Jeremias Rodrigues" and "page=" in pagina_url and encontrados == 0:
                break
    return novos, paginas


def buscar(session, url, timeout=30, retries=0):
    print(f"[HTTP] GET {url}", flush=True)
    resposta = None
    for tentativa in range(retries + 1):
        try:
            resposta = session.get(url, headers=HEADERS, timeout=timeout)
            break
        except requests.Timeout:
            if tentativa >= retries:
                raise
            print(
                f"[HTTP] Timeout em {url}; tentando novamente ({tentativa + 1}/{retries})",
                flush=True,
            )
    if resposta is None:
        raise requests.RequestException(f"Não foi possível obter resposta de {url}")
    resposta.raise_for_status()
    print(
        f"[HTTP] {resposta.status_code} · {len(resposta.content)} bytes recebidos",
        flush=True,
    )
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
        url = re.sub(r"vmi=[^&]*", f"vmi={int(PRECO_MIN)}", url)
        url = re.sub(r"vma=[^&]*", f"vma={int(PRECO_MAX)}", url)
        cidade_url = next(
            (cidade for cidade in SLUG_CIDADE if f"/{cidade}/" in urlparse(url).path or f"/{cidade}?" in urlparse(url).path),
            None,
        )
        if cidade_url and cidade_url not in CIDADES_BUSCA:
            continue
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
                cidade = cidade_url or _cidade_no_texto(card.get_text(" ", strip=True))
                if cidade is None and len(CIDADES_BUSCA) < len(SLUG_CIDADE):
                    continue
                if not imovel_atende_filtros(titulo, preco, link, cidade):
                    continue
                registro = criar_registro(titulo, preco, link, pagina, ids)
                if registro:
                    novos.append(registro)
    return novos, paginas_verificadas


def coletar_tailwind(session, config, ids):
    url = re.sub(r"([?&])min=[^&]*", rf"\g<1>min={PRECO_MIN:.2f}", config["url"])
    url = re.sub(r"([?&])max=[^&]*", rf"\g<1>max={PRECO_MAX:.2f}", url)
    soup = buscar(session, url)
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
        link = urljoin(url, card.get("href", ""))
        titulo = titulo_tag.get_text(" ", strip=True)
        cidade = config.get("cidade") or _cidade_no_texto(card.get_text(" ", strip=True))
        if cidade is None and len(CIDADES_BUSCA) < len(SLUG_CIDADE):
            continue
        if not imovel_atende_filtros(titulo, preco, link, cidade):
            continue
        registro = criar_registro(
            titulo, preco, link, 1, ids
        )
        if registro:
            novos.append(registro)
    return novos, 1


def main(portais=None):
    estado = pegar_json(GERAL_JSON)
    ids, dados = estado["ids"], estado["dados"]
    novos_total = []
    falhas = []
    selecionados = set(portais or [*PORTAIS_CARD, *PORTAIS_TAILWIND, *PORTAIS_LOCAIS])
    with requests.Session() as session:
        for nome, config in PORTAIS_CARD.items():
            if nome not in selecionados:
                continue
            try:
                novos, paginas = coletar_card_portal(session, config, ids)
                for item in novos:
                    dados.append(item)
                novos_total.extend(novos)
                print(f"{nome}: {len(novos)} novo(s), {paginas} página(s).")
            except Exception as erro:
                falhas.append((nome, erro))
                print(f"{nome}: falha na consulta: {erro}")

        for nome, config in PORTAIS_TAILWIND.items():
            if nome not in selecionados:
                continue
            try:
                novos, paginas = coletar_tailwind(session, config, ids)
                for item in novos:
                    dados.append(item)
                novos_total.extend(novos)
                print(f"{nome}: {len(novos)} novo(s), {paginas} página(s).")
            except Exception as erro:
                falhas.append((nome, erro))
                print(f"{nome}: falha na consulta: {erro}")

        for nome in PORTAIS_LOCAIS:
            if nome not in selecionados:
                continue
            try:
                novos, paginas = coletar_portal_local(session, nome, ids)
                dados.extend(novos)
                novos_total.extend(novos)
                print(f"{nome}: {len(novos)} novo(s), {paginas} página(s).")
            except Exception as erro:
                falhas.append((nome, erro))
                print(f"{nome}: falha na consulta: {erro}")

    if novos_total:
        salvar_json(dados, GERAL_JSON)
    if falhas:
        raise RuntimeError(f"Falharam {len(falhas)} portal(is) do coletor genérico.")


if __name__ == "__main__":
    import argparse

    portais_disponiveis = [*PORTAIS_CARD, *PORTAIS_TAILWIND, *PORTAIS_LOCAIS]
    parser = argparse.ArgumentParser(description="Coleta anúncios de portais configurados.")
    parser.add_argument(
        "--portal", action="append", choices=portais_disponiveis,
        help="Executa somente o portal informado; pode ser repetido.",
    )
    main(parser.parse_args().portal)
