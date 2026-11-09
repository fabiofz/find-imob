"""Streamlit Community Cloud entrypoint."""
from pathlib import Path

import streamlit as st
from dashboard_runtime import run_dashboard
import ui_feedback  # Keep the navigation component in the entrypoint dependency graph.

st.set_page_config(
    page_title='Find Imob | Central de coleta',
    page_icon=Path(__file__).with_name('assets') / 'findimob.svg',
    layout='wide',
    initial_sidebar_state='expanded',
)
run_dashboard(require_cloud=True)
