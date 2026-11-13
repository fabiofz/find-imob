import io
import unittest
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
import requests

import runner
from scripts import catalog_collectors as collectors
from utils.collection_errors import collect_errors, continue_on_error


class ContinueOnErrorsTests(unittest.TestCase):
    def test_bad_card_does_not_prevent_next_card_or_checkpoint(self):
        page = BeautifulSoup('<a class="card-with-buttons" href="/imovel/1"></a><a class="card-with-buttons" href="/imovel/2"></a>', 'html.parser')
        saved, failures = [], []
        with collect_errors(failures), patch.object(collectors, 'buscar', return_value=page), \
             patch.object(collectors, 'extrair_cartao_locacao', side_effect=[ValueError('cartão inválido'), ('Casa', 'R$ 2.100', 'https://example.com/2')]):
            records, pages = collectors.coletar_catalogo_locacao(None, 'Berith Imóveis', set(), on_records=lambda items: saved.extend(items))
        self.assertEqual(len(records), 1)
        self.assertEqual(saved, records)
        self.assertEqual(len(failures), 1)

    def test_card_pagination_continues_after_middle_page_timeout(self):
        first = BeautifulSoup('<a class="lipagina-btn-paginacao-atual">3</a>', 'html.parser')
        third = BeautifulSoup('<article class="imovelcard"><a class="imovelcard__img" title="Casa Centro" href="/imovel/3"></a><div class="imovelcard__valor__valor">R$ 2.100</div></article>', 'html.parser')
        failures, saved = [], []
        with collect_errors(failures), patch.object(collectors, 'buscar', side_effect=[first, requests.Timeout('página 2'), third]) as fetch:
            records, pages = collectors.coletar_card_portal(None, {'paginado': True, 'urls': ['https://example.com/imovel/locacao/casa/pindamonhangaba/?vmi=1500&vma=4500']}, set(), on_records=lambda items: saved.extend(items))
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(len(failures), 1)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['pagina'], 3)
        self.assertEqual(saved, records)

    def test_checkpoint_failure_does_not_stop_next_linked_page(self):
        first = BeautifulSoup('<a class="card-with-buttons" href="/imovel/1"></a><a href="?pagina=2">2</a>', 'html.parser')
        second = BeautifulSoup('<a class="card-with-buttons" href="/imovel/2"></a>', 'html.parser')
        failures = []
        checkpoint = Mock(side_effect=[OSError('disco temporariamente indisponível'), None])
        with collect_errors(failures), patch.object(collectors, 'buscar', side_effect=[first, second]), \
             patch.object(collectors, 'extrair_cartao_locacao', side_effect=[('Casa 1', 'R$ 2.100', 'https://example.com/1'), ('Casa 2', 'R$ 2.100', 'https://example.com/2')]):
            records, pages = collectors.coletar_catalogo_locacao(None, 'Berith Imóveis', set(), on_records=checkpoint)
        self.assertEqual(checkpoint.call_count, 2)
        self.assertEqual(len(records), 2)
        self.assertEqual(len(failures), 1)
        self.assertEqual(len(checkpoint.call_args.args[0]), 2)

    def test_logging_failure_does_not_stop_later_steps(self):
        completed = []
        with patch('utils.collection_errors.registrar_erro_coleta', side_effect=OSError('log indisponível')):
            for item in range(3):
                with continue_on_error('etapa'):
                    if item == 1:
                        raise ValueError('item inválido')
                    completed.append(item)
        self.assertEqual(completed, [0, 2])

    def test_manual_interrupt_is_not_swallowed(self):
        with self.assertRaises(KeyboardInterrupt):
            with continue_on_error('interromper'):
                raise KeyboardInterrupt()

    def test_runner_records_partial_even_when_subprocess_exits_zero(self):
        process = Mock(stdout=io.StringIO('[COLETA_PARCIAL] erro isolado\ncontinua\n'))
        process.poll.return_value = 0
        process.wait.return_value = 0
        failures = []
        with patch.object(runner.subprocess, 'Popen', return_value=process), patch.object(runner, 'registrar_erro_coleta'):
            runner._run_collector('exemplo', {}, failures)
        self.assertEqual(failures, [('scripts.exemplo', 1)])
