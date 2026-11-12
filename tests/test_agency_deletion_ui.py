import ast
import hashlib
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


class AgencyDeletionUITests(unittest.TestCase):
    def test_confirmation_cancel_and_bulk_delete_ignore_text_filter(self):
        source = Path('app.py').read_text()
        tree = ast.parse(source)
        functions = '\n\n'.join(ast.get_source_segment(source, node) for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in {
                'excluir_resultados_imobiliaria', 'renderizar_exclusao_imobiliaria',
                'solicitar_exclusao_imobiliaria', 'cancelar_exclusao_imobiliaria'})
        script = '''
import hashlib
import streamlit as st
if 'excluded' not in st.session_state:
    st.session_state.excluded = []
def listar_anuncios():
    return [{'key': 'a-one'}, {'key': 'a-two'}, {'key': 'favorite'}, {'key': 'b-one'}]
def agrupar_por_imobiliaria(items):
    return {'Agência A': items[:3], 'Agência B': items[3:]}
def chave_anuncio(item):
    return item['key']
ADVERTISEMENT_STATE_FILE = 'unused'
def exclude_advertisements(path, keys, preserve_favorites=False):
    assert preserve_favorites
    selected = set(keys) - {'favorite'} - set(st.session_state.excluded)
    st.session_state.excluded += sorted(selected)
    return len(selected)
''' + functions + '''
feedback = st.session_state.pop('_delete_agency_feedback', None)
if feedback:
    st.success(feedback)
st.text_input('Buscar anúncio', key='busca_anuncio')
expanded = st.session_state.pop('_expand_agencia_apos_acao', None)
with st.expander('Agência A', expanded=expanded == 'Agência A' or st.session_state.get('_delete_agency_pending') == 'Agência A'):
    renderizar_exclusao_imobiliaria('Agência A', 2)
'''
        app = AppTest.from_string(script).run()
        key = hashlib.sha256('Agência A'.encode()).hexdigest()[:16]
        app.text_input(key='busca_anuncio').input('a-one').run()
        app.button(key=f'delete_agency_{key}').click().run()
        self.assertIn('2 resultados', app.warning[0].value)
        self.assertEqual(app.session_state.excluded, [])
        app.button(key=f'cancel_delete_agency_{key}').click().run()
        self.assertEqual(app.session_state.excluded, [])
        self.assertEqual(len(app.warning), 0)
        self.assertTrue(app.expander[0].proto.expanded)
        app.button(key=f'delete_agency_{key}').click().run()
        app.button(key=f'confirm_delete_agency_{key}').click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state.excluded, ['a-one', 'a-two'])
        self.assertIn('2 anúncio(s)', app.success[0].value)
