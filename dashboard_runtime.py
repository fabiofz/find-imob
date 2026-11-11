"""Run the dashboard for each Streamlit route without reloading shared modules."""
import os
from pathlib import Path
import runpy

import streamlit as st

DASHBOARD_RELEASE = "2026-11-11-collector-recovery"


def home_page():
    return 'cloud_app.py' if os.environ.get('FINDIMOB_CLOUD') == '1' else 'app.py'


@st.cache_resource
def initialize_cloud():
    import cloud_store
    import auth_store
    cloud_store.initialize()
    auth_store.initialize()


def run_dashboard(*, require_cloud=False):
    # Direct links to pages must also initialize the cloud environment, even
    # when that process has not rendered the main entrypoint yet.
    try:
        settings = dict(st.secrets)
    except FileNotFoundError:
        settings = {}
    for name in ('DATABASE_URL', 'DATABASE_DIRECT_URL', 'FINDIMOB_ADMIN_PASSWORD'):
        if not os.environ.get(name) and settings.get(name):
            os.environ[name] = str(settings[name])
    hosted = require_cloud or os.environ.get('FINDIMOB_CLOUD') == '1' or bool(os.environ.get('DATABASE_URL'))
    if hosted:
        os.environ['FINDIMOB_CLOUD'] = '1'
        if not os.environ.get('DATABASE_URL'):
            st.error('A conexão com o banco de dados ainda não foi configurada.')
            st.stop()
        initialize_cloud()
    st.html(f'<span data-findimob-release="{DASHBOARD_RELEASE}" style="display:none"></span>')
    # A fresh script namespace per rerun avoids the shared sys.modules['app']
    # identity and import-spec errors encountered by importlib.reload().
    runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='_findimob_dashboard')
