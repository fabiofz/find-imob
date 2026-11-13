from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import cloud_store
import collection_jobs as jobs
import collection_worker as worker

PARAMETERS = {'preco_min': 1500, 'preco_max': 4500, 'tipos': ['casa'], 'cidades': ['pindamonhangaba']}


class BackgroundCollectionTests(unittest.TestCase):
    def test_launcher_can_exit_while_collection_completes_and_saves_history(self):
        # Real detached process. No network, real catalogue or browser session.
        with tempfile.TemporaryDirectory() as folder:
            child = '''
import sys, time
from pathlib import Path
import cloud_store
from collection_worker import run_job
path = Path(sys.argv[1])
def collect(state):
    print('Primeira etapa', flush=True)
    time.sleep(1.5)
    cloud_store.write_json(path.parent.parent/'geral.json', [{'id':'test','titulo':'Casa de teste','link':'https://example.com/1'}])
    print('Última etapa', flush=True)
    return 0
run_job(path, collector=collect, enricher=lambda *args:None)
'''
            launcher = '''
import json, subprocess, sys
from pathlib import Path
from unittest.mock import patch
import collection_jobs
real_spawn = subprocess.Popen
child = sys.argv[2]
def spawn(command, **kwargs):
    return real_spawn([sys.executable, '-c', child, command[-1]], **kwargs)
with patch.object(collection_jobs.subprocess, 'Popen', side_effect=spawn):
    job, created = collection_jobs.start_collection('Teste', 'all', None, json.loads(sys.argv[3]), root=Path(sys.argv[1]))
    duplicate, created_twice = collection_jobs.start_collection('Teste', 'all', None, json.loads(sys.argv[3]), root=Path(sys.argv[1]))
    assert not created_twice and duplicate['id'] == job['id']
print(job['id'])
'''
            environment = {**os.environ, 'DATABASE_URL': '', 'FINDIMOB_CLOUD': '',
                           'PYTHONPATH': str(Path(__file__).resolve().parents[1])}
            result = subprocess.run([sys.executable, '-c', launcher, folder, child, json.dumps(PARAMETERS)],
                                    capture_output=True, text=True, timeout=10, env=environment, check=True)
            job_id = result.stdout.strip()
            state = jobs.read_job(job_id, folder)
            self.assertIn(state['status'], jobs.RUNNING)
            deadline = time.monotonic() + 10
            while state.get('status') in jobs.RUNNING and time.monotonic() < deadline:
                time.sleep(.1)
                state = jobs.read_job(job_id, folder)
            self.assertEqual(state['status'], 'completed', (state, (Path(folder)/'.collection_jobs'/f'{job_id}.worker.log').read_text()))
            self.assertEqual(state['novos'], 1)
            self.assertTrue(any('Última etapa' in line for line in state['log']))
            self.assertEqual(jobs.read_active(folder)['id'], job_id)
            history = jobs.read_json(Path(folder)/'.execucoes.json')
            self.assertEqual(history[0]['resultado'], 'sucesso')
            property_state = jobs.read_json(Path(folder)/'.anuncios_estado.json')
            self.assertEqual(property_state['novos'], ['https://example.com/1'])
            self.assertTrue(jobs.read_json(Path(folder)/'.resultados_notificacao.json')['pendente'])

    def test_dead_process_is_marked_interrupted_and_can_be_restarted(self):
        with tempfile.TemporaryDirectory() as folder:
            job_id = 'a'*32
            path = Path(folder)/'.collection_jobs'/f'{job_id}.json'
            jobs.write_json(path, {'id':job_id,'status':'running','pid':0,'parametros':PARAMETERS,'rotulo':'Teste'})
            jobs.write_json(Path(folder)/'.execucao_ativa.json', {'job_id':job_id})
            self.assertEqual(jobs.read_active(folder)['status'], 'interrupted')
            with patch.object(jobs.subprocess, 'Popen') as spawn:
                spawn.return_value.pid = 1234
                new, created = jobs.start_collection('Teste', 'all', None, PARAMETERS, folder)
            self.assertTrue(created)
            self.assertNotEqual(new['id'], job_id)
            self.assertIs(spawn.call_args.kwargs['stdin'], subprocess.DEVNULL)
            self.assertTrue(spawn.call_args.kwargs['start_new_session'])
            self.assertNotEqual(spawn.call_args.kwargs['stdout'], subprocess.PIPE)

    def test_collector_failure_still_finalizes_existing_results(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'DATABASE_URL':''}):
            path = Path(folder)/'.collection_jobs'/('b'*32+'.json')
            jobs.write_json(path, {'id':'b'*32,'rotulo':'Teste','tipo':'all','identificador':None,'parametros':PARAMETERS})
            def failure(state):
                raise RuntimeError('falha simulada')
            with patch('utils.funcs.registrar_erro_coleta') as error_log:
                worker.run_job(path, collector=failure, enricher=lambda *args:None)
            state = jobs.read_json(path)
            self.assertEqual(state['status'], 'completed')
            self.assertEqual(state['resultado'], 'parcial')
            error_log.assert_called_once()
            self.assertEqual(jobs.read_json(Path(folder)/'.execucoes.json')[0]['resultado'], 'parcial')

    def test_failed_collector_allows_retry_instead_of_reporting_success(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'DATABASE_URL':''}):
            path = Path(folder)/'.collection_jobs'/('c'*32+'.json')
            jobs.write_json(path, {'id':'c'*32,'rotulo':'Teste','tipo':'all','identificador':None,'parametros':PARAMETERS})
            with patch('utils.funcs.registrar_erro_coleta'):
                worker.run_job(path, collector=lambda state:1, enricher=lambda *args:None)
            state = jobs.read_json(path)
            self.assertEqual(state['status'], 'failed')
            self.assertEqual(state['resultado'], 'falha')
            self.assertEqual(jobs.read_json(Path(folder)/'.execucoes.json')[0]['resultado'], 'falha')

    def test_legacy_zombie_does_not_block_a_new_collection(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs.write_json(Path(folder)/'.execucao_ativa.json', {'id':'old','pid':0,'rotulo':'Todas as imobiliárias','log':['old']})
            state = jobs.read_active(folder)
            self.assertTrue(state['legacy'])
            self.assertEqual(state['status'], 'interrupted')
