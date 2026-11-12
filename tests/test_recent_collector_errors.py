import unittest
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
import requests

from scripts import catalog_collectors as collectors
from scripts import rodrigoderrico


class RecentCollectorErrorsTests(unittest.TestCase):
    def test_cloudflare_520_is_retried(self):
        bad, good = requests.Response(), requests.Response()
        bad.status_code = 520
        good.status_code = 200
        good._content = b'<h1>Recovered</h1>'
        session = Mock()
        session.get.side_effect = [bad, good]
        with patch.object(collectors.time, 'sleep'):
            self.assertEqual(collectors.buscar(session, 'https://example.com').h1.text, 'Recovered')
        self.assertEqual(session.get.call_count, 2)

    def test_inovare_does_not_invent_a_second_page(self):
        with patch.object(collectors, 'buscar', return_value=BeautifulSoup('<p>Sem anúncios</p>', 'html.parser')) as fetch:
            records, pages = collectors.coletar_portal_local(None, 'Imobiliária Inovare', set())
        self.assertEqual(pages, 1)
        fetch.assert_called_once()

    def test_inovare_follows_same_site_pagination_only(self):
        first = BeautifulSoup('<a href="/imovel/locacao/?pag=2">2</a><a href="https://other.com/?pag=3">3</a>', 'html.parser')
        with patch.object(collectors, 'buscar', side_effect=[first, BeautifulSoup('', 'html.parser')]) as fetch:
            records, pages = collectors.coletar_portal_local(None, 'Imobiliária Inovare', set())
        self.assertEqual(pages, 2)
        self.assertEqual(fetch.call_args.args[1], 'https://www.imobiliariainovare.com.br/imovel/locacao/?pag=2')

    def test_rodrigo_continues_after_failure_and_checkpoints_each_success(self):
        html = '''<ul class="properties_list"><li><h3>Sem preço</h3></li>
        <li><h3>Valor: R$3.000,00</h3><h3>Bairro: CENTRO</h3>
        <a href="/locacao_casas/one/index.htm">Casa</a></li></ul>'''
        soup = BeautifulSoup(html, 'html.parser')
        saved = []
        with patch.object(rodrigoderrico, 'buscar', side_effect=[soup, requests.Timeout('timeout'), soup]):
            records, failures = rodrigoderrico.coletar(None, set(), on_records=lambda records: saved.append(list(records)))
        self.assertEqual(len(failures), 1)
        self.assertEqual(len(saved), 2)
        self.assertEqual(len(saved[0]), 1)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]['link'], 'https://www.rodrigoderrico.com.br/locacao_casas/one/index.htm')
        self.assertEqual(records[1]['titulo'], 'Apartamento - CENTRO')
