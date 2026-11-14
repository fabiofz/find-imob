"""Rota amigável para o histórico mensal."""

from dashboard_runtime import run_dashboard
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(
    page_title="Find Imob | Histórico mensal",
    page_icon=ROOT / "assets" / "findimob.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.session_state._friendly_route = "historico"
st.session_state.pagina = "Histórico mensal"

run_dashboard()
