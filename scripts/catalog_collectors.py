"""Coletores configurados para portais que compartilham o mesmo HTML."""
from utils.collection_errors import continue_on_error, collect_errors
import hashlib
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import database
import cloud_store
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse, quote

import requests
from bs4 import BeautifulSoup

from utils.funcs import pegar_json, preco_para_float, salvar_json, limpar_preco, registrar_erro_coleta
from utils.variables import (
    CIDADES_BUSCA, GERAL_JSON, PRECO_MAX, PRECO_MIN,
    TIPOS_BUSCA, imovel_atende_filtros, normalizar_filtro, cidade_selecionada,
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

# Catálogos de locação com cartões Kenlo ou Voa (Pinda Prime).
PORTAIS_SJC = {
    'Domus Imóveis SJC': "https://www.domusimoveissjc.com.br/imoveis/para-alugar/sao-jose-dos-campos",
    'Prime Imóveis SJC': "https://www.primeimoveissjc.com.br/imoveis/para-alugar/sao-jose-dos-campos",
    'Unike Imóveis': "https://www.unikeimoveis.com.br/imoveis/para-alugar/sao-jose-dos-campos",
    'AZV Imóveis': "https://azvimoveis.com.br/imoveis/para-alugar",
}

PORTAIS_LOCACAO = {
    **PORTAIS_SJC,
    'Pinda Prime': "https://www.pindaprime.com.br/imoveis/?disponibilidade=para-alugar",
    'Berith Imóveis': "https://www.berithimoveis.com.br/imoveis/para-alugar",
    'Ricardo Monteiro Imóveis': "https://www.ricardomonteiroimoveis.com.br/imoveis/para-alugar",
    'Batista Imóveis': "https://www.batistaimoveispinda.com.br/imoveis/para-alugar",
    'Grothe & Lima': "https://www.grothelimaimoveis.com.br/imoveis/para-alugar",
    'Meta Negócios Imobiliários': "https://www.metanegociosimobiliarios.com.br/imoveis/para-alugar",
    'Max Gold': "https://www.maxgold.imb.br/imoveis/para-alugar",
}

# Portais com estruturas próprias; a extração tolera variações de markup entre cards.
PORTAIS_INDISPONIVEIS = {
    "Imobiliária Guerrero": "O domínio cadastrado agora atende Vitória (ES). Aguardando um endereço confirmado de Pindamonhangaba.",
}

PORTAIS_LOCAIS = {
    **PORTAIS_LOCACAO,
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
    "Sales Imóveis": "salesimoveis",
    "Euro Imóveis": "euroimoveis",
    "Imobiliária Danelli": "danelli",
    "ATOM Inteligência Imobiliária": "atomimobiliaria",
    "City Taubaté Imobiliária": "citytaubate",
    "Solar Imóveis Taubaté": "solarimoveistaubate",
    "Salzano Imóveis": "salzanoimoveis",
    "Teomi Imóveis": "teomiimoveis",
    "Go Home Soluções Imobiliárias": "gohomebrasil",
    "BS Negócios Imobiliários": "bsimoveistaubate",
    "Vilella Imóveis": "vilellaimoveis",
    "Universo Ello Imóveis": "universoello",
    "Imobiliária Apolo": "apolo",
    "Imobiliária Guerrero": "imobiliariaguerrero",
    "Saframa Imóveis": "saframa",
    "Imobiliária Aliança": "alianca",
}

MARCADORES_LINK_PORTAL = {
    "Sales Imóveis": ("/imoveis/locacao-",),
}

SLUG_CIDADE = {
    "pindamonhangaba": "pindamonhangaba",
    "tremembe": "tremembe",
    "taubate": "taubate",
    "sao-jose-dos-campos": "sao-jose-dos-campos",
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
    "Sales Imóveis": "taubate",
    "Euro Imóveis": "taubate",
    "Imobiliária Danelli": "taubate",
    "ATOM Inteligência Imobiliária": "taubate",
    "City Taubaté Imobiliária": "taubate",
    "Solar Imóveis Taubaté": "taubate",
    "Salzano Imóveis": "taubate",
    "Teomi Imóveis": "taubate",
    "Go Home Soluções Imobiliárias": "taubate",
    "BS Negócios Imobiliários": "taubate",
    "Vilella Imóveis": "pindamonhangaba",
    "Universo Ello Imóveis": "pindamonhangaba",
    "Imobiliária Apolo": "pindamonhangaba",
    "Imobiliária Guerrero": "pindamonhangaba",
    "Saframa Imóveis": "pindamonhangaba",
    "Imobiliária Aliança": "pindamonhangaba",
}


def urls_portal_local(nome):
    """Monta consultas por cidade e tipo a partir dos filtros atuais."""
    if nome in PORTAIS_LOCACAO:
        if nome in PORTAIS_SJC and not cidade_selecionada("sao-jose-dos-campos"):
            return []
        url = PORTAIS_LOCACAO[nome]
        if nome not in {"Pinda Prime", "AZV Imóveis", "Batista Imóveis"}:
            url += f"?preco-de-locacao={int(PRECO_MIN)}~{int(PRECO_MAX)}"
        return [url]
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
        elif nome == "Sales Imóveis" and cidade == "taubate":
            urls.append("https://www.salesimoveis.imb.br/")
        elif nome == "Euro Imóveis" and cidade == "taubate":
            urls.append("https://www.euroimoveis.cim.br/imoveis?finalidade=aluguel")
        elif nome == "Imobiliária Danelli" and cidade == "taubate":
            urls.append("https://www.danelli.com.br/aluguel/")
        elif nome == "ATOM Inteligência Imobiliária" and cidade == "taubate":
            urls.append("https://www.atomimobiliaria.com.br/")
        elif nome == "City Taubaté Imobiliária" and cidade == "taubate":
            urls.append("https://www.citytaubate.com.br/")
        elif nome == "Solar Imóveis Taubaté" and cidade == "taubate":
            urls.append("https://www.solarimoveistaubate.com.br/imoveis/para-alugar")
        elif nome == "Salzano Imóveis" and cidade == "taubate":
            urls.append("https://www.salzanoimoveis.com.br/")
        elif nome == "Teomi Imóveis" and cidade == "taubate":
            urls.append("https://www.teomiimoveis.com.br/")
        elif nome == "Go Home Soluções Imobiliárias" and cidade == "taubate":
            urls.append("https://gohomebrasil.com.br/busca")
        elif nome == "BS Negócios Imobiliários" and cidade == "taubate":
            urls.append("https://bsimoveistaubate.com.br/")
        elif nome == "Vilella Imóveis" and cidade == "pindamonhangaba":
            urls.append("https://www.vilellaimoveis.com.br/aluguel/")
        elif nome == "Universo Ello Imóveis" and cidade == "pindamonhangaba":
            urls.append("https://universoello.com.br/")
        elif nome == "Imobiliária Guerrero" and cidade == "pindamonhangaba":
            urls.append("https://www.imobiliariaguerrero.com.br/")
        elif nome == "Saframa Imóveis" and cidade == "pindamonhangaba":
            urls.append("https://www.saframa.com.br/")
    return list(dict.fromkeys(urls))


def _cidade_no_texto(texto):
    normalizado = normalizar_filtro(texto)
    for slug, nome in (("pindamonhangaba", "Pindamonhangaba"), ("tremembe", "Tremembé"), ("taubate", "Taubaté"), ("sao-jose-dos-campos", "São José dos Campos")):
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


def coletar_portal_local(session, nome, ids, on_records=None):
    if nome in PORTAIS_INDISPONIVEIS:
        raise ValueError(PORTAIS_INDISPONIVEIS[nome])
    if nome == "Imobiliária Danelli":
        return coletar_danelli(session, ids, on_records=on_records)
    if nome in PORTAIS_LOCACAO:
        return coletar_catalogo_locacao(session, nome, ids, on_records=on_records)
    novos = []
    paginas = 0
    urls = urls_portal_local(nome)
    marcadores_link = MARCADORES_LINK_PORTAL.get(nome, ("/imovel/",))
    for url in urls:
        with continue_on_error('Catálogo: página'):
            urls_pagina = [url]
            if nome == "Jeremias Rodrigues":
                urls_pagina = [url, *(f"{url}?page={n}" for n in range(2, 11))]
            elif nome == "Personal Consultoria":
                urls_pagina = [url, *(f"{url}?start={n}" for n in range(40, 561, 40))]
            vistos_na_url = set()
            links_pagina_anterior = None
            for pagina_url in urls_pagina:
                with continue_on_error('Catálogo: página'):
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
                    if nome == "Imobiliária Inovare" and pagina_url == url:
                        # Follow the pagination advertised by the site, rather than
                        # requesting a second page even when it no longer exists.
                        for anchor in soup.select("a[href]"):
                            next_url = urljoin(url, anchor["href"])
                            parsed = urlparse(next_url)
                            page = parse_qs(parsed.query).get("pag", [""])[0]
                            if (parsed.netloc == urlparse(url).netloc
                                    and parsed.path.rstrip("/") == urlparse(url).path.rstrip("/")
                                    and page.isdigit() and 2 <= int(page) <= 10
                                    and next_url not in urls_pagina):
                                urls_pagina.append(next_url)
                    paginas += 1
                    encontrados = 0
                    marcadores_pagina = ("/imoveis-locacao/",) if nome == "Gomes Nova Opção" else marcadores_link
                    links_da_pagina = {
                        urljoin(pagina_url, ancora.get("href", ""))
                        for ancora in soup.select("a[href]")
                        if any(marcador in ancora.get("href", "").casefold() for marcador in marcadores_pagina)
                    }
                    if nome == "Personal Consultoria" and links_da_pagina == links_pagina_anterior:
                        break
                    links_pagina_anterior = links_da_pagina
                    if nome == "Personal Consultoria" and not links_da_pagina:
                        break
                    for ancora in soup.select("a[href]"):
                        with continue_on_error('Catálogo: anúncio'):
                            href = ancora.get("href", "")
                            marcadores_ancora = ("/imoveis-locacao/",) if nome == "Gomes Nova Opção" else marcadores_link
                            if not any(marcador in href.casefold() for marcador in marcadores_ancora):
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
                    if on_records:
                        with continue_on_error("Salvar página do catálogo"):
                            on_records(novos)
                    # Duplicate IDs must not terminate pagination: there may be new
                    # properties on later pages. Stop only when no property links exist.
                    if nome == "Jeremias Rodrigues" and "page=" in pagina_url and not links_da_pagina:
                        break
    return novos, paginas



def coletar_danelli(session, ids, on_records=None):
    """Use the public JSON search that replaced Danelli's old HTML routes."""
    base = "https://www.danelli.com.br/"
    buscar(session, base + "aluguel/")
    novos, vistos = [], set()
    paginas = 0
    for pagina in range(1, 31):
        with continue_on_error('Catálogo: página'):
            response = session.post(
                base + "retornar-imoveis-disponiveis", headers={**HEADERS, "Referer": base + "aluguel/"},
                data={"finalidade": "aluguel", "numeropagina": pagina, "numeroregistros": 20,
                      "valorde": f"{PRECO_MIN:.2f}".replace(".", ","),
                      "valorate": f"{PRECO_MAX:.2f}".replace(".", ","), "opcaoimovel": 0},
                timeout=(5, 20),
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get("lista"), list):
                raise ValueError("Danelli retornou um formato de catálogo não reconhecido.")
            paginas += 1
            items = data["lista"]
            if not items:
                break
            codigos = {str(item.get("codigo")) for item in items}
            if codigos.issubset(vistos):
                break
            vistos.update(codigos)
            for item in items:
                with continue_on_error('Catálogo: anúncio'):
                    if str(item.get("codigofinalidade")) != "1":
                        continue
                    cidade = _cidade_no_texto(item.get("cidade", ""))
                    if not cidade:
                        continue
                    titulo = str(item.get("titulo") or f"{item.get('tipo', '')} - {item.get('bairro', '')} - {item.get('cidade', '')}")
                    preco = _preco_card(str(item.get("valor", "")))
                    slug, codigo = item.get("url_amigavel"), item.get("codigo")
                    if not slug or not codigo:
                        continue
                    link = base + "imovel/" + quote(str(slug), safe="-") + "/" + quote(str(codigo), safe="")
                    if not imovel_atende_filtros(f"{item.get('tipo', '')} {titulo}", preco, link, cidade):
                        continue
                    registro = criar_registro(titulo, preco, link, pagina, ids)
                    if registro:
                        novos.append(registro)
            if on_records:
                with continue_on_error("Salvar página do catálogo"):
                    on_records(novos)
            if pagina * 20 >= int(data.get("quantidade", 0)):
                break
    return novos, paginas


def extrair_cartao_locacao(card, pagina_url):
    """Lê apenas o valor de aluguel do cartão, separado de venda e taxas."""
    link = urljoin(pagina_url, card.get("href", ""))
    if urlparse(link).netloc != urlparse(pagina_url).netloc:
        return None
    if "property-card-link" in card.get("class", []):
        card = card.find_parent(class_="thumbnail_one") or card
    texto = card.get_text(" ", strip=True)
    preco = None
    # Os dois layouts Kenlo mantêm finalidade e preço no mesmo contêiner.
    for container in card.select('[class$="__value-container"]'):
        label = container.select_one('[class$="__value-title"]')
        valor = container.select_one('[class$="__value"]')
        if label and valor and normalizar_filtro(label.get_text()) == "aluguel":
            if re.search(r"/\s*(dia|diaria|semana)", valor.get_text(), re.I):
                return None
            preco = _preco_card(valor.get_text(" ", strip=True))
            break
    tipo = card.select_one('.card-with-buttons__title, .card_split_vertically__type')
    local = card.select_one('h2')
    if tipo and local:
        titulo = f"{tipo.get_text(' ', strip=True)} - {local.get_text(' ', strip=True)}"
    elif card.select_one('.property_pricing'):
        finalidade = card.select_one('.Featured')
        titulo_tag = card.select_one('.property_card_heading')
        valor = card.select_one('.property_pricing')
        if not titulo_tag:
            return None
        if finalidade and normalizar_filtro(finalidade.get_text()) != "para alugar":
            return None
        if "para alugar" not in normalizar_filtro(titulo_tag.get_text()):
            return None
        if re.search(r"/\s*(dia|diaria|semana)", valor.get_text(), re.I):
            return None
        titulo = titulo_tag.get_text(" ", strip=True)
        preco = _preco_card(valor.get_text(" ", strip=True))
    else:
        # A listagem Voa separa o título e o preço nos campos h3 e .price.
        titulo_tag = card.select_one('h3')
        valor = card.select_one('.price')
        if not titulo_tag or not valor:
            return None
        titulo = titulo_tag.get_text(" ", strip=True)
        if "para alugar" not in normalizar_filtro(titulo):
            return None
        if re.search(r"\b(alugado|vendido)\b", normalizar_filtro(texto)):
            return None
        preco = _preco_card(valor.get_text(" ", strip=True))
    cidade = _cidade_no_texto(titulo)
    if not cidade or not imovel_atende_filtros(titulo, preco, link, cidade):
        return None
    return titulo, preco, link


def coletar_catalogo_locacao(session, nome, ids, on_records=None):
    novos = []
    urls = urls_portal_local(nome)
    if not urls:
        print(f"{nome}: São José dos Campos não está selecionada nos parâmetros.", flush=True)
        return [], 0
    url = urls[0]
    url_inicial = url
    visitadas, links_vistos = set(), set()
    for pagina in range(1, 31):
        with continue_on_error('Catálogo: página'):
            if not url or url in visitadas:
                break
            visitadas.add(url)
            soup = buscar(session, url)
            cards = soup.select('a.card-with-buttons, a.card_split_vertically')
            if nome == "AZV Imóveis":
                cards = soup.select('a.property-card-link')
            elif nome == "Pinda Prime":
                cards = soup.select('a[href*="/imovel/"]:has(.price)')
            if not cards and not re.search(
                r"nenhum im[oó]vel|n[aã]o encontr|0 im[oó]veis", soup.get_text(" ", strip=True), re.I
            ):
                raise ValueError(f"{nome}: formato da listagem não reconhecido em {url}")
            links_pagina = {urljoin(url, c.get("href", "")) for c in cards}
            if cards and links_pagina.issubset(links_vistos):
                break
            links_vistos.update(links_pagina)
            for card in cards:
                with continue_on_error('Catálogo: anúncio'):
                    campos = extrair_cartao_locacao(card, url)
                    if campos:
                        registro = criar_registro(*campos, pagina, ids)
                        if registro:
                            novos.append(registro)
            if on_records:
                with continue_on_error("Salvar página do catálogo"):
                    on_records(novos)
            proxima = None
            for ancora in soup.select('a[href]'):
                candidata = urljoin(url, ancora["href"])
                partes = urlparse(candidata)
                if (
                    partes.netloc == urlparse(url).netloc
                    and partes.path.rstrip("/") == urlparse(url).path.rstrip("/")
                    and parse_qs(partes.query).get("pagina") == [str(pagina + 1)]
                ):
                    # Mantém os filtros da consulta, mesmo se o link os omitir.
                    parametros = {**parse_qs(urlparse(url_inicial).query), **parse_qs(partes.query)}
                    proxima = urlunparse(partes._replace(query=urlencode(parametros, doseq=True)))
                    break
            url = proxima
    if url and len(visitadas) == 30:
        print(f"[WARN] {nome}: limite de 30 páginas atingido; resultados parciais.", flush=True)
    return novos, len(visitadas)


def _aguardar_consulta(session, url):
    """Leave a small interval between requests to the same site."""
    if not isinstance(session, requests.sessions.Session):
        return
    host = urlparse(url).netloc
    consultas = session.__dict__.setdefault("_findimob_consultas", {})
    anterior = consultas.get(host)
    if anterior is not None:
        restante = .75 - (time.monotonic() - anterior)
        if restante > 0:
            time.sleep(restante)


def _espera_retentativa(response, tentativa):
    espera = min(2 * (2 ** tentativa), 8)
    if response is None:
        return espera
    valor = response.headers.get("Retry-After", "")
    if valor:
        try:
            informado = float(valor)
        except ValueError:
            try:
                momento = parsedate_to_datetime(valor)
                informado = (momento - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                informado = 0
        # Do not retry sooner than requested; long waits are deferred to the
        # next collection instead of exhausting this collector's time budget.
        if informado > 30:
            return None
        espera = max(espera, informado)
    return espera


def buscar(session, url, timeout=(5, 20), retries=2):
    print(f"[HTTP] GET {url}", flush=True)
    for tentativa in range(retries + 1):
        try:
            _aguardar_consulta(session, url)
            try:
                resposta = session.get(url, headers=HEADERS, timeout=timeout)
            finally:
                if isinstance(session, requests.sessions.Session):
                    session.__dict__.setdefault("_findimob_consultas", {})[urlparse(url).netloc] = time.monotonic()
            resposta.raise_for_status()
            print(f"[HTTP] {resposta.status_code} · {len(resposta.content)} bytes recebidos", flush=True)
            return BeautifulSoup(resposta.text, "html.parser")
        except requests.RequestException as erro:
            response = getattr(erro, "response", None)
            transitorio = isinstance(erro, (requests.Timeout, requests.ConnectionError)) or (
                response is not None and response.status_code in {408, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
            )
            if not transitorio or tentativa >= retries:
                raise
            espera = _espera_retentativa(response, tentativa)
            if espera is None:
                print("[HTTP] O site solicitou uma pausa longa. Consulta adiada para a próxima coleta.", flush=True)
                raise
            print(f"[HTTP] Falha temporária; aguardando {espera:g}s antes da tentativa {tentativa + 1}/{retries}.", flush=True)
            time.sleep(espera)


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


def coletar_card_portal(session, config, ids, on_records=None):
    novos = []
    paginas_verificadas = 0
    paginado = config.get("paginado", False)
    for url in config["urls"]:
        with continue_on_error('Catálogo: página'):
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
                with continue_on_error('Catálogo: página'):
                    if pagina > 1:
                        soup = buscar(session, f"{url}&pag={pagina}")
                    paginas_verificadas += 1
                    for card in soup.select(".imovelcard"):
                        with continue_on_error('Catálogo: anúncio'):
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
                    if on_records:
                        with continue_on_error("Salvar página do catálogo"):
                            on_records(novos)
    return novos, paginas_verificadas


def coletar_tailwind(session, config, ids, on_records=None):
    url = re.sub(r"([?&])min=[^&]*", rf"\g<1>min={PRECO_MIN:.2f}", config["url"])
    url = re.sub(r"([?&])max=[^&]*", rf"\g<1>max={PRECO_MAX:.2f}", url)
    soup = buscar(session, url)
    novos = []
    cards = soup.select("a.flex.flex-col.bg-white.rounded-xl.h-full.relative")
    for card in cards:
        with continue_on_error('Catálogo: anúncio'):
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
    if on_records:
        with continue_on_error("Salvar página do catálogo"):
            on_records(novos)
    return novos, 1


def main(portais=None):
    estado = pegar_json(GERAL_JSON)
    ids, dados = estado["ids"], estado["dados"]
    novos_total = []
    falhas = []
    selecionados = set(portais or [*PORTAIS_CARD, *PORTAIS_TAILWIND, *PORTAIS_LOCAIS])
    persistidos = {item["id"] for item in dados}

    def persistir(registros):
        pendentes = [item for item in registros if item["id"] not in persistidos]
        if not pendentes:
            return
        for item in pendentes:
            with continue_on_error('Catálogo: anúncio'):
                dados.append(item)
        if database.is_cloud():
            cloud_store.save_catalogue(pendentes)
        else:
            salvar_json(dados, GERAL_JSON)
        persistidos.update(item["id"] for item in pendentes)
        print(f"[SALVO] {len(pendentes)} anúncio(s) preservado(s).", flush=True)
    with collect_errors(falhas), requests.Session() as session:
        for nome, config in PORTAIS_CARD.items():
            if nome not in selecionados:
                continue
            try:
                novos, paginas = coletar_card_portal(session, config, ids, on_records=persistir)
                persistir(novos)
                novos_total.extend(novos)
                print(f"{nome}: {len(novos)} novo(s), {paginas} página(s).")
            except Exception as erro:
                falhas.append((nome, erro))
                print(f"{nome}: falha na consulta: {erro}")

        for nome, config in PORTAIS_TAILWIND.items():
            if nome not in selecionados:
                continue
            try:
                novos, paginas = coletar_tailwind(session, config, ids, on_records=persistir)
                persistir(novos)
                novos_total.extend(novos)
                print(f"{nome}: {len(novos)} novo(s), {paginas} página(s).")
            except Exception as erro:
                falhas.append((nome, erro))
                print(f"{nome}: falha na consulta: {erro}")

        for nome in PORTAIS_LOCAIS:
            if nome in PORTAIS_INDISPONIVEIS:
                if nome in selecionados:
                    print(f"[INDISPONÍVEL] {nome}: {PORTAIS_INDISPONIVEIS[nome]}", flush=True)
                continue
            if nome not in selecionados:
                continue
            try:
                novos, paginas = coletar_portal_local(session, nome, ids, on_records=persistir)
                persistir(novos)
                novos_total.extend(novos)
                print(f"{nome}: {len(novos)} novo(s), {paginas} página(s).")
            except Exception as erro:
                falhas.append((nome, erro))
                print(f"{nome}: falha na consulta: {erro}")

    if falhas:
        detalhe = f"{len(falhas)} de {len(selecionados)} portal(is) falharam; os demais foram coletados."
        print(f"Aviso: coleta parcial. {detalhe}")
        try:
            registrar_erro_coleta("Coleta parcial", "\n".join([detalhe, *(f"- {nome}: {erro}" for nome, erro in falhas)]))
        except Exception as erro_log:
            print(f"Nao foi possivel registrar as falhas parciais: {erro_log}")
    return 1 if falhas else 0


if __name__ == "__main__":
    import argparse

    portais_disponiveis = [*PORTAIS_CARD, *PORTAIS_TAILWIND, *PORTAIS_LOCAIS]
    parser = argparse.ArgumentParser(description="Coleta anúncios de portais configurados.")
    parser.add_argument(
        "--portal", action="append", choices=portais_disponiveis,
        help="Executa somente o portal informado; pode ser repetido.",
    )
    raise SystemExit(main(parser.parse_args().portal))
