import ast
from pathlib import Path
import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
from scripts import catalog_collectors as collectors
from utils.variables import cidade_selecionada


class SaoJoseCollectorsTests(unittest.TestCase):
    def test_city_is_recognized_with_accents_and_in_urls(self):
        for value in ('São José dos Campos', 'sao-jose-dos-campos', 'Sao Jose dos Campos'):
            with self.subTest(value=value):
                self.assertTrue(cidade_selecionada(value))
                self.assertEqual(collectors._cidade_no_texto(value), 'sao-jose-dos-campos')

    def test_sources_are_skipped_if_city_not_selected(self):
        with patch('utils.variables.CIDADES_BUSCA', ['taubate']), patch.object(collectors,'buscar') as fetch:
            for name in collectors.PORTAIS_SJC:
                self.assertEqual(collectors.coletar_portal_local(None,name,set()), ([],0))
            fetch.assert_not_called()

    def test_praedium_reads_split_card_without_condominium_fee(self):
        html = '''<div class="thumbnail_one">
            <a class="property-card-link" href="/imovel/apartamento-para-alugar/1">
                <div class="property_pricing">R$ 2.500/mês</div><span>Condomínio R$ 600</span></a>
            <a class="property-card-link" href="/imovel/apartamento-para-alugar/1">
                <h2 class="property_card_heading">Apartamento para Alugar - São José dos Campos</h2></a></div>'''
        soup = BeautifulSoup(html,'html.parser')
        records=[collectors.extrair_cartao_locacao(a,'https://azvimoveis.com.br/imoveis/para-alugar') for a in soup.select('a')]
        self.assertEqual(records[0],records[1])
        self.assertEqual(records[0][1],'R$ 2.500')
        sale = BeautifulSoup(html.replace('para Alugar','à Venda'),'html.parser')
        self.assertIsNone(collectors.extrair_cartao_locacao(sale.a,'https://azvimoveis.com.br/imoveis/para-alugar'))
        with patch('utils.variables.CIDADES_BUSCA',['taubate']):
            self.assertIsNone(collectors.extrair_cartao_locacao(soup.a,'https://azvimoveis.com.br/imoveis/para-alugar'))

    def test_new_agencies_have_city_and_domain_in_dashboard(self):
        module=ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text())
        values={node.targets[0].id:ast.literal_eval(node.value) for node in module.body
                if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)
                and node.targets[0].id in {'AGENCIES','AGENCY_CITY_GROUPS','AGENCY_DOMAINS'}}
        for name in collectors.PORTAIS_SJC:
            self.assertIn((name,'catalog',name),values['AGENCIES'])
            self.assertIn(name,values['AGENCY_CITY_GROUPS']['São José dos Campos'])
            self.assertIn(name,values['AGENCY_DOMAINS'])
