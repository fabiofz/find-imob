"""Rota direta para entrar no Find Imob."""

from dashboard_runtime import run_dashboard
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(
    page_title="Find Imob | Entrar",
    page_icon=ROOT / "assets" / "findimob.svg",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.session_state._auth_route_mode = "login"
run_dashboard()
