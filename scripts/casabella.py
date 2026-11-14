"""Casa Bella: bounded requests, rental price and per-page persistence."""
from utils.collection_errors import continue_on_error
import re
from urllib.parse import urlencode, urljoin

import requests

from scripts.catalog_collectors import buscar, criar_registro
from utils.funcs import pegar_json, salvar_json
from utils.variables import GERAL_JSON, TIPOS_BUSCA, cidade_selecionada, imovel_atende_filtros

BASE = 'https://www.casabellaimoveispinda.com.br/'


def extrair_card(card, pagina_url):
    anchor = card.select_one('h3 a[href]')
    price = card.select_one('.price')
    if not anchor or not price:
        return None
    # The following amounts are IPTU, waste fees and condominium, not rent.
    match = re.search(r'R\$\s*(\d[\d.,]*)', price.get_text(' ', strip=True))
    if not match:
        return None
    title = anchor.get_text(' ', strip=True)
    rent = 'R$ ' + match.group(1)
    link = urljoin(pagina_url, anchor['href'])
    if not imovel_atende_filtros(title, rent, link, 'pindamonhangaba'):
        return None
    return title, rent, link


def executar():
    if not cidade_selecionada('pindamonhangaba'):
        print('Casa Bella: Pindamonhangaba não está selecionada.')
        return 0
    state = pegar_json(GERAL_JSON)
    ids, records = state['ids'], state['dados']
    count = 0
    with requests.Session() as session:
        for property_type in TIPOS_BUSCA:
            with continue_on_error('casabella: página ou categoria'):
                query = urlencode({'location': 'pindamonhangaba', 'type': property_type, 'status': 'aluguel'})
                initial_url = BASE + 'busca-de-imoveis/?' + query
                soup = buscar(session, initial_url)
                labels = [int(a.get_text(strip=True)) for a in soup.select('.rh_pagination a.rh_pagination__btn')
                          if a.get_text(strip=True).isdigit()]
                pages = min(max(labels, default=1), 30)
                for page in range(1, pages + 1):
                    with continue_on_error('casabella: página ou categoria'):
                        url = initial_url if page == 1 else BASE + f'busca-de-imoveis/page/{page}/?' + query
                        if page > 1:
                            soup = buscar(session, url)
                        added = 0
                        for card in soup.select('article.rh_list_card'):
                            with continue_on_error('casabella: anúncio'):
                                fields = extrair_card(card, url)
                                if not fields:
                                    continue
                                record = criar_registro(*fields, page, ids)
                                if record:
                                    records.append(record)
                                    added += 1
                        if added:
                            salvar_json(records, GERAL_JSON)
                            count += added
                            print(f'[SALVO] Casa Bella: {added} anúncio(s) na página {page}.', flush=True)
    print(f'Casa Bella: {count} anúncio(s) novo(s).', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(executar())
