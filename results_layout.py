"""Shared presentation for the results and favourites lists."""
import streamlit as st


RESULTS_CSS = '''
<style>
.results-summary { display:flex; flex-wrap:wrap; gap:8px; margin:6px 0 20px; }
.results-summary span { padding:6px 12px; border:1px solid var(--line); border-radius:999px; background:var(--panel); color:var(--muted); font-size:.82rem; }
.results-summary strong { color:var(--text); }
[class*="st-key-property_card_"] { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:12px; margin-bottom:12px; transition:border-color .15s ease; }
[class*="st-key-property_card_"]:hover { border-color:var(--green); }
[class*="st-key-property_card_"] [data-testid="stVerticalBlock"] { gap:.55rem; }
[class*="st-key-property_card_"] .wa-preview { height:174px; margin:0; border:0; border-radius:10px; }
[class*="st-key-property_card_"] .wa-preview-main { height:138px; grid-template-columns:38% minmax(0,1fr); }
[class*="st-key-property_card_"] .wa-preview-info { padding:12px; }
[class*="st-key-property_card_"] .wa-preview-title { font-size:.9rem; line-height:1.35; }
[class*="st-key-property_card_"] .wa-preview-description { margin-top:7px; }
[class*="st-key-property_card_"] .wa-preview-price { font-size:1rem; margin-top:9px; }
[class*="st-key-property_card_"] button { min-height:38px !important; height:auto !important; font-size:.8rem !important; }
[class*="st-key-property_card_"] [class*="st-key-reviews_"] button { background:transparent !important; color:var(--muted) !important; border:1px solid var(--line) !important; }
[class*="st-key-property_card_"] [class*="st-key-favorite"] button { background:var(--panel-hover) !important; color:var(--text) !important; border-color:var(--line) !important; }
[class*="st-key-property_card_"] [class*="st-key-favorite-on_"] button { color:var(--green) !important; }
[class*="st-key-property_card_"] [class*="st-key-delete_"] button,
[class*="st-key-agency_tools_"] button,
[class*="st-key-cancel_delete_agency_"] button { background:transparent !important; color:var(--muted) !important; border:1px solid var(--line) !important; transform:none !important; }
[class*="st-key-property_card_"] [class*="st-key-delete_"] button:hover,
[class*="st-key-agency_tools_"] button:hover { color:#e05260 !important; border-color:#e05260 !important; background:color-mix(in srgb,#e05260 8%,var(--panel)) !important; }
[class*="st-key-agency_tools_"] { padding:6px 0 14px; }
[class*="st-key-agency_tools_"] [data-testid="stHorizontalBlock"] { align-items:center; }
[class*="st-key-agency_confirmation_"] { padding:16px; border:1px solid color-mix(in srgb,#e05260 45%,var(--line)); border-radius:12px; background:var(--panel); margin-bottom:16px; }
[class*="st-key-confirm_delete_agency_"] button { background:#c83d4c !important; color:white !important; }
.selected-agency-header { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:6px; }
.selected-agency-header > span:not(.agency-new-dot) { margin-left:auto; }
.st-key-filtro_imobiliaria label p, .st-key-busca_anuncio label p { color:var(--text) !important; }
@media(max-width:640px) {
  [class*="st-key-property_card_"] { padding:10px; }
  [class*="st-key-agency_tools_"] [data-testid="stHorizontalBlock"] { gap:6px; }
  [class*="st-key-agency_tools_"] button { width:100%; }
  [class*="st-key-property_card_"] [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; }
  [class*="st-key-property_card_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { width:calc(50% - 8px) !important; min-width:0 !important; flex:1 1 0 !important; }
  .results-summary { margin-bottom:14px; }
}
</style>
'''


def render_results_styles():
    st.markdown(RESULTS_CSS, unsafe_allow_html=True)
