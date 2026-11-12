"""Shared presentation for the results and favourites lists."""
import streamlit as st


RESULTS_CSS = '''
<style>
.results-summary { display:flex; flex-wrap:wrap; gap:18px; margin:4px 0 18px; color:var(--muted); font-size:.85rem; }
.results-summary strong { color:var(--text); font-weight:700; }
[class*="st-key-property_card_"] { background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:0 0 12px; overflow:hidden; margin:0 0 12px; box-shadow:0 4px 14px #00000008; }
[class*="st-key-property_card_"] > div { gap:8px !important; }
[class*="st-key-property_card_"] .wa-preview { height:330px; margin:0 0 2px; border:0; border-radius:0; background:var(--panel); color:var(--text); }
[class*="st-key-property_card_"] .wa-preview-main { display:flex; flex-direction:column; height:auto; background:var(--panel); }
[class*="st-key-property_card_"] .wa-preview-photo,
[class*="st-key-property_card_"] .wa-preview-fallback { flex:0 0 155px; height:155px; width:100%; background-color:var(--panel-hover,var(--bg)); }
[class*="st-key-property_card_"] .wa-preview-fallback { background:linear-gradient(135deg,color-mix(in srgb,var(--green) 6%,var(--panel)),var(--bg)); color:var(--muted); font-size:2.8rem; }
[class*="st-key-property_card_"] .wa-preview-info { display:flex; flex-direction:column; padding:16px 16px 4px; }
[class*="st-key-property_card_"] .wa-preview-title { order:1; color:var(--text); font-size:1rem; line-height:1.4; font-weight:600; min-height:2.8em; }
[class*="st-key-property_card_"] .wa-preview-price { order:2; color:var(--text); font-size:1.25rem; font-weight:750; margin:8px 0 5px; }
[class*="st-key-property_card_"] .wa-preview-description { order:3; color:var(--muted); font-size:.8rem; line-height:1.4; margin:0; -webkit-line-clamp:1; }
[class*="st-key-property_card_"] a.wa-preview-url { color:var(--muted) !important; font-size:.78rem !important; text-decoration:none !important; padding:7px 16px; height:32px; }
[class*="st-key-property_card_"] a.wa-preview-url:hover { color:var(--green) !important; }
[class*="st-key-property_card_"] [data-testid="stButton"] { padding:0 12px; }
[class*="st-key-property_card_"] [data-testid="stHorizontalBlock"] { padding:0 12px; gap:8px !important; flex-wrap:nowrap !important; }
[class*="st-key-property_card_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { min-width:0 !important; flex:1 1 0 !important; width:50% !important; }
[class*="st-key-property_card_"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] { padding:0; }
[class*="st-key-property_card_"] button { min-height:38px !important; height:auto !important; font-size:.8rem !important; transform:none !important; box-shadow:none !important; }
[class*="st-key-property_card_"] [class*="st-key-reviews_"] button { background:transparent !important; color:var(--muted) !important; border:0 !important; }
[class*="st-key-property_card_"] [class*="st-key-favorite"] button { background:color-mix(in srgb,var(--green) 10%,var(--panel)) !important; color:var(--text) !important; border:1px solid color-mix(in srgb,var(--green) 25%,var(--line)) !important; }
[class*="st-key-property_card_"] [class*="st-key-delete_"] button,
[class*="st-key-agency_tools_"] button,
[class*="st-key-agency_confirmation_"] [class*="st-key-cancel_delete_agency_"] button { background:transparent !important; color:var(--muted) !important; border:1px solid var(--line) !important; transform:none !important; }
[class*="st-key-property_card_"] [class*="st-key-delete_"] button:hover,
[class*="st-key-agency_tools_"] button:hover { color:#e05260 !important; border-color:#e05260 !important; }
[class*="st-key-agency_tools_"] { padding:0 0 12px; }
[class*="st-key-agency_tools_"] [data-testid="stHorizontalBlock"] { align-items:center; }
[class*="st-key-agency_confirmation_"] { padding:14px 16px; border:1px solid var(--line); border-left:3px solid var(--green); border-radius:10px; background:var(--panel); margin-bottom:16px; }
.agency-confirm-title { color:var(--text); font-size:.9rem; font-weight:600; line-height:1.4; }
.agency-confirm-description { color:var(--muted); font-size:.8rem; line-height:1.5; margin:4px 0 10px; }
[class*="st-key-agency_confirmation_"] [data-testid="stHorizontalBlock"] { gap:8px !important; flex-wrap:nowrap !important; justify-content:flex-start; }
[class*="st-key-agency_confirmation_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { flex:0 0 auto !important; width:auto !important; min-width:0 !important; }
[class*="st-key-agency_confirmation_"] button { width:auto !important; min-height:32px !important; height:32px !important; padding:4px 12px !important; border-radius:8px !important; box-shadow:none !important; transform:none !important; }
[class*="st-key-agency_confirmation_"] button p { font-size:.8rem !important; }
[class*="st-key-agency_confirmation_"] [class*="st-key-confirm_delete_agency_"] button { background:var(--green) !important; color:#102419 !important; border:1px solid var(--green) !important; }
[class*="st-key-agency_confirmation_"] [class*="st-key-confirm_delete_agency_"] button:hover { background:var(--green-hover) !important; }
[class*="st-key-agency_confirmation_"] [class*="st-key-cancel_delete_agency_"] button:hover { background:var(--panel-hover,var(--bg)) !important; color:var(--text) !important; }
.selected-agency-header { display:flex; align-items:center; flex-wrap:wrap; gap:8px; padding:10px 0; background:transparent; border:0; margin:8px 0; font-size:1.2rem; }
.selected-agency-header > span:not(.agency-new-dot) { margin-left:auto; color:var(--muted); }
.date-time-label { border:0; background:transparent; color:var(--muted); font-size:.78rem; font-weight:400; padding:8px 0; margin:8px 0 0; }
.price-band-label { background:transparent; border:0; border-bottom:1px solid var(--line); border-radius:0; font-size:.9rem; padding:8px 0 12px; margin:0 0 16px; }
.st-key-filtro_imobiliaria label p, .st-key-busca_anuncio label p { color:var(--text) !important; }
@media(max-width:640px) {
  .results-summary { gap:12px; margin-bottom:14px; }
  [class*="st-key-agency_tools_"] [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; }
  [class*="st-key-agency_tools_"] [data-testid="stColumn"] { min-width:0 !important; width:50% !important; flex:1 1 0 !important; }
}
</style>
'''


def render_results_styles():
    st.markdown(RESULTS_CSS, unsafe_allow_html=True)
