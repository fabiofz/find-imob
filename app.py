"""Painel local para acompanhar e executar os coletores de imóveis."""

import base64
import hashlib
import json
from html import escape
import os
import re
import subprocess
import sys
import time
import shlex
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from bs4 import BeautifulSoup
from utils.funcs import preco_para_float


ROOT = Path(__file__).resolve().parent
LOGO_FILE = ROOT / "assets" / "findimob.svg"
HISTORY_FILE = ROOT / ".execucoes.json"
ERROR_LOG_FILE = ROOT / "logs_erros.txt"
PREVIEW_CACHE_FILE = ROOT / ".link_previews.json"
RESULTS_NOTIFICATION_FILE = ROOT / ".resultados_notificacao.json"
ADVERTISEMENT_STATE_FILE = ROOT / ".anuncios_estado.json"
BUSCA_CONFIG_FILE = ROOT / ".parametros_busca.json"
THEME_FILE = ROOT / ".tema.json"
LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
TAIL_LINES = 24
COLETORES_PINDAMONHANGABA = {
    "casabella", "castor", "confianca", "delta_imoveis", "derrico", "domus",
    "hamilton", "moraes_pereira", "palacete", "pindense", "rodrigoderrico",
    "spaco", "visao", "wilson",
}
TIPOS_IMOVEL = {
    "apartamento": "Apartamento",
    "casa": "Casa",
    "casa-em-condominio": "Casa em condomínio",
    "casa-terrea": "Casa térrea",
    "sobrado": "Sobrado",
    "duplex": "Duplex",
    "kitnet": "Kitnet / studio / loft",
    "comercial": "Comercial",
    "terreno": "Terreno",
    "chacara": "Chácara / sítio",
    "galpao": "Galpão",
}
CIDADES_BUSCA = {
    "pindamonhangaba": "Pindamonhangaba",
    "tremembe": "Tremembé",
    "taubate": "Taubaté",
}

# Coletores que têm HTML próprio. Os nomes das chaves genéricas vêm do catálogo.
AGENCIES = [
    ("012 Imóveis", "catalog", "012 Imóveis"),
    ("Casa Bella", "module", "casabella"),
    ("Castor Imóveis", "module", "castor"),
    ("Imobiliária Confiança", "module", "confianca"),
    ("Delta Imóveis", "module", "delta_imoveis"),
    ("D'Errico Imóveis", "module", "derrico"),
    ("Domus Imóveis", "module", "domus"),
    ("Edifficatho", "catalog", "Edifficatho"),
    ("Erida Vieira", "catalog", "Erida Vieira"),
    ("Hamilton Imóveis", "module", "hamilton"),
    ("Júlio Estefano", "catalog", "Júlio Estefano"),
    ("Moraes & Pereira", "module", "moraes_pereira"),
    ("Nova Cabana", "catalog", "Nova Cabana"),
    ("Palacete Imobiliária", "module", "palacete"),
    ("Palazzo Reale", "catalog", "Palazzo Reale"),
    ("Imobiliária Pindense", "module", "pindense"),
    ("Rodrigo D'Errico", "module", "rodrigoderrico"),
    ("Simob", "catalog", "Simob"),
    ("Spaco Imóveis", "module", "spaco"),
    ("Visão Consultoria", "module", "visao"),
    ("Wilson Imóveis", "module", "wilson"),
    ("Imóveis DNA", "catalog", "DNA"),
    ("Taubaté Imóveis", "catalog", "Taubaté Imóveis"),
    ("Jeremias Rodrigues", "catalog", "Jeremias Rodrigues"),
    ("Única Imóveis", "catalog", "Única Imóveis"),
    ("Márcio Santos", "catalog", "Márcio Santos"),
    ("Imobiliária São Paulo", "catalog", "Imobiliária São Paulo"),
    ("Unidas Imóveis", "catalog", "Unidas Imóveis"),
    ("Personal Consultoria", "catalog", "Personal Consultoria"),
    ("Rio Center Imóveis", "catalog", "Rio Center Imóveis"),
    ("Imobiliária Inovare", "catalog", "Imobiliária Inovare"),
    ("Gomes Nova Opção", "catalog", "Gomes Nova Opção"),
    ("D'Casa Imóveis", "catalog", "D'Casa Imóveis"),
    ("Vista Bela Imóveis", "catalog", "Vista Bela Imóveis"),
    ("Aloisio Imóveis", "catalog", "Aloisio Imóveis"),
    ("Félix Imóveis Especiais", "catalog", "Félix Imóveis Especiais"),
    ("Impera Imóveis", "catalog", "Impera Imóveis"),
]
AGENCY_DOMAINS = {
    "012 Imóveis": ("012imoveis.com.br",),
    "Casa Bella": ("casabellaimoveispinda.com.br",),
    "Castor Imóveis": ("castorimoveis.com.br",),
    "Imobiliária Confiança": ("imobiliariaconfianca.com.br",),
    "Delta Imóveis": ("deltaimoveis.com.br",),
    "D'Errico Imóveis": ("derricoimoveis.com.br",),
    "Domus Imóveis": ("domusimoveis.com",),
    "Edifficatho": ("edifficatho.com.br",),
    "Erida Vieira": ("eridavieira.com.br",),
    "Hamilton Imóveis": ("hnegocios.com",),
    "Júlio Estefano": ("estefanoconsultoria.com.br",),
    "Moraes & Pereira": ("moraesepereiraimoveis.com.br",),
    "Nova Cabana": ("novacabana.com.br",),
    "Palacete Imobiliária": ("palaceteimobiliaria.com.br",),
    "Palazzo Reale": ("palazzorealeimoveis.com.br",),
    "Imobiliária Pindense": ("imobiliariapindense.com.br",),
    "Rodrigo D'Errico": ("rodrigoderrico.com.br",),
    "Simob": ("simobsolucoesimobiliarias.com.br",),
    "Spaco Imóveis": ("spacoimoveis.com",),
    "Visão Consultoria": ("visaoconsultoriadeimoveis.com.br",),
    "Wilson Imóveis": ("wilsonimoveisvale.com.br",),
    "Imóveis DNA": ("imoveisdna.com.br",),
    "Taubaté Imóveis": ("taubateimoveis.com.br",),
    "Jeremias Rodrigues": ("jeremiasrodrigues.com.br",),
    "Única Imóveis": ("unicaimoveistaubate.com.br",),
    "Márcio Santos": ("marciosantosimoveis.com.br",),
    "Imobiliária São Paulo": ("imobiliariasp.com.br",),
    "Unidas Imóveis": ("unidasimoveistaubate.com.br",),
    "Personal Consultoria": ("personalimob.com.br",),
    "Rio Center Imóveis": ("imobiliariariocenter.com.br",),
    "Imobiliária Inovare": ("imobiliariainovare.com.br",),
    "Gomes Nova Opção": ("gomesnovaopcaoimoveis.com.br",),
    "D'Casa Imóveis": ("dcasaimoveis.com.br",),
    "Vista Bela Imóveis": ("vistabelaimoveis.com.br",),
    "Aloisio Imóveis": ("aloisioimoveis.com.br",),
    "Félix Imóveis Especiais": ("feliximoveisespeciais.com",),
    "Impera Imóveis": ("imperaimoveis.com.br",),
}
AGENCY_BY_DOMAIN = {
    dominio: nome
    for nome, dominios in AGENCY_DOMAINS.items()
    for dominio in dominios
}
MESES_PT = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)
DIAS_SEMANA_PT = (
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
)
TEMAS = {
    "Escuro": {"bg": "#121212", "panel": "#181818", "line": "#282828", "muted": "#b3b3b3", "text": "#f5f5f5", "sidebar": "#000000", "hover": "#242424", "band": "#121a24", "field": "#111720"},
    "Branco e verde": {"bg": "#f4f8f5", "panel": "#ffffff", "line": "#d2e2d7", "muted": "#52645a", "text": "#17241b", "sidebar": "#eaf3ed", "hover": "#edf5ef", "band": "#e9f2ec", "field": "#ffffff"},
    "Azul escuro e verde": {"bg": "#0c1727", "panel": "#12233a", "line": "#29415d", "muted": "#b2c3d7", "text": "#f1f6fc", "sidebar": "#091321", "hover": "#1a304b", "band": "#122239", "field": "#14263d"},
}


def carregar_tema():
    try:
        dados = json.loads(THEME_FILE.read_text(encoding="utf-8"))
        tema = dados.get("tema") if isinstance(dados, dict) else None
    except (OSError, json.JSONDecodeError):
        tema = None
    return tema if tema in TEMAS else "Escuro"


