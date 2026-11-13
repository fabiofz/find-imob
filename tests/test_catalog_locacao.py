import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
from scripts import catalog_collectors as collectors


def soup(html):
    return BeautifulSoup(html, "html.parser")


def card(city="Taubaté", rental="2.000", sale="450.000", unit="mês"):
    return f'''<a class="card-with-buttons" href="/imovel/casa/CA001">
        <p class="card-with-buttons__title">Casa</p><h2>Centro - {city} - SP</h2>
        <div class="card-with-buttons__value-container">
            <p class="card-with-buttons__value-title">Venda</p>
            <p class="card-with-buttons__value">R$ {sale}</p></div>
        <div class="card-with-buttons__value-container">
            <p class="card-with-buttons__value-title">Aluguel</p>
            <p class="card-with-buttons__value">R$ {rental}/{unit}</p></div></a>'''


class CatalogLocacaoTests(unittest.TestCase):
    url = "https://www.berithimoveis.com.br/imoveis/para-alugar"

    def extract(self, html):
        return collectors.extrair_cartao_locacao(soup(html).a, self.url)

    def test_rental_is_not_sale_or_condominium_price(self):
        record = self.extract(card(sale="1.800"))
        self.assertEqual(record[:2], ("Casa - Centro - Taubaté - SP", "R$ 2.000"))

    def test_daily_rent_and_outside_city_are_excluded(self):
        self.assertIsNone(self.extract(card(unit="dia")))
        self.assertIsNone(self.extract(card(city="Ubatuba")))

    def test_user_filters_are_applied(self):
        self.assertIsNone(self.extract(card(rental="9.000")))
        with patch('utils.variables.CIDADES_BUSCA', ['pindamonhangaba']):
            self.assertIsNone(self.extract(card()))
        with patch('utils.variables.TIPOS_BUSCA', ['apartamento']):
            self.assertIsNone(self.extract(card()))

    def test_sale_only_and_unknown_city_are_excluded(self):
        self.assertIsNone(self.extract(card().replace('>Aluguel<', '>Venda<')))
        self.assertIsNone(self.extract(card(city="")))

    def test_voa_listing_requires_rental_and_available_status(self):
        html = '''<a href="/imovel/casa/1"><h3>Casa para alugar em Pindamonhangaba</h3>
                  <span>Disponível</span><span class="price">R$ 2.500,00</span></a>'''
        self.assertEqual(self.extract(html)[1], 'R$ 2.500,00')
        self.assertIsNone(self.extract(html.replace('Disponível', 'Alugado')))
        self.assertIsNone(self.extract(html.replace('para alugar', 'à venda')))

    def test_pagination_continues_after_no_matches_and_deduplicates(self):
        pages = [soup(card(rental="9.000").replace("CA001", "CA002") + '<a href="?pagina=2">Ver mais</a>'),
                 soup(card() + card())]
        with patch.object(collectors, 'buscar', side_effect=pages) as fetch:
            records, total = collectors.coletar_catalogo_locacao(None, 'Berith Imóveis', set())
        self.assertEqual(total, 2)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['pagina'], 2)
        self.assertIn('preco-de-locacao=', fetch.call_args.args[1])

    def test_unrecognized_layout_is_reported_as_failure(self):
        failures = []
        with collectors.collect_errors(failures), patch.object(collectors, 'buscar', return_value=soup('<h1>Falha</h1>')):
            collectors.coletar_catalogo_locacao(None, 'Berith Imóveis', set())
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0][1], ValueError)


if __name__ == '__main__':
    unittest.main()
