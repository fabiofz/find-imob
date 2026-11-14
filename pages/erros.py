"""Rota amigável para o log de erros."""

from dashboard_runtime import run_dashboard
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(
    page_title="Find Imob | Log de erros",
    page_icon=ROOT / "assets" / "findimob.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.session_state._friendly_route = "erros"
st.session_state.pagina = "Log de erros"

run_dashboard()