def salvar_tema():
    tema = st.session_state.get("tema_app", "Escuro")
    if tema in TEMAS:
        THEME_FILE.write_text(json.dumps({"tema": tema}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    st.set_page_config(
        page_title="Find Imob | Central de coleta",
        page_icon=LOGO_FILE,
        layout="wide",
        initial_sidebar_state="expanded",
    )

if "tema_app" not in st.session_state:
    st.session_state.tema_app = carregar_tema()

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
      :root { --bg:#121212; --panel:#181818; --line:#282828; --muted:#b3b3b3; --text:#f5f5f5; --orange:#32cb79; --green:#32cb79; --green-hover:#51d891; --green-dark:#207b4c; --green-soft:#e7f8ef; --green-card:#d5f1e0; --green-photo:#c5e9d3; --green-text:#1d7045; }
      html, body, [data-testid="stAppViewContainer"] { background:var(--bg); color:var(--text); font-family:'DM Sans',sans-serif; }
      [data-testid="stHeader"] { background:transparent; }
      [data-testid="stSidebar"] { background:#000; border-right:1px solid #282828; }
      [data-testid="stSidebar"] [data-testid="stSidebarHeader"] { position:relative; height:0 !important; min-height:0 !important; padding:0 !important; overflow:visible !important; }
      [data-testid="stSidebar"] [data-testid="stSidebarHeader"] button { position:absolute !important; top:8px; right:12px; z-index:5; }
      [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding-top:0 !important; margin-top:0 !important; }
      [data-testid="stSidebar"] .block-container { padding-top:0 !important; }
      .sidebar-brand { display:flex; align-items:center; gap:12px; width:100%; min-height:58px; margin:0 0 8px; padding:0 28px 0 0; box-sizing:border-box; }
      .sidebar-brand img { display:block; width:48px; height:48px; flex:0 0 48px; object-fit:contain; }
      .sidebar-brand span { color:var(--green); font-weight:700; letter-spacing:.1em; font-size:1rem; line-height:1.25; white-space:nowrap; }
      [data-testid="stSidebarNav"] { display:none; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color:#eaf2fb; }
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color:#b5c5d8; }
      [data-baseweb="tag"] { background:#bd5c17 !important; color:#fff !important; border-color:#f08b3e !important; }
      [data-baseweb="tag"] button { background:transparent !important; color:#fff !important; }
      [data-testid="stSidebar"] [role="radiogroup"] label { background:transparent; border:1px solid transparent; border-radius:8px; padding:10px 12px; margin:4px 0; color:#b3b3b3; transition:background .16s ease,color .16s ease; }
      [data-testid="stSidebar"] [role="radiogroup"] label:hover { background:#181818; color:#fff; }
      [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background:#181818; border-color:#282828; color:#fff; box-shadow:inset 3px 0 var(--green); }
      .block-container { padding-top:1.5rem; padding-bottom:3rem; max-width:1500px; }
      h1,h2,h3,p,span,label { font-family:'DM Sans',sans-serif; }
      h1 { letter-spacing:-.04em; }
      .eyebrow { text-transform:uppercase; letter-spacing:.16em; color:var(--orange); font-size:.72rem; font-weight:700; }
      .subtle { color:var(--muted); }
      .metric-card { background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:18px 20px; min-height:100px; }
      .metric-label { color:var(--muted); font-size:.82rem; }
      .metric-value { color:var(--text); font-size:1.7rem; font-weight:700; margin-top:5px; }
      .agency-card { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:12px 12px 8px; min-height:88px; margin-bottom:5px; transition:background .16s ease,transform .16s ease; }
      .agency-card:hover { background:var(--panel-hover); transform:translateY(-2px); }
      .agency-name { font-weight:700; font-size:.9rem; min-height:22px; }
      .agency-type { color:#a9b6c6; font-size:.7rem; margin-top:1px; }
      .selected-agency-header { background:var(--panel-hover); color:var(--text); border:1px solid var(--line); border-radius:12px; padding:14px 18px; font-weight:700; font-size:1.05rem; margin:10px 0 16px; }
      .selected-agency-header > span:not(.agency-new-dot) { color:#b5c5d8; font-weight:500; font-size:.86rem; margin-left:10px; }
      [data-testid="stExpander"] details summary { background:#181818; border:1px solid #282828; border-radius:10px; color:#fff; }
      [data-testid="stExpander"] details summary p { color:#fff !important; font-weight:700; }
      [data-testid="stExpander"] details summary:hover { background:#242424; border-color:#444; }
      .wa-preview { position:relative; box-sizing:border-box; height:144px; display:flex; flex-direction:column; overflow:hidden; border:1px solid #c4cad2; border-radius:11px; background:#e5e7eb; color:#1f2937; margin-bottom:12px; }
      .wa-preview-main { display:grid; grid-template-columns:minmax(90px, 42%) minmax(0, 1fr); flex:1; min-height:0; height:112px; background:#d1d5db; }
      .wa-preview-photo { width:100%; height:100%; background-color:#c4cad2; background-position:center; background-size:cover; background-repeat:no-repeat; }
      .wa-preview-fallback { width:100%; height:100%; display:flex; align-items:center; justify-content:center; color:#6b7280; font-size:2.3rem; background:#c4cad2; }
      .wa-preview-info { padding:9px 10px; min-width:0; overflow:hidden; }
      .wa-preview-title { color:#1f2937; font-size:.82rem; font-weight:700; line-height:1.25; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
      .wa-preview-description { color:#525b66; font-size:.72rem; line-height:1.25; margin-top:4px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
      .wa-preview-price { color:#374151; font-size:.7rem; font-weight:700; margin-top:4px; }
      .wa-preview a.wa-preview-url { box-sizing:border-box; width:100%; max-width:100%; height:32px; min-height:32px; display:block !important; padding:8px 10px; color:#4b5563 !important; font-size:.68rem !important; line-height:1.1; text-decoration:underline !important; overflow:hidden !important; text-overflow:ellipsis !important; white-space:nowrap !important; overflow-wrap:normal !important; }
      .wa-preview-url-placeholder { box-sizing:border-box; height:32px; min-height:32px; padding:8px 10px; }
      .wa-preview--orange { background:var(--green-soft); border-color:var(--green); }
      .wa-preview--orange .wa-preview-main { background:var(--green-card); }
      .wa-preview--orange .wa-preview-photo, .wa-preview--orange .wa-preview-fallback { background-color:var(--green-photo); }
      .wa-preview--orange .wa-preview-description { color:var(--green-text); }
      .wa-preview--orange .wa-preview-price { color:var(--green-dark); }
      .wa-preview--orange a.wa-preview-url { color:var(--green-dark) !important; }
      .wa-preview-new-dot { position:absolute; z-index:2; top:7px; right:7px; width:10px; height:10px; border:2px solid #fff; border-radius:50%; background:#ef4444; box-shadow:0 1px 5px #0005; }
      .agency-new-dot { display:inline-block; width:9px; height:9px; margin:0 8px 1px 0; border-radius:50%; background:#ef4444; box-shadow:0 0 0 3px #ef444433; vertical-align:middle; }
      .date-time-label { color:var(--text); font-weight:700; letter-spacing:.02em; border-left:3px solid #ef4444; padding:7px 10px; margin:12px 0 10px; background:var(--band); border-radius:0 8px 8px 0; }
      .wa-preview--yellow { background:#fff8d8; border-color:#e2c653; }
      .wa-preview--yellow .wa-preview-main { background:#fff0a8; }
      .wa-preview--yellow .wa-preview-photo, .wa-preview--yellow .wa-preview-fallback { background-color:#f3e6a5; }
      .wa-preview--yellow .wa-preview-description { color:#6d5e27; }
      .wa-preview--yellow .wa-preview-price { color:#765600; }
      .wa-preview--yellow a.wa-preview-url { color:#8a6500 !important; }
      @media (max-width: 900px) { .wa-preview-main { grid-template-columns:minmax(72px, 38%) minmax(0, 1fr); } .wa-preview-title { font-size:.76rem; } .wa-preview-description { font-size:.68rem; } }
      .terminal { background:#080808; border:1px solid #282828; border-radius:14px; padding:14px 16px; }
      .terminal-head { color:#97a7b8; font:700 .75rem 'Space Mono',monospace; border-bottom:1px solid #1a2430; padding-bottom:10px; margin-bottom:10px; }
      .terminal-body { color:#a5e9bf; font: .78rem/1.6 'Space Mono',monospace; white-space:pre-wrap; overflow-wrap:anywhere; max-height:360px; overflow-y:auto; }
      .month-label { color:var(--orange); font-weight:700; letter-spacing:.04em; border-bottom:1px solid var(--line); padding:12px 0 7px; }
      .day-label { color:var(--text); font-weight:700; background:var(--panel); border:1px solid var(--line); border-radius:9px; padding:9px 12px; margin:12px 0 8px; }
      .price-band-label { color:var(--text); font-weight:700; letter-spacing:.02em; border-left:3px solid var(--green); padding:6px 10px; margin:8px 0 10px; background:var(--band); border-radius:0 8px 8px 0; }
      div[data-testid="stButton"] button, div[data-testid="stFormSubmitButton"] button { background:var(--green) !important; color:#fff !important; border:0 !important; border-radius:10px; font-weight:700; transition:all .15s ease; }
      div[data-testid="stButton"] button:hover, div[data-testid="stFormSubmitButton"] button:hover { background:var(--green-hover) !important; color:#fff !important; border:0 !important; transform:translateY(-1px); }
      div[data-testid="stDownloadButton"] button { background:var(--green); color:#fff; border:0; border-radius:10px; font-weight:700; transition:all .15s ease; }
      div[data-testid="stDownloadButton"] button:hover { background:var(--green-hover); color:#fff; border:0; transform:translateY(-1px); }
      div.st-key-run_all button { background:var(--green); color:#101010; min-height:48px; }
      div.st-key-run_all button:hover { background:var(--green-hover); color:#101010; border:0; }
      [data-testid="stDialog"] { align-items:center; padding:16px !important; }
      [data-testid="stDialog"] > div { box-sizing:border-box; width:min(1200px, calc(100vw - 32px)) !important; max-width:calc(100vw - 32px) !important; max-height:calc(100dvh - 32px) !important; overflow-y:auto !important; background:#101720; border:1px solid #33465a; border-radius:18px; }
      [data-testid="stDialog"] .terminal-body { max-height:min(38vh, 320px); }
      @media (max-height: 700px) { [data-testid="stDialog"] .terminal-body { max-height:32vh; } }
      [data-testid="stDialog"] h2 { color:#f0f5fa; }
      div[data-testid="stTextInput"] input { background:#111720; border-color:#273342; }
      div.st-key-busca_imobiliaria input { background:#fff !important; color:#17212b !important; border-color:#cbd5df !important; }
      div.st-key-busca_imobiliaria input::placeholder { color:#657383 !important; opacity:1; }
      div.st-key-busca_anuncio input { background:#fff !important; color:#17212b !important; border-color:#cbd5df !important; }
      div.st-key-busca_anuncio input::placeholder { color:#657383 !important; opacity:1; }
      div.st-key-filtro_imobiliaria label, div.st-key-busca_anuncio label { color:#edf2f7 !important; }
      div.st-key-filtro_imobiliaria [data-baseweb="select"] > div { background:#fff !important; color:#17212b !important; border-color:#cbd5df !important; }
      div.st-key-filtro_imobiliaria [data-baseweb="select"] div { color:#17212b !important; }
      div.st-key-filtro_imobiliaria [data-baseweb="select"] input { color:#17212b !important; }
      div[class*="st-key-favorite"] [data-testid="stButton"] button,
      div[class*="st-key-delete_"] button { min-height:32px; height:32px; padding:0 8px !important; border:1px solid #34475c !important; border-radius:8px !important; background:#121a24 !important; color:#cbd5e1 !important; font-size:.86rem !important; box-shadow:none !important; }
      div[class*="st-key-favorite"] [data-testid="stButton"] button:hover,
      div[class*="st-key-delete_"] button:hover { background:#1b2a39 !important; border-color:#60758c !important; color:#fff !important; transform:none !important; }
      div[class*="st-key-favorite-on_"] [data-testid="stButton"] button { color:#f3c969 !important; border-color:#8a7131 !important; }
      [data-testid="stExpander"] { border:1px solid var(--line); border-radius:12px; }
      .st-key-pagina_mobile { display:none; }
      @media (min-width: 769px) and (max-width: 1100px) {
        [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(4)) { flex-wrap:wrap; }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(4)) > [data-testid="column"] { flex:1 1 calc(50% - .4rem) !important; width:calc(50% - .4rem) !important; min-width:calc(50% - .4rem) !important; }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(5)) { flex-wrap:wrap; }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(5)) > [data-testid="column"] { flex:1 1 calc(33.333% - .5rem) !important; width:calc(33.333% - .5rem) !important; min-width:calc(33.333% - .5rem) !important; }
      }
      @media (max-width: 768px) {
        [data-testid="stSidebar"] { display:none; }
        [data-testid="collapsedControl"] { display:none; }
        [data-testid="stAppViewContainer"] { overflow-x:hidden; }
        .block-container { padding:0.75rem .9rem calc(6.5rem + env(safe-area-inset-bottom)); }
        .st-key-pagina_mobile { display:block; position:fixed !important; left:0 !important; right:0 !important; bottom:0 !important; top:auto !important; z-index:9999; width:100vw !important; box-sizing:border-box; margin:0 !important; padding:8px 8px calc(8px + env(safe-area-inset-bottom)) !important; background:var(--sidebar); border-top:1px solid var(--line); box-shadow:0 -6px 20px #0003; }
        .st-key-pagina_mobile [role="radiogroup"] { display:flex; flex-wrap:nowrap; justify-content:space-around; gap:4px; overflow:visible; padding:2px 0; }
        .st-key-pagina_mobile [role="radiogroup"]::-webkit-scrollbar { display:none; }
        .st-key-pagina_mobile [role="radiogroup"] label { flex:1 1 0; min-width:0; min-height:42px; display:flex; align-items:center; justify-content:center; padding:7px 4px; margin:0; background:transparent; border:1px solid transparent; border-radius:12px; color:var(--muted); white-space:nowrap; font-size:1.35rem; line-height:1; }
        .st-key-pagina_mobile [role="radiogroup"] label > div:first-child { display:none !important; }
        .st-key-pagina_mobile [role="radiogroup"] label:has(input:checked) { background:var(--green); border-color:var(--green); color:#10251a; box-shadow:none; font-weight:700; }
        [data-testid="stHorizontalBlock"] { flex-wrap:wrap; gap:.65rem; }
        [data-testid="stHorizontalBlock"] > [data-testid="column"] { flex:1 1 calc(50% - .4rem) !important; width:calc(50% - .4rem) !important; min-width:calc(50% - .4rem) !important; }
        h1 { font-size:1.8rem !important; line-height:1.1; }
        h2 { font-size:1.35rem !important; }
        .metric-card { padding:14px; min-height:82px; }
        .metric-value { font-size:1.35rem; }
        .terminal { padding:11px; }
        .terminal-body { font-size:.68rem; max-height:45vh; }
        [data-testid="stDialog"] { padding:8px !important; }
        [data-testid="stDialog"] > div { width:calc(100vw - 16px) !important; max-width:calc(100vw - 16px) !important; max-height:calc(100dvh - 16px) !important; padding:1rem !important; }
      }
      @media (max-width: 520px) {
        .block-container { padding-left:.7rem; padding-right:.7rem; }
        [data-testid="stHorizontalBlock"] > [data-testid="column"] { flex:1 1 100% !important; width:100% !important; min-width:100% !important; }
        [data-testid="stHorizontalBlock"]:has(div[class*="st-key-favorite"]) > [data-testid="column"] { flex:1 1 calc(50% - .35rem) !important; width:calc(50% - .35rem) !important; min-width:calc(50% - .35rem) !important; }
        .selected-agency-header { padding:12px; font-size:.95rem; }
        .wa-preview { height:138px; }
        .wa-preview-main { grid-template-columns:minmax(96px, 38%) minmax(0, 1fr); }
        div[data-testid="stButton"] button { min-height:42px; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

cores_tema = TEMAS[st.session_state.tema_app]
st.markdown(
    f"""<style>
      :root {{
        --bg:{cores_tema['bg']}; --panel:{cores_tema['panel']}; --line:{cores_tema['line']};
        --muted:{cores_tema['muted']}; --text:{cores_tema['text']}; --sidebar:{cores_tema['sidebar']};
        --panel-hover:{cores_tema['hover']}; --band:{cores_tema['band']}; --field:{cores_tema['field']};
        --orange:#32cb79; --green:#32cb79; --green-hover:#51d891; --green-dark:#207b4c;
      }}
      [data-testid="stSidebar"] {{ background:var(--sidebar) !important; border-color:var(--line) !important; }}
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{ color:var(--text); }}
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color:var(--muted); }}
      [data-testid="stSidebar"] [role="radiogroup"] label {{ color:var(--muted); }}
      [data-testid="stSidebar"] [role="radiogroup"] label:hover,
      [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{ background:var(--panel); border-color:var(--line); color:var(--text); }}
      .metric-card,.agency-card,[data-testid="stExpander"] details summary {{ background:var(--panel); border-color:var(--line); color:var(--text); }}
      .agency-card:hover,[data-testid="stExpander"] details summary:hover {{ background:var(--panel-hover); }}
      .selected-agency-header,.day-label {{ background:var(--panel-hover); border-color:var(--line); color:var(--text); }}
      .selected-agency-header > span:not(.agency-new-dot) {{ color:var(--muted); }}
      .price-band-label,.date-time-label {{ background:var(--band); color:var(--text); }}
      div[data-testid="stTextInput"] input {{ background:var(--field); color:var(--text); border-color:var(--line); }}
      div[data-testid="stTextInput"] input::placeholder {{ color:var(--muted); opacity:.8; }}
    </style>""",
    unsafe_allow_html=True,
)


def ler_historico():
    try:
        conteudo = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return conteudo if isinstance(conteudo, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def salvar_historico(historico):
    HISTORY_FILE.write_text(
        json.dumps(historico[-300:], ensure_ascii=False, indent=2), encoding="utf-8"
    )


def registrar_log_erro(rotulo, codigo, duracao, linhas):
    instante = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
    bloco = [
        "=" * 78,
        f"[{instante}] ERRO · {rotulo}",
        f"Código de saída: {codigo} · duração: {duracao:.1f}s",
        *linhas[-500:],
        "",
    ]
    with ERROR_LOG_FILE.open("a", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(bloco))


def listar_anuncios():
    caminho = ROOT / "geral.json"
    if not caminho.exists():
        return []
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return dados if isinstance(dados, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def carregar_notificacao_resultados():
    try:
        dados = json.loads(RESULTS_NOTIFICATION_FILE.read_text(encoding="utf-8"))
        return bool(dados.get("pendente")) if isinstance(dados, dict) else False
    except (OSError, json.JSONDecodeError):
        return False


def salvar_notificacao_resultados(pendente):
    try:
        RESULTS_NOTIFICATION_FILE.write_text(
            json.dumps({"pendente": bool(pendente)}, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def chave_anuncio(anuncio):
    link = str(anuncio.get("link") or "").strip()
    if link:
        try:
            parsed = urlparse(link)
            if parsed.hostname:
                return parsed._replace(
                    netloc=parsed.hostname.lower(),
                    path=parsed.path.rstrip("/"),
                    query="",
                    fragment="",
                ).geturl()
        except (TypeError, ValueError):
            pass
        return link.casefold()
    return str(anuncio.get("id") or "")


def carregar_estado_anuncios():
    try:
        estado = json.loads(ADVERTISEMENT_STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(estado, dict):
            return {
                "favoritos": set(), "excluidos": set(),
                "novos": set(), "coletado_em": {},
            }
        return {
            "favoritos": set(estado.get("favoritos", [])),
            "excluidos": set(estado.get("excluidos", [])),
            "novos": set(estado.get("novos", [])),
            "coletado_em": estado.get("coletado_em", {})
            if isinstance(estado.get("coletado_em", {}), dict) else {},
        }
    except (OSError, json.JSONDecodeError, TypeError):
        return {"favoritos": set(), "excluidos": set(), "novos": set(), "coletado_em": {}}


def salvar_estado_anuncios(estado):
    conteudo = {
        "favoritos": sorted(estado.get("favoritos", set())),
        "excluidos": sorted(estado.get("excluidos", set())),
        "novos": sorted(estado.get("novos", set())),
        "coletado_em": estado.get("coletado_em", {}),
    }
    temporario = ADVERTISEMENT_STATE_FILE.with_suffix(".tmp")
    temporario.write_text(
        json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporario.replace(ADVERTISEMENT_STATE_FILE)


def definir_favorito(chave, favorito):
    estado = carregar_estado_anuncios()
    if favorito:
        estado["favoritos"].add(chave)
        estado["excluidos"].discard(chave)
    else:
        estado["favoritos"].discard(chave)
    salvar_estado_anuncios(estado)


def excluir_anuncio(chave):
    estado = carregar_estado_anuncios()
    estado["favoritos"].discard(chave)
    estado["excluidos"].add(chave)
    salvar_estado_anuncios(estado)


def carregar_cache_previews():
    try:
        dados = json.loads(PREVIEW_CACHE_FILE.read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def carregar_parametros_busca():
    padrao = {
        "preco_min": 1500,
        "preco_max": 4500,
        "tipos": ["apartamento", "casa", "casa-em-condominio", "casa-terrea", "sobrado", "duplex"],
        "cidades": list(CIDADES_BUSCA),
    }
    try:
        dados = json.loads(BUSCA_CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(dados, dict):
            return padrao
        minimo = max(0, float(dados.get("preco_min", padrao["preco_min"])))
        maximo = max(0, float(dados.get("preco_max", padrao["preco_max"])))
        if minimo > maximo:
            minimo, maximo = maximo, minimo
        tipos = [tipo for tipo in dados.get("tipos", padrao["tipos"]) if tipo in TIPOS_IMOVEL]
        cidades = [cidade for cidade in dados.get("cidades", padrao["cidades"]) if cidade in CIDADES_BUSCA]
        return {"preco_min": minimo, "preco_max": maximo, "tipos": tipos, "cidades": cidades}
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return padrao


def salvar_parametros_busca(parametros):
    BUSCA_CONFIG_FILE.write_text(
        json.dumps(parametros, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def salvar_cache_previews(cache):
    PREVIEW_CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def validar_imagem_preview(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False
        with requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; FindImobPreview/1.0)"},
            timeout=(2, 3),
            allow_redirects=True,
            stream=True,
        ) as resposta:
            resposta.raise_for_status()
            tipo = resposta.headers.get("Content-Type", "").split(";", 1)[0].lower()
            cabecalho = next(resposta.iter_content(1024), b"")
            assinaturas = (
                cabecalho.startswith(b"\xff\xd8\xff"),
                cabecalho.startswith(b"\x89PNG\r\n\x1a\n"),
                cabecalho.startswith((b"GIF87a", b"GIF89a")),
                cabecalho.startswith(b"BM"),
                cabecalho.startswith((b"II*\x00", b"MM\x00*")),
                cabecalho.startswith(b"RIFF") and cabecalho[8:12] == b"WEBP",
                b"ftypavif" in cabecalho or b"ftypavis" in cabecalho,
            )
            svg_valido = tipo == "image/svg+xml" and b"<svg" in cabecalho.lower()
            return (tipo.startswith("image/") and any(assinaturas)) or svg_valido
    except (requests.RequestException, ValueError, TypeError):
        return False


def buscar_metadados_preview(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return {}
        resposta = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; FindImobPreview/1.0)"},
            timeout=(3, 6),
            allow_redirects=True,
        )
        resposta.raise_for_status()
        soup = BeautifulSoup(resposta.text, "html.parser")

        def meta(*chaves):
            for chave in chaves:
                tag = soup.find("meta", attrs={"property": chave}) or soup.find(
                    "meta", attrs={"name": chave}
                )
                conteudo = tag.get("content", "").strip() if tag else ""
                if conteudo:
                    return conteudo
            return ""

        titulo = meta("og:title", "twitter:title")
        descricao = meta("og:description", "description", "twitter:description")
        imagem = meta("og:image", "twitter:image")
        termos_excluir_imagem = ("logo", "icon", "avatar", "placeholder", "banner")
        if imagem and any(termo in imagem.lower() for termo in termos_excluir_imagem):
            imagem = ""
        candidatas = []
        if imagem:
            candidatas.append((10, imagem))
        for img in soup.find_all("img"):
            src = next((img.get(atributo, "") for atributo in (
                    "src", "data-src", "data-lazy-src", "data-original"
            ) if img.get(atributo)), "")
            srcset = img.get("srcset", "")
            if not src and srcset:
                src = srcset.split(",", 1)[0].strip().split(" ", 1)[0]
            alt = " ".join((img.get("alt", ""), img.get("title", ""))).lower()
            if not src or any(termo in (src + alt).lower() for termo in termos_excluir_imagem):
                continue
            try:
                largura = int(img.get("width", 0))
                altura = int(img.get("height", 0))
            except (TypeError, ValueError):
                largura = altura = 0
            if (largura and largura < 120) or (altura and altura < 90):
                continue
            pontuacao = (2 if largura >= 300 or altura >= 220 else 0) + (
                1 if any(termo in alt for termo in ("imóvel", "imovel", "casa", "fachada", "sala")) else 0
            )
            candidatas.append((pontuacao, src))
        # Muitos portais montam galerias com divs estilizadas em vez de
        # elementos <img>; nesse caso a URL fica no atributo style.
        for elemento in soup.select("[style]"):
            estilo = elemento.get("style", "")
            fundos = re.findall(
                r"background(?:-image)?\s*:\s*url\([\"']?([^\"')]+)",
                estilo,
                flags=re.IGNORECASE,
            )
            for src in fundos:
                if any(termo in src.lower() for termo in termos_excluir_imagem):
                    continue
                pontuacao = 4 if "/imoveis/" in src.lower() else 1
                if "sf-item" in elemento.get("class", []):
                    pontuacao += 2
                candidatas.append((pontuacao, src))
        # Alguns sites guardam as fotos em atributos de dados ou em JSON
        # inline, sem inserir <img> nem style no HTML inicial.
        for elemento in soup.find_all(True):
            for atributo in ("data-bg", "data-background", "data-image", "data-src", "data-original"):
                src = elemento.get(atributo, "")
                if src and re.search(r"\.(?:jpe?g|png|webp|gif|avif)(?:[?#]|$)", src, re.I):
                    if not any(termo in src.lower() for termo in termos_excluir_imagem):
                        candidatas.append((3, src))
        for src in re.findall(
            r"(?:https?:)?//[^\"'\s<>]+?\.(?:jpe?g|png|webp|gif|avif)(?:\?[^\"'\s<>]*)?|/[^\"'\s<>]+?\.(?:jpe?g|png|webp|gif|avif)(?:\?[^\"'\s<>]*)?",
            resposta.text,
            flags=re.IGNORECASE,
        ):
            if not any(termo in src.lower() for termo in termos_excluir_imagem):
                candidatas.append((2 + (3 if "/imoveis/" in src.lower() else 0), src))
        imagem_url = ""
        imagem_validada = False
        vistos = set()
        for tentativa, (_, candidata) in enumerate(
            sorted(candidatas, key=lambda item: item[0], reverse=True)
        ):
            if tentativa >= 4:
                break
            candidata_url = urljoin(resposta.url, candidata)
            if candidata_url in vistos:
                continue
            vistos.add(candidata_url)
            if validar_imagem_preview(candidata_url):
                imagem_url = candidata_url
                imagem_validada = True
                break
        return {
            "titulo": titulo,
            "descricao": descricao,
            "imagem": imagem_url if imagem_validada else "",
            "imagem_validada": imagem_validada,
            "consultado": datetime.now(LOCAL_TZ).isoformat(),
        }
    except (requests.RequestException, ValueError, TypeError):
        return {"consultado": datetime.now(LOCAL_TZ).isoformat()}


def agrupar_por_imobiliaria(anuncios):
    grupos = {nome: [] for nome, _, _ in AGENCIES}
    grupos["Outras imobiliárias"] = []
    for anuncio in anuncios:
        try:
            dominio = (urlparse(anuncio.get("link", "")).hostname or "").lower()
            if dominio.startswith("www."):
                dominio = dominio[4:]
        except (TypeError, ValueError):
            dominio = ""
        imobiliaria = AGENCY_BY_DOMAIN.get(dominio, "Outras imobiliárias")
        grupos.setdefault(imobiliaria, []).append(anuncio)
    return grupos


def html_preview_anuncio(imobiliaria, anuncio, cache, novo=False):
    link = str(anuncio.get("link") or "")
    try:
        parsed_link = urlparse(link)
    except (TypeError, ValueError):
        parsed_link = urlparse("")
    preview = cache.get(link, {})
    titulo = escape(str(preview.get("titulo") or anuncio.get("titulo") or "Imóvel sem título"))
    descricao = escape(
        str(preview.get("descricao") or f"Locação de imóvel · {anuncio.get('preco') or 'consulte o preço'}")
    )
    preco = escape(str(anuncio.get("preco") or "Preço não informado"))
    tipo_destaque = any(
        termo in str(anuncio.get("titulo", "")).casefold()
        for termo in ("sobrado", "duplex")
    )
    preco_num = preco_para_float(str(anuncio.get("preco") or ""))
    if preco_num is not None and preco_num > 4000:
        classe_cartao = "wa-preview wa-preview--yellow"
    elif tipo_destaque:
        classe_cartao = "wa-preview wa-preview--orange"
    else:
        classe_cartao = "wa-preview"
    imagem_url = preview.get("imagem", "")
    try:
        parsed_imagem = urlparse(imagem_url)
    except (TypeError, ValueError):
        parsed_imagem = urlparse("")
    if (
        preview.get("imagem_validada")
        and parsed_imagem.scheme in {"http", "https"}
        and parsed_imagem.netloc
    ):
        imagem_css_url = quote(imagem_url, safe=":/?#[]@!$&*+,;=%-._~")
        imagem = (
            '<div class="wa-preview-photo" style="background-image:url(&quot;'
            + escape(imagem_css_url, quote=True)
            + '&quot;)" role="img" aria-label="Foto do imóvel"></div>'
        )
    else:
        imagem = '<div class="wa-preview-fallback">⌂</div>'
    url_html = '<div class="wa-preview-url-placeholder"></div>'
    try:
        host_link = parsed_link.hostname or ""
        porta_link = parsed_link.port
        link_valido = (
            parsed_link.scheme in {"http", "https"}
            and bool(host_link)
            and not any(caractere.isspace() for caractere in link)
        )
    except ValueError:
        host_link, porta_link, link_valido = "", None, False
    if link_valido:
        if host_link.startswith("www."):
            host_link = host_link[4:]
        rotulo_link = f"{host_link}:{porta_link}" if porta_link else host_link
        url_html = (
            f'<a class="wa-preview-url" href="{escape(link, quote=True)}" '
            f'title="{escape(link, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(rotulo_link)} ↗</a>'
        )
    else:
        url_html = '<div class="wa-preview-url-placeholder">Link indisponível</div>'
    indicador_novo = '<span class="wa-preview-new-dot" title="Anúncio novo"></span>' if novo else ""
    return (
        f'<div class="{classe_cartao}">{indicador_novo}<div class="wa-preview-main">'
        + imagem
        + '<div class="wa-preview-info">'
        + f'<div class="wa-preview-title">{titulo}</div>'
        + f'<div class="wa-preview-description">{descricao}</div>'
        + f'<div class="wa-preview-price">{preco}</div>'
        + '</div></div>' + url_html + '</div>'
    )


def deduplicar_anuncios(anuncios, cache):
    unicos = []
    chaves_vistas = set()
    for anuncio in anuncios:
        link = str(anuncio.get("link") or "")
        try:
            parsed = urlparse(link)
            chave_link = parsed._replace(
                netloc=(parsed.hostname or "").lower(),
                path=parsed.path.rstrip("/"),
                query="",
                fragment="",
            ).geturl()
        except (TypeError, ValueError):
            chave_link = link.strip().casefold()
        chaves_anuncio = [("link", chave_link)] if chave_link else []

        preview = cache.get(link, {})
        imagem = preview.get("imagem") if preview.get("imagem_validada") else ""
        if imagem:
            titulo = unicodedata.normalize(
                "NFKD", str(anuncio.get("titulo") or "")
            ).encode("ascii", "ignore").decode("ascii").casefold()
            titulo = " ".join(re.sub(r"[^a-z0-9]+", " ", titulo).split())
            preco = preco_para_float(str(anuncio.get("preco") or ""))
            chave_visual = ("visual", titulo, preco, imagem.split("#", 1)[0])
            if titulo:
                chaves_anuncio.append(chave_visual)

        if any(chave in chaves_vistas for chave in chaves_anuncio):
            continue
        chaves_vistas.update(chaves_anuncio)
        unicos.append(anuncio)
    return unicos


def renderizar_cartao(imobiliaria, anuncio, cache, pagina_favoritos, novos):
    chave = chave_anuncio(anuncio)
    estado = carregar_estado_anuncios()
    favorito_atual = chave in estado["favoritos"]
    if (
        chave in estado["excluidos"]
        or (pagina_favoritos and not favorito_atual)
        or (not pagina_favoritos and favorito_atual)
    ):
        return

    st.markdown(
        html_preview_anuncio(imobiliaria, anuncio, cache, novo=chave in novos),
        unsafe_allow_html=True,
    )
    acao_coluna, excluir_coluna = st.columns(2, gap="small")
    hash_anuncio = hashlib.sha256(chave.encode()).hexdigest()[:16]
    with acao_coluna:
        if st.button(
            "★" if favorito_atual else "☆",
            help="Remover dos favoritos" if favorito_atual else "Favoritar anúncio",
            key=f"favorite-on_{hash_anuncio}" if favorito_atual else f"favorite_{hash_anuncio}",
            use_container_width=True,
        ):
            definir_favorito(chave, not favorito_atual)
            st.session_state["_expand_agencia_apos_acao"] = imobiliaria
            st.rerun(scope="fragment")
            return
    with excluir_coluna:
        if st.button(
            "🗑",
            help="Excluir anúncio",
            key=f"delete_{hash_anuncio}",
            use_container_width=True,
        ):
            excluir_anuncio(chave)
            st.session_state["_expand_agencia_apos_acao"] = imobiliaria
            st.rerun(scope="fragment")
            return


def renderizar_previews(imobiliaria, resultados, cache, pagina_favoritos, novos):
    for inicio in range(0, len(resultados), 4):
        colunas = st.columns(4, gap="small")
        for coluna, anuncio in zip(colunas, resultados[inicio:inicio + 4]):
            with coluna:
                renderizar_cartao(imobiliaria, anuncio, cache, pagina_favoritos, novos)


def agrupar_por_faixa_preco(resultados):
    faixas = {
        "Acima de R$ 4.000": [],
        "R$ 3.000 a R$ 4.000": [],
        "R$ 2.000 a R$ 3.000": [],
        "Até R$ 2.000": [],
        "Preço não informado": [],
    }
    for anuncio in resultados:
        valor = preco_para_float(str(anuncio.get("preco") or ""))
        if valor is None:
            faixa = "Preço não informado"
        elif valor > 4000:
            faixa = "Acima de R$ 4.000"
        elif valor > 3000:
            faixa = "R$ 3.000 a R$ 4.000"
        elif valor > 2000:
            faixa = "R$ 2.000 a R$ 3.000"
        else:
            faixa = "Até R$ 2.000"
        faixas[faixa].append(anuncio)
    return {faixa: itens for faixa, itens in faixas.items() if itens}


def agrupar_por_data_hora(resultados, datas_coleta):
    grupos = {}
    for anuncio in resultados:
        chave = chave_anuncio(anuncio)
        data_hora = datas_coleta.get(chave) or anuncio.get("coletado_em")
        instante = None
        if data_hora:
            try:
                instante = datetime.fromisoformat(str(data_hora))
                if instante.tzinfo is None:
                    instante = instante.replace(tzinfo=LOCAL_TZ)
                instante = instante.astimezone(LOCAL_TZ).replace(microsecond=0)
            except (TypeError, ValueError):
                instante = None
        grupos.setdefault(instante, []).append(anuncio)

    return sorted(
        grupos.items(),
        key=lambda grupo: grupo[0] or datetime.min.replace(tzinfo=LOCAL_TZ),
        reverse=True,
    )


def renderizar_resultados_por_faixa(
    imobiliaria, resultados, cache, pagina_favoritos, datas_coleta, novos
):
    for instante, anuncios_data in agrupar_por_data_hora(resultados, datas_coleta):
        rotulo_data = (
            instante.strftime("%d/%m/%Y às %H:%M:%S")
            if instante else "Data/hora não registrada"
        )
        st.markdown(
            f'<div class="date-time-label">{rotulo_data} · {len(anuncios_data)} anúncio(s)</div>',
            unsafe_allow_html=True,
        )
        for faixa, itens in agrupar_por_faixa_preco(anuncios_data).items():
            st.markdown(
                f'<div class="price-band-label">{faixa} · {len(itens)} anúncio(s)</div>',
                unsafe_allow_html=True,
            )
            renderizar_previews(
                imobiliaria, itens, cache, pagina_favoritos, novos
            )


def executar(rotulo, tipo, identificador):
    if st.session_state.get("coletando", False):
        st.warning("Já existe uma coleta em andamento nesta sessão.")
        return
    parametros_execucao = carregar_parametros_busca()
    anuncios_antes = {
        chave_anuncio(anuncio)
        for anuncio in listar_anuncios()
        if chave_anuncio(anuncio)
    }
    if (
        tipo == "module"
        and identificador in COLETORES_PINDAMONHANGABA
        and "pindamonhangaba" not in parametros_execucao["cidades"]
    ):
        st.info(f"{rotulo} atende Pindamonhangaba. Inclua essa cidade nos parâmetros para executar este coletor.")
        return

    st.session_state.coletando = True
    comando = [sys.executable]
    if tipo == "all":
        comando.append(str(ROOT / "runner.py"))
    elif tipo == "module":
        comando.extend(["-m", f"scripts.{identificador}"])
    else:
        comando.extend(["-m", "scripts.catalog_collectors", "--portal", identificador])

    instante = datetime.now(LOCAL_TZ)
    inicio = time.monotonic()
    hora_inicio = instante.strftime("%H:%M:%S")
    log = [
        f"[{hora_inicio}] [INFO] Preparando execução para: {rotulo}",
        f"[{hora_inicio}] [CMD] {shlex.join(comando)}",
        f"[{hora_inicio}] [INFO] Diretório: {ROOT}",
        f"[{hora_inicio}] [INFO] Acompanhando saída em modo tail ({TAIL_LINES} linhas)",
    ]
    terminal = st.empty()
    status = st.status(f"Executando: {rotulo}", expanded=True)
    terminal.markdown(
        f'<div class="terminal"><div class="terminal-head">● TAIL · ÚLTIMAS {min(len(log), TAIL_LINES)} / {len(log)} LINHAS &nbsp; · &nbsp; '
        + rotulo
        + '</div><div class="terminal-body">'
        + "\n".join(log).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        + "</div></div>",
        unsafe_allow_html=True,
    )

    ambiente = os.environ.copy()
    ambiente["PYTHONUNBUFFERED"] = "1"
    ambiente["FINDIMOB_PRECO_MIN"] = str(parametros_execucao["preco_min"])
    ambiente["FINDIMOB_PRECO_MAX"] = str(parametros_execucao["preco_max"])
    ambiente["FINDIMOB_TIPOS"] = ",".join(parametros_execucao["tipos"])
    ambiente["FINDIMOB_CIDADES"] = ",".join(parametros_execucao["cidades"])
    processo = None
    codigo = 1
    try:
        processo = subprocess.Popen(
            comando,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=ambiente,
        )
        for linha in processo.stdout:
            hora = datetime.now(LOCAL_TZ).strftime("%H:%M:%S")
            log.append(f"[{hora}] {linha.rstrip()}")
            corpo = "\n".join(log[-TAIL_LINES:]) or "Aguardando saída..."
            terminal.markdown(
                f'<div class="terminal"><div class="terminal-head">● TAIL · ÚLTIMAS {min(len(log), TAIL_LINES)} / {len(log)} LINHAS &nbsp; · &nbsp; '
                + rotulo
                + '</div><div class="terminal-body">'
                + corpo.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                + "</div></div>",
                unsafe_allow_html=True,
            )
        codigo = processo.wait()
    except Exception as erro:  # Mostra erros de inicialização também no terminal.
        log.append(f"Erro ao iniciar o coletor: {erro}")
    finally:
        st.session_state.coletando = False

    duracao = round(time.monotonic() - inicio, 1)
    resultado = "sucesso" if codigo == 0 else "falha"
    hora_fim = datetime.now(LOCAL_TZ).strftime("%H:%M:%S")
    log.append(f"[{hora_fim}] [{'OK' if codigo == 0 else 'ERRO'}] Processo terminou com código {codigo} após {duracao:.1f}s")
    corpo = "\n".join(log[-TAIL_LINES:]) or "Processo finalizado sem mensagens."
    terminal.markdown(
        f'<div class="terminal"><div class="terminal-head">● TAIL · ÚLTIMAS {min(len(log), TAIL_LINES)} / {len(log)} LINHAS &nbsp; · &nbsp; '
        + rotulo
        + '</div><div class="terminal-body">'
        + corpo.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        + "</div></div>",
        unsafe_allow_html=True,
    )
    if codigo != 0:
        try:
            registrar_log_erro(rotulo, codigo, duracao, log)
        except OSError as erro_log:
            log.append(f"[{hora_fim}] [ERRO] Não foi possível gravar logs_erros.txt: {erro_log}")
    status.update(
        label=(f"Concluído em {duracao}s" if codigo == 0 else f"Finalizado com erro ({codigo})"),
        state=("complete" if codigo == 0 else "error"),
        expanded=(codigo != 0),
    )
    st.session_state.ultima_execucao_dialogo = {
        "id": st.session_state.get("execucao_dialogo_id"),
        "rotulo": rotulo,
        "codigo": codigo,
        "duracao": duracao,
        "log": log[-TAIL_LINES:],
    }
    catalogo_depois = listar_anuncios()
    anuncios_depois = {
        chave_anuncio(anuncio)
        for anuncio in catalogo_depois
        if chave_anuncio(anuncio)
    }
    chaves_novas = anuncios_depois - anuncios_antes
    if chaves_novas:
        estado_anuncios = carregar_estado_anuncios()
        chaves_novas_visiveis = chaves_novas - estado_anuncios["excluidos"]
        hora_coleta = instante.isoformat()
        for anuncio in catalogo_depois:
            chave = chave_anuncio(anuncio)
            if chave in chaves_novas_visiveis:
                estado_anuncios["coletado_em"][chave] = hora_coleta
        estado_anuncios["novos"].update(chaves_novas_visiveis)
        salvar_estado_anuncios(estado_anuncios)
    if chaves_novas - carregar_estado_anuncios()["excluidos"]:
        st.session_state.resultados_notificacao = True
        salvar_notificacao_resultados(True)
    historico = ler_historico()
    historico.append(
        {
            "inicio": instante.isoformat(),
            "rotulo": rotulo,
            "resultado": resultado,
            "codigo": codigo,
            "duracao": duracao,
            "log": log[-120:],
        }
    )
    salvar_historico(historico)
    st.session_state.ultimo_resultado = resultado


@st.dialog("Visualizador de execução", width="large")
def visualizar_execucao(rotulo, tipo, identificador, execucao_id):
    st.caption(f"Processo selecionado · {rotulo}")
    if iniciar_execucao_dialogo(st.session_state, execucao_id):
        # Marca antes de iniciar: qualquer rerun do diálogo não pode relançar o coletor.
        executar(rotulo, tipo, identificador)
    else:
        resultado = st.session_state.get("ultima_execucao_dialogo", {})
        if resultado.get("id") == execucao_id:
            codigo = resultado["codigo"]
            log = resultado["log"]
            corpo = "\n".join(log).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            st.markdown(
                f'<div class="terminal"><div class="terminal-head">● TAIL · ÚLTIMAS {len(log)} LINHAS &nbsp; · &nbsp; '
                + escape(resultado["rotulo"])
                + '</div><div class="terminal-body">'
                + corpo
                + "</div></div>",
                unsafe_allow_html=True,
            )
            st.status(
                f"{'Concluído' if codigo == 0 else f'Finalizado com erro ({codigo})'} · {resultado['duracao']}s",
                state="complete" if codigo == 0 else "error",
                expanded=codigo != 0,
            )
        else:
            st.info("Esta execução já foi iniciada.")
    if st.button("Fechar visualizador", key="close_execution_viewer", use_container_width=True):
        st.rerun()


def iniciar_execucao_dialogo(estado, execucao_id):
    """Retorna True somente na primeira renderização de uma execução do diálogo."""
    if estado.get("execucao_dialogo_id") == execucao_id:
        return False
    estado["execucao_dialogo_id"] = execucao_id
    return True


historico = ler_historico()
anuncios = listar_anuncios()
cache_previews = carregar_cache_previews()
parametros_busca = carregar_parametros_busca()
for chave, valor in (
    ("busca_preco_min", parametros_busca["preco_min"]),
    ("busca_preco_max", parametros_busca["preco_max"]),
    ("busca_tipos", parametros_busca["tipos"]),
    ("busca_cidades", parametros_busca["cidades"]),
):
    if chave not in st.session_state:
        st.session_state[chave] = valor
ultima_execucao = historico[-1]["inicio"] if historico else None
execucoes_por_imobiliaria = {}
for registro_execucao in historico:
    nome_executado = registro_execucao.get("rotulo", "")
    if nome_executado and nome_executado != "Todas as imobiliárias":
        execucoes_por_imobiliaria[nome_executado] = (
            execucoes_por_imobiliaria.get(nome_executado, 0) + 1
        )

paginas_disponiveis = [
    "Imobiliárias", "Resultados das buscas", "Favoritos", "Histórico mensal", "Log de erros"
]
ROTAS_AMIGAVEIS = {
    "Imobiliárias": ("imobiliarias", "pages/imobiliarias.py"),
    "Resultados das buscas": ("resultados", "pages/resultados.py"),
    "Favoritos": ("favoritos", "pages/favoritos.py"),
    "Histórico mensal": ("historico", "pages/historico.py"),
    "Log de erros": ("erros", "pages/erros.py"),
}
pagina_salva = st.query_params.get("pagina", "Imobiliárias")
if "pagina" not in st.session_state:
    st.session_state.pagina = pagina_salva if pagina_salva in paginas_disponiveis else "Imobiliárias"
if "resultados_notificacao" not in st.session_state:
    st.session_state.resultados_notificacao = carregar_notificacao_resultados()
if st.session_state.pagina == "Resultados das buscas" and st.session_state.resultados_notificacao:
    st.session_state.resultados_notificacao = False
    salvar_notificacao_resultados(False)
if "_friendly_route" not in st.session_state:
    st.session_state._friendly_route = "home"


def persistir_parametro_url(chave):
    valor = st.session_state.get(chave, "")
    if chave == "pagina" and valor in paginas_disponiveis:
        st.session_state.pagina_mobile = valor
    if chave == "pagina" and valor in ROTAS_AMIGAVEIS:
        rota, arquivo = ROTAS_AMIGAVEIS[valor]
        st.query_params.pop(chave, None)
        if st.session_state.get("_friendly_route") != rota:
            st.session_state._friendly_route = rota
            st.switch_page(arquivo)
        return
    if valor:
        st.query_params[chave] = str(valor)
    else:
        st.query_params.pop(chave, None)


def selecionar_pagina_mobile():
    st.session_state.pagina = st.session_state.pagina_mobile
    persistir_parametro_url("pagina")


@st.fragment
def renderizar_pagina_anuncios(pagina):
    expandir_agencia = st.session_state.pop("_expand_agencia_apos_acao", None)
    anuncios = listar_anuncios()
    cache_previews = carregar_cache_previews()
    estado_anuncios = carregar_estado_anuncios()
    favoritos = estado_anuncios["favoritos"]
    excluidos = estado_anuncios["excluidos"]
    novos = set(estado_anuncios["novos"])
    datas_coleta = estado_anuncios["coletado_em"]
    if pagina == "Favoritos":
        anuncios_da_pagina = [
            anuncio for anuncio in anuncios
            if chave_anuncio(anuncio) in favoritos
            and chave_anuncio(anuncio) not in excluidos
        ]
        texto_vazio = "Você ainda não favoritou nenhum anúncio."
        st.caption("Os anúncios favoritos ficam guardados aqui entre as atualizações.")
    else:
        anuncios_da_pagina = [
            anuncio for anuncio in anuncios
            if chave_anuncio(anuncio) not in favoritos
            and chave_anuncio(anuncio) not in excluidos
        ]
        texto_vazio = "Ainda não há anúncios coletados para exibir."
        st.caption("Anúncios do catálogo agrupados pela imobiliária identificada no link de origem.")

    grupos = agrupar_por_imobiliaria(anuncios_da_pagina)
    grupos = {nome: itens for nome, itens in grupos.items() if itens}
    if not grupos:
        st.info(texto_vazio)
        return

    filtro_coluna, busca_coluna = st.columns([1, 2])
    chave_filtro = "filtro_favoritos_imobiliaria" if pagina == "Favoritos" else "filtro_imobiliaria"
    chave_busca = "busca_favoritos" if pagina == "Favoritos" else "busca_anuncio"
    with filtro_coluna:
        opcoes_imobiliaria = ["Todas", *grupos.keys()]
        imobiliaria_salva = (
            st.query_params.get("imobiliaria", "Todas")
            if pagina == "Resultados das buscas"
            else "Todas"
        )
        if chave_filtro not in st.session_state:
            st.session_state[chave_filtro] = (
                imobiliaria_salva if imobiliaria_salva in opcoes_imobiliaria else "Todas"
            )
        if st.session_state[chave_filtro] not in opcoes_imobiliaria:
            st.session_state[chave_filtro] = "Todas"
        imobiliaria_selecionada = st.selectbox(
            "Imobiliária",
            opcoes_imobiliaria,
            key=chave_filtro,
            on_change=persistir_parametro_url if pagina == "Resultados das buscas" else None,
            args=("imobiliaria",) if pagina == "Resultados das buscas" else None,
        )
    with busca_coluna:
        if chave_busca not in st.session_state:
            st.session_state[chave_busca] = (
                st.query_params.get("busca", "")
                if pagina == "Resultados das buscas"
                else ""
            )
        consulta = st.text_input(
            "Buscar anúncio",
            placeholder="Título, preço ou bairro…",
            label_visibility="visible",
            key=chave_busca,
            on_change=persistir_parametro_url if pagina == "Resultados das buscas" else None,
            args=("busca",) if pagina == "Resultados das buscas" else None,
        ).casefold()

    grupos_filtrados = (
        [(imobiliaria_selecionada, grupos[imobiliaria_selecionada])]
        if imobiliaria_selecionada != "Todas"
        else grupos.items()
    )
    resultados_por_imobiliaria = {}
    for nome, itens in grupos_filtrados:
        resultados = [
            item for item in itens
            if not consulta or consulta in " ".join(
                str(item.get(chave, "")) for chave in ("titulo", "preco", "link")
            ).casefold()
        ]
        if resultados:
            resultados = deduplicar_anuncios(resultados, cache_previews)
            resultados.sort(
                key=lambda item: preco_para_float(str(item.get("preco") or "")) or 0,
                reverse=True,
            )
            resultados_por_imobiliaria[nome] = resultados

    total_visivel = sum(len(resultados) for resultados in resultados_por_imobiliaria.values())
    anuncios_visiveis = [
        item for itens in resultados_por_imobiliaria.values() for item in itens
    ]
    progresso_previews_slot = st.empty()
    status_previews_slot = st.empty()
    if anuncios_visiveis:
        carregar_previews = st.button(
            "Carregar fotos e descrição dos anúncios",
            key=f"fetch_previews_{'favorites' if pagina == 'Favoritos' else 'results'}",
        )
        if carregar_previews:
            urls = list(dict.fromkeys(
                str(item.get("link") or "") for item in anuncios_visiveis
                if str(item.get("link") or "").startswith(("http://", "https://"))
                and not cache_previews.get(str(item.get("link") or ""), {}).get("imagem_validada")
            ))
            if not urls:
                st.info("As fotos dos anúncios visíveis já estão carregadas.")
            else:
                progresso_previews = progresso_previews_slot.progress(
                    0, text=f"Fotos 0 de {len(urls)}"
                )
                status_previews = status_previews_slot.status(
                    f"Consultando {len(urls)} anúncio(s)…", expanded=False
                )
                with ThreadPoolExecutor(max_workers=6) as executor:
                    tarefas = {
                        executor.submit(buscar_metadados_preview, url): url
                        for url in urls
                    }
                    for concluido, tarefa in enumerate(as_completed(tarefas), start=1):
                        url = tarefas[tarefa]
                        try:
                            cache_previews[url] = tarefa.result()
                        except Exception as erro:
                            cache_previews[url] = {
                                "erro": str(erro),
                                "consultado": datetime.now(LOCAL_TZ).isoformat(),
                            }
                        salvar_cache_previews(cache_previews)
                        progresso_previews.progress(
                            concluido / len(tarefas),
                            text=f"Fotos {concluido} de {len(tarefas)}",
                        )
                validas = sum(
                    bool(cache_previews.get(url, {}).get("imagem_validada"))
                    for url in urls
                )
                status_previews.update(
                    label=f"Fotos carregadas: {validas} de {len(urls)} anúncio(s)",
                    state="complete" if validas else "error",
                    expanded=not validas,
                )
                st.rerun()

    if (
        imobiliaria_selecionada != "Todas"
        and imobiliaria_selecionada in resultados_por_imobiliaria
    ):
        nome = imobiliaria_selecionada
        resultados = resultados_por_imobiliaria[nome]
        possui_novidades = pagina == "Resultados das buscas" and any(
            chave_anuncio(anuncio) in novos for anuncio in resultados
        )
        indicador_imobiliaria = (
            '<span class="agency-new-dot" title="Há anúncios novos" '
            'aria-label="Há anúncios novos"></span>'
            if possui_novidades else ""
        )
        st.markdown(
            f'<div class="selected-agency-header">{indicador_imobiliaria}{escape(nome)}'
            f'<span>{len(resultados)} anúncio(s)</span></div>',
            unsafe_allow_html=True,
        )
        renderizar_resultados_por_faixa(
            nome, resultados, cache_previews, pagina == "Favoritos", datas_coleta, novos
        )
    else:
        for nome, resultados in resultados_por_imobiliaria.items():
            possui_novidades = pagina == "Resultados das buscas" and any(
                chave_anuncio(anuncio) in novos for anuncio in resultados
            )
            indicador_imobiliaria = "🔴 " if possui_novidades else ""
            with st.expander(
                f"{indicador_imobiliaria}{nome} · {len(resultados)} anúncio(s)",
                expanded=nome == expandir_agencia,
            ):
                renderizar_resultados_por_faixa(
                    nome, resultados, cache_previews, pagina == "Favoritos", datas_coleta, novos
                )

    if pagina == "Resultados das buscas" and novos:
        estado_anuncios["novos"].difference_update(novos)
        salvar_estado_anuncios(estado_anuncios)

    if total_visivel:
        st.caption(f"{total_visivel} resultado(s) exibido(s)")
    else:
        st.info("Nenhum anúncio corresponde ao filtro.")

with st.sidebar:
    logo_data = base64.b64encode(LOGO_FILE.read_bytes()).decode("ascii")
    st.markdown(
        f'<div class="sidebar-brand"><img src="data:image/svg+xml;base64,{logo_data}" '
        'alt="Find Imob"><span>PAINEL DE<br>OPERAÇÕES</span></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.selectbox(
        "Esquema de cores",
        options=list(TEMAS),
        key="tema_app",
        on_change=salvar_tema,
    )
    st.divider()
    pagina = st.radio(
        "Seção",
        paginas_disponiveis,
        format_func=lambda opcao: (
            f"🔴 {opcao}"
            if opcao == "Resultados das buscas" and st.session_state.resultados_notificacao
            else opcao
        ),
        key="pagina",
        on_change=persistir_parametro_url,
        args=("pagina",),
        label_visibility="collapsed",
    )
    st.divider()
    with st.expander("Parâmetros da busca", expanded=True):
        st.caption("Aplicados nas próximas execuções dos coletores.")
        with st.form("parametros_busca_form"):
            coluna_min, coluna_max = st.columns(2)
            with coluna_min:
                st.number_input(
                    "Valor mínimo (R$)", min_value=0, step=100,
                    key="busca_preco_min",
                )
            with coluna_max:
                st.number_input(
                    "Valor máximo (R$)", min_value=0, step=100,
                    key="busca_preco_max",
                )
            st.multiselect(
                "Tipos de imóvel",
                options=list(TIPOS_IMOVEL),
                format_func=lambda tipo: TIPOS_IMOVEL[tipo],
                key="busca_tipos",
            )
            st.multiselect(
                "Cidades",
                options=list(CIDADES_BUSCA),
                format_func=lambda cidade: CIDADES_BUSCA[cidade],
                key="busca_cidades",
            )
            salvar_filtros = st.form_submit_button("Salvar parâmetros", use_container_width=True)
        if salvar_filtros:
            valor_min = float(st.session_state.busca_preco_min)
            valor_max = float(st.session_state.busca_preco_max)
            if valor_min > valor_max:
                st.error("O valor mínimo não pode ser maior que o máximo.")
            elif not st.session_state.busca_tipos or not st.session_state.busca_cidades:
                st.error("Selecione ao menos um tipo de imóvel e uma cidade.")
            else:
                parametros_busca = {
                    "preco_min": valor_min,
                    "preco_max": valor_max,
                    "tipos": st.session_state.busca_tipos,
                    "cidades": st.session_state.busca_cidades,
                }
                salvar_parametros_busca(parametros_busca)
                st.success("Parâmetros salvos.")
    st.divider()
    st.markdown("**Resumo**")
    st.caption(f"{len(AGENCIES)} imobiliárias conectadas")
    st.caption(f"{len(historico)} execuções registradas")
    st.caption(f"{'Erros registrados' if ERROR_LOG_FILE.exists() else 'Sem erros registrados'}")
    st.divider()
    st.markdown("**Arquivos**")
    st.caption("Catálogo · geral.json")
    st.caption("Exportação · Excel")

if st.session_state.get("pagina_mobile") != pagina:
    st.session_state.pagina_mobile = pagina
st.radio(
    "Navegação",
    paginas_disponiveis,
    key="pagina_mobile",
    horizontal=True,
    help="Navegação: início, resultados, favoritos, histórico mensal e log de erros.",
    label_visibility="collapsed",
    format_func=lambda opcao: {
        "Imobiliárias": "⌂",
        "Resultados das buscas": (
            "🔴⌕"
            if st.session_state.resultados_notificacao else "⌕"
        ),
        "Favoritos": "★",
        "Histórico mensal": "◷",
        "Log de erros": "⚠",
    }[opcao],
    on_change=selecionar_pagina_mobile,
)

st.markdown('<div class="eyebrow">Find Imob &nbsp; / &nbsp; Operações</div>', unsafe_allow_html=True)
st.title(
    pagina if pagina in {"Resultados das buscas", "Favoritos"} else "Central de coleta"
)
st.markdown(
    '<p class="subtle">Anúncios coletados, organizados por imobiliária.</p>'
    if pagina == "Resultados das buscas"
    else (
        '<p class="subtle">Anúncios salvos como favoritos.</p>'
        if pagina == "Favoritos"
        else '<p class="subtle">Acompanhe os portais, execute coletas e consulte o histórico mensal.</p>'
    ),
    unsafe_allow_html=True,
)

if pagina == "Imobiliárias":
    col_a, col_b, col_c = st.columns([1, 1, 2])
    with col_a:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Imobiliárias</div><div class="metric-value">{len(AGENCIES)}</div></div>', unsafe_allow_html=True)
    with col_b:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Anúncios no catálogo</div><div class="metric-value">{len(anuncios):,}</div></div>', unsafe_allow_html=True)
    with col_c:
        ultima = datetime.fromisoformat(ultima_execucao).astimezone(LOCAL_TZ).strftime("%d/%m/%Y às %H:%M") if ultima_execucao else "Ainda não há execuções registradas"
        st.markdown(f'<div class="metric-card"><div class="metric-label">Última atividade</div><div class="metric-value" style="font-size:1.25rem">{ultima}</div></div>', unsafe_allow_html=True)

    st.write("")
    if st.button("▶  EXECUTAR TODAS AS IMOBILIÁRIAS", key="run_all", use_container_width=True):
        execucao_id = str(time.time_ns())
        visualizar_execucao("Todas as imobiliárias", "all", None, execucao_id)

    st.write("")
    busca = st.text_input(
        "Buscar imobiliária",
        placeholder="Digite o nome do portal…",
        label_visibility="collapsed",
        key="busca_imobiliaria",
    )
    agencias_visiveis = [item for item in AGENCIES if busca.casefold() in item[0].casefold()]
    st.markdown(f'<p class="subtle">{len(agencias_visiveis)} portal(is) disponíveis</p>', unsafe_allow_html=True)
    for inicio_grade in range(0, len(agencias_visiveis), 5):
        grade = st.columns(5, gap="small")
        for coluna, agencia in zip(grade, agencias_visiveis[inicio_grade:inicio_grade + 5]):
            nome, tipo, identificador = agencia
            with coluna:
                quantidade_execucoes = execucoes_por_imobiliaria.get(nome, 0)
                rotulo_execucoes = (
                    f"{quantidade_execucoes} execução individual"
                    if quantidade_execucoes == 1
                    else f"{quantidade_execucoes} execuções individuais"
                )
                st.markdown(
                    f'<div class="agency-card"><div class="agency-name">{nome}</div>'
                    f'<div class="agency-type">{rotulo_execucoes}</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    "▶  Executar imobiliária",
                    key=f"run_agency_{identificador}",
                    use_container_width=True,
                ):
                    execucao_id = str(time.time_ns())
                    visualizar_execucao(nome, tipo, identificador, execucao_id)

elif pagina in {"Resultados das buscas", "Favoritos"}:
    renderizar_pagina_anuncios(pagina)

elif pagina == "Histórico mensal":
    st.subheader("Histórico de execuções")
    if not historico:
        st.info("As execuções aparecerão aqui, separadas por dia e horário.")
    else:
        agrupado_por_dia = {}
        for item in historico:
            momento = datetime.fromisoformat(item["inicio"]).astimezone(LOCAL_TZ)
            agrupado_por_dia.setdefault(momento.date(), []).append((momento, item))
        for dia, itens in sorted(agrupado_por_dia.items(), reverse=True):
            rotulo_dia = (
                f"{DIAS_SEMANA_PT[dia.weekday()].capitalize()}, "
                f"{dia.day} de {MESES_PT[dia.month - 1]} de {dia.year}"
            )
            st.markdown(f'<div class="day-label">{rotulo_dia}</div>', unsafe_allow_html=True)
            for momento, item in sorted(itens, key=lambda registro: registro[0], reverse=True):
                icone = "✅" if item["resultado"] == "sucesso" else "⚠️"
                with st.expander(f"{icone}  {momento.strftime('%H:%M:%S')}  —  {item['rotulo']}  ·  {item['duracao']}s"):
                    st.code("\n".join(item.get("log", [])) or "Sem saída registrada.", language="text")
elif pagina == "Log de erros":
    st.subheader("Log de erros")
    st.markdown("As falhas de coleta são registradas em `logs_erros.txt` e permanecem disponíveis entre execuções.")
    if ERROR_LOG_FILE.exists():
        texto_erros = ERROR_LOG_FILE.read_text(encoding="utf-8", errors="replace")
        st.download_button(
            "Baixar logs_erros.txt",
            texto_erros,
            file_name="logs_erros.txt",
            mime="text/plain",
        )
        st.code("\n".join(texto_erros.splitlines()[-1000:]), language="text")
    else:
        st.success("Nenhum erro foi registrado até agora.")
