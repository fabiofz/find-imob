"""Rota amigável para abrir diretamente os anúncios favoritos."""

from dashboard_runtime import run_dashboard
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(
    page_title="Find Imob | Favoritos",
    page_icon=ROOT / "assets" / "findimob.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.session_state._friendly_route = "favoritos"
st.session_state.pagina = "Favoritos"

run_dashboard()
