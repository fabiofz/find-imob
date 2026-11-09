"""Streamlit Community Cloud entrypoint (configure DATABASE_URL in app secrets)."""
import os
from pathlib import Path
import runpy

import streamlit as st

for name in ('DATABASE_URL', 'DATABASE_DIRECT_URL', 'FINDIMOB_ADMIN_PASSWORD'):
    if not os.environ.get(name) and st.secrets.get(name):
        os.environ[name] = str(st.secrets[name])

if not os.environ.get('DATABASE_URL'):
    st.error('A conexão com o banco de dados ainda não foi configurada.')
    st.stop()


@st.cache_resource
def initialize_cloud():
    import cloud_store
    import auth_store
    cloud_store.initialize()
    auth_store.initialize()


initialize_cloud()
runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='__main__')
