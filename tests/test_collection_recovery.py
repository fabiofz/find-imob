import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests
from bs4 import BeautifulSoup
import runner
from scripts import catalog_collectors as collectors
from scripts import casabella
from utils.funcs import RegistrosUnicos

HTML = '''<a class="card-with-buttons" href="/imovel/casa/1">
<p class="card-with-buttons__title">Casa</p><h2>Centro - Pindamonhangaba - SP</h2>
<div class="card-with-buttons__value-container"><p class="card-with-buttons__value-title">Aluguel</p>
<p class="card-with-buttons__value">R$ 2.100/mês</p></div></a>'''


class CollectionRecoveryTests(unittest.TestCase):
    def test_timeout_budget_is_per_agency_and_later_agency_still_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'catalog_collectors.py').touch()
            calls=[]
            def run(module, environment, failures, portal=None):
                calls.append(portal)
                if portal=='First':failures.append((portal,124))
            with patch.object(runner,'SCRIPTS_DIR',Path(folder)), \
                 patch.object(runner,'_run_collector',side_effect=run), \
                 patch.object(collectors,'PORTAIS_CARD',{}),patch.object(collectors,'PORTAIS_TAILWIND',{}), \
                 patch.object(collectors,'PORTAIS_LOCAIS',{'First':'first','Second':'second'}), \
                 patch.object(collectors,'PORTAIS_INDISPONIVEIS',{}):
                self.assertEqual(runner.main(),1)
            self.assertEqual(calls,['First','Second'])

    def test_subprocess_command_includes_agency_selection(self):
        process=Mock(stdout=io.StringIO(''))
        process.poll.return_value=0
        process.wait.return_value=0
        with patch.object(runner.subprocess,'Popen',return_value=process) as spawn:
            runner._run_collector('catalog_collectors',{},[],portal='Berith Imóveis')
        self.assertEqual(spawn.call_args.args[0][-2:],['--portal','Berith Imóveis'])

    def test_page_is_checkpointed_before_next_request_fails(self):
        first=BeautifulSoup(HTML+'<a href="?pagina=2">Ver mais</a>','html.parser')
        saved=[]
        failures = []
        with collectors.collect_errors(failures), patch.object(collectors,'buscar',side_effect=[first,requests.Timeout('página 2')]):
            collectors.coletar_catalogo_locacao(None,'Berith Imóveis',set(),
                on_records=lambda records:saved.extend(dict(item) for item in records))
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0][1], requests.Timeout)
        self.assertEqual(len(saved),1)
        self.assertEqual(saved[0]['preco'],'R$ 2.100')

    def test_main_saves_partial_records_and_reports_failure(self):
        records=RegistrosUnicos()
        saved=[]
        def collect(session,name,ids,on_records=None):
            on_records([{'id':'one','titulo':'Casa','preco':'R$ 2.100','link':'https://example.com/1'}])
            raise requests.Timeout('página seguinte')
        with patch.object(collectors,'pegar_json',return_value={'ids':set(),'dados':records}), \
             patch.object(collectors.database,'is_cloud',return_value=False), \
             patch.object(collectors,'salvar_json',side_effect=lambda data,path:saved.append(list(data))), \
             patch.object(collectors,'coletar_portal_local',side_effect=collect), \
             patch.object(collectors,'registrar_erro_coleta') as log:
            result=collectors.main(['Berith Imóveis'])
        self.assertEqual(result,1)
        self.assertEqual(saved[-1][0]['id'],'one')
        log.assert_called_once()

    def test_transient_connection_failure_is_retried(self):
        response=requests.Response()
        response.status_code=200
        response._content=b'<h1>OK</h1>'
        session=Mock()
        session.get.side_effect=[requests.ConnectionError('reset'),response]
        with patch.object(collectors.time,'sleep'):
            self.assertEqual(collectors.buscar(session,'https://example.com').h1.text,'OK')
        self.assertEqual(session.get.call_count,2)

    def test_404_is_not_retried(self):
        response=requests.Response()
        response.status_code=404
        session=Mock()
        session.get.return_value=response
        with self.assertRaises(requests.HTTPError):collectors.buscar(session,'https://example.com')
        session.get.assert_called_once()

    def test_batista_does_not_send_unsupported_price_filter(self):
        self.assertNotIn('preco-de-locacao',collectors.urls_portal_local('Batista Imóveis')[0])

    def test_guerrero_is_not_queried_for_pinda(self):
        with patch.object(collectors,'buscar') as fetch:
            with self.assertRaisesRegex(ValueError,'Vitória'):
                collectors.coletar_portal_local(None,'Imobiliária Guerrero',set())
            fetch.assert_not_called()

    def test_casabella_uses_rent_without_adding_taxes(self):
        card=BeautifulSoup('''<article><h3><a href="/imovel/1">Apartamento Centro</a></h3>
        <p class="price">R$2.100,00 IPTU + TX: R$113,92 + COND: R$646,10</p></article>''','html.parser').article
        self.assertEqual(casabella.extrair_card(card,'https://example.com')[1],'R$ 2.100,00')
        self.assertIsNone(casabella.extrair_card(BeautifulSoup('<article/>','html.parser').article,'https://example.com'))

    def test_danelli_uses_brazilian_price_format_and_excludes_sales(self):
        response=Mock()
        response.json.return_value={'quantidade':2,'lista':[
            {'codigo':1,'tipo':'Casa','cidade':'Taubaté','codigofinalidade':1,'valor':'R$ 2.100,00','titulo':'Casa Centro','url_amigavel':'casa-centro'},
            {'codigo':2,'tipo':'Casa','cidade':'Taubaté','codigofinalidade':2,'valor':'R$ 2.100,00','titulo':'Casa venda','url_amigavel':'casa-venda'}]}
        session=Mock()
        session.post.return_value=response
        with patch.object(collectors,'buscar'):
            records,pages=collectors.coletar_danelli(session,set())
        self.assertEqual(len(records),1)
        self.assertEqual(pages,1)
        self.assertIn(',',session.post.call_args.kwargs['data']['valorde'])
