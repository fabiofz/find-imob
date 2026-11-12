"""Collect Rodrigo D'Errico with retries and a checkpoint after each page."""
from urllib.parse import urljoin

import requests

from scripts.catalog_collectors import buscar, criar_registro
from utils.funcs import pegar_json, salvar_json, registrar_erro_coleta
from utils.variables import GERAL_JSON, imovel_atende_filtros

URLS = [
    'https://www.rodrigoderrico.com.br/locacao-casas-opc1-padrao.html',
    'https://www.rodrigoderrico.com.br/locacao-casas-opc1-condominio.html',
    'https://www.rodrigoderrico.com.br/locacao-apartamentos.html',
]


def coletar(session, ids, on_records=None):
    records, failures = [], []
    for page, url in enumerate(URLS, 1):
        try:
            soup = buscar(session, url, timeout=(8, 15), retries=1)
        except requests.RequestException as error:
            failures.append((url, error))
            print(f"Rodrigo D'Errico: falha na página {url}: {error}", flush=True)
            continue
        for card in soup.select('ul.properties_list li'):
            fields = {}
            for heading in card.select('h3'):
                label, separator, value = heading.get_text(' ', strip=True).partition(':')
                if separator:
                    fields[label.strip().casefold()] = value.strip()
            price = fields.get('valor')
            neighborhood = fields.get('bairro')
            anchor = card.select_one('a[href]')
            if not price or not neighborhood or not anchor:
                continue
            kind = 'Apartamento' if 'apartamentos' in url else 'Casa'
            title = f'{kind} - {neighborhood}'
            link = urljoin(url, anchor['href'])
            if not imovel_atende_filtros(title, price, link, 'pindamonhangaba'):
                continue
            record = criar_registro(title, price, link, page, ids)
            if record:
                records.append(record)
        if on_records:
            on_records(records)
    return records, failures


def main():
    state = pegar_json(GERAL_JSON)
    persisted = {item['id'] for item in state['dados']}

    def checkpoint(records):
        pending = [item for item in records if item['id'] not in persisted]
        if pending:
            for item in pending:
                state['dados'].append(item)
            salvar_json(state['dados'], GERAL_JSON)
            persisted.update(item['id'] for item in pending)

    with requests.Session() as session:
        records, failures = coletar(session, state['ids'], on_records=checkpoint)
    print(f"Rodrigo D'Errico: {len(records)} novo(s); {len(failures)} página(s) com falha.", flush=True)
    if failures:
        registrar_erro_coleta("Coleta parcial · Rodrigo D'Errico", '\n'.join(
            f'{url}: {error}' for url, error in failures))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
