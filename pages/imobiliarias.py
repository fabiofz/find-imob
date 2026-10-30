"""Rota amigável para o painel das imobiliárias."""

import importlib
import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(
    page_title="Find Imob | Imobiliárias",
    page_icon=ROOT / "assets" / "findimob.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.session_state._friendly_route = "imobiliarias"
st.session_state.pagina = "Imobiliárias"

if "app" in sys.modules:
    importlib.reload(sys.modules["app"])
else:
    import app  # noqa: F401
