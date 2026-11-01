"""Login, cadastro de perfis e aprovação administrativa."""
from io import BytesIO
import json
import base64
import re
import time
import warnings
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

import auth_store as store

SESSION_TIMEOUT = 30 * 60
MAX_AVATAR_BYTES = 2 * 1024 * 1024
THEME_FILE = Path(__file__).resolve().parent / ".tema.json"
THEMES = {
    "Escuro": {
        "icon": "🌙", "key": "escuro", "bg": "#121212", "panel": "#181818",
        "line": "#282828", "text": "#f5f5f5", "muted": "#b3b3b3",
    },
    "Branco e verde": {
        "icon": "🌿", "key": "branco_verde", "bg": "#f4f8f5", "panel": "#ffffff",
        "line": "#b8c7bd", "text": "#17241b", "muted": "#52645a",
    },
}


def _current_theme():
    try:
        value = json.loads(THEME_FILE.read_text(encoding="utf-8")).get("tema")
    except (OSError, json.JSONDecodeError, AttributeError):
        value = None
    return value if value in THEMES else "Escuro"


def _save_theme(theme):
    THEME_FILE.write_text(
        json.dumps({"tema": theme}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _render_auth_styles():
    theme = THEMES[_current_theme()]
    selected = theme["key"]
    st.markdown(
        f"""<style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
        html, body, [data-testid="stAppViewContainer"] {{ font-family:'DM Sans',sans-serif; }}
        :root {{
          --bg:{theme['bg']}; --panel:{theme['panel']}; --line:{theme['line']};
          --text:{theme['text']}; --muted:{theme['muted']};
          --field-bg:{'#181818' if selected == 'escuro' else '#ffffff'};
          --field-border:#353333;
          --field-focus-border:{'#777777' if selected == 'escuro' else '#32cb79'};
          --eye-color:{'#32cb79' if selected == 'escuro' else theme['muted']};
          --green:#32cb79; --green-hover:#51d891;
        }}
        [data-testid="stTextInput"] [class*="st-emotion-cache"],
        [data-testid="stNumberInput"] [class*="st-emotion-cache"],
        [data-testid="stDateInput"] [class*="st-emotion-cache"],
        [data-testid="stTimeInput"] [class*="st-emotion-cache"],
        [data-testid="stTextArea"] [class*="st-emotion-cache"],
        [data-testid="stSelectbox"] [class*="st-emotion-cache"],
        [data-testid="stMultiSelect"] [class*="st-emotion-cache"],
        [data-testid="stFileUploader"] [class*="st-emotion-cache"] {{
          border-color:var(--field-border) !important; background-color:var(--field-bg) !important;
        }}
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
          background:var(--bg) !important; color:var(--text) !important;
        }}
        [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {{
          background:#e11236 !important; color:#fff !important;
          border:1px solid #ff294b !important; box-shadow:0 0 0 1px #ff294b55;
        }}
        [data-testid="stAlertContentError"],
        [data-testid="stAlertContentError"] * {{ color:#fff !important; white-space:pre-wrap; }}
        [data-testid="stAlertContentError"] svg {{ fill:currentColor !important; stroke:currentColor !important; }}
        .st-key-initial_password_notice [data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {{
          background:#f59e0b !important; border:1px solid #fb923c !important;
          color:#211304 !important; box-shadow:0 4px 14px #f59e0b22;
        }}
        .st-key-initial_password_notice [data-testid="stAlertContentInfo"],
        .st-key-initial_password_notice [data-testid="stAlertContentInfo"] * {{
          color:#211304 !important;
        }}
        .st-key-initial_password_notice [data-testid="stAlertContentInfo"] svg {{
          fill:currentColor !important; stroke:currentColor !important;
        }}
        .stApp[data-test-script-state="running"] div[data-testid="stElementContainer"]:has(.st-key-auth_theme_float),
        .stApp[data-test-script-state="running"] .st-key-auth_theme_float,
        .stApp[data-test-script-state="rerunRequested"] div[data-testid="stElementContainer"]:has(.st-key-auth_theme_float),
        .stApp[data-test-script-state="rerunRequested"] .st-key-auth_theme_float,
        .stApp[data-test-script-state="stopRequested"] div[data-testid="stElementContainer"]:has(.st-key-auth_theme_float),
        .stApp[data-test-script-state="stopRequested"] .st-key-auth_theme_float {{
          visibility:hidden !important; opacity:0 !important; pointer-events:none !important;
          transition:none !important;
        }}
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"], [data-testid="stHeader"] {{
          display:none !important;
        }}
        [data-testid="stMainBlockContainer"] {{
          width:100% !important; max-width:none !important;
          padding:2rem 1rem 3rem !important;
        }}
        .st-key-auth_shell {{
          box-sizing:border-box; width:30vw; max-width:600px; min-width:320px;
          margin:4vh auto !important; padding:clamp(22px,3.5vw,44px);
          color:var(--text); background:var(--panel);
          border:1px solid var(--line); border-radius:22px;
          box-shadow:0 20px 70px #0002;
        }}
        .st-key-auth_back [data-testid="stPageLink"] a {{
          display:inline-flex; align-items:center; min-height:36px; padding:6px 10px !important;
          border-radius:9px; color:var(--muted) !important; text-decoration:none !important;
        }}
        .st-key-auth_back [data-testid="stPageLink"] a:hover {{
          color:var(--green) !important; background:color-mix(in srgb,var(--green) 10%,transparent);
        }}
        .st-key-auth_shell h1 {{ text-align:center; color:var(--text); }}
        .st-key-auth_shell [data-testid="stCaptionContainer"] {{
          text-align:center; color:var(--muted);
        }}
        .st-key-auth_shell [data-testid="stTabs"] button {{
          color:var(--muted);
        }}
        .st-key-auth_shell [data-testid="stTabs"] button[aria-selected="true"] {{
          color:var(--green) !important;
        }}
        .st-key-auth_route_nav [data-testid="stHorizontalBlock"] {{ width:max-content !important; gap:0; border-bottom:1px solid var(--line); margin:8px 0 18px; }}
        .st-key-auth_route_nav [data-testid="stColumn"] {{ min-width:0 !important; width:max-content !important; flex:0 0 auto !important; padding-right:8px; }}
        .st-key-auth_route_nav [data-testid="stPageLink"] {{ padding:0 !important; }}
        .st-key-auth_route_nav a {{ display:block; padding:10px 14px !important; border-bottom:2px solid transparent; color:var(--muted) !important; text-decoration:none !important; white-space:nowrap; }}
        .st-key-auth_route_nav a:hover {{ color:var(--text) !important; }}
        .st-key-auth_route_login a, .st-key-auth_route_cadastrar a {{ border-bottom:2px solid var(--green); color:var(--text) !important; }}
        .st-key-auth_shell [data-testid="stForm"] {{
          padding:1rem 1.15rem; border:1px solid var(--line);
          border-radius:16px; background:color-mix(in srgb,var(--panel) 94%,var(--bg));
        }}
        .st-key-auth_shell [data-testid="stTextInput"] [data-baseweb="input"],
        .st-key-auth_shell [data-testid="stNumberInput"] [data-baseweb="input"],
        .st-key-auth_shell [data-testid="stDateInput"] [data-baseweb="input"],
        .st-key-auth_shell [data-testid="stTimeInput"] [data-baseweb="input"] {{
          box-sizing:border-box; min-height:42px; overflow:hidden;
          background:var(--field-bg) !important; border:1px solid var(--field-border) !important;
          border-radius:9px !important; box-shadow:none !important;
        }}
        .st-key-auth_shell [data-testid="stTextInput"] [data-baseweb="input"]:focus-within,
        .st-key-auth_shell [data-testid="stNumberInput"] [data-baseweb="input"]:focus-within,
        .st-key-auth_shell [data-testid="stDateInput"] [data-baseweb="input"]:focus-within,
        .st-key-auth_shell [data-testid="stTimeInput"] [data-baseweb="input"]:focus-within {{
          border-color:var(--field-focus-border) !important;
        }}
        .st-key-auth_shell [data-baseweb="base-input"] {{
          min-height:40px; background:transparent !important; border:0 !important;
          box-shadow:none !important; box-sizing:border-box;
        }}
        .st-key-auth_shell [data-testid="stTextInput"] input,
        .st-key-auth_shell [data-testid="stNumberInput"] input,
        .st-key-auth_shell [data-testid="stDateInput"] input,
        .st-key-auth_shell [data-testid="stTimeInput"] input {{
          display:block; box-sizing:border-box; width:100%; min-height:40px;
          background:transparent !important; color:var(--text) !important;
          border:0 !important; border-radius:0 !important; box-shadow:none !important;
        }}
        .st-key-auth_shell [data-baseweb="input"] button {{
          min-height:40px; background:var(--field-bg) !important; color:var(--eye-color) !important;
          border:0 !important; border-left:1px solid var(--field-border) !important;
          border-radius:0 !important; box-shadow:none !important;
        }}
        .st-key-auth_shell [data-baseweb="input"] button svg,
        .st-key-auth_shell [data-baseweb="input"] button svg path {{
          color:var(--eye-color) !important; stroke:var(--eye-color) !important;
        }}
        .st-key-auth_shell [data-testid="stTextArea"] textarea {{
          box-sizing:border-box; min-height:42px; color:var(--text) !important;
          background:var(--field-bg) !important; border:1px solid var(--field-border) !important;
          border-radius:9px !important; box-shadow:none !important;
        }}
        .st-key-auth_shell [data-testid="stTextArea"] textarea:focus {{
          border-color:var(--field-focus-border) !important;
        }}
        .st-key-auth_shell [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        .st-key-auth_shell [data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
          min-height:42px; background:var(--field-bg) !important; color:var(--text) !important;
          border:1px solid var(--field-border) !important; border-radius:9px !important;
          box-shadow:none !important;
        }}
        .st-key-auth_shell [data-baseweb="input"] button svg,
        .st-key-auth_shell [data-baseweb="input"] button svg path {{
          color:var(--eye-color) !important; stroke:var(--eye-color) !important;
        }}
        .st-key-auth_shell [data-testid="InputInstructions"] {{
          display:flex !important; justify-content:flex-end; color:var(--muted) !important;
          font-size:.72rem !important; white-space:nowrap;
        }}
        .st-key-auth_shell [data-testid="InputInstructions"] span {{ display:none !important; }}
        .st-key-auth_shell [data-testid="InputInstructions"]::after {{
          content:"Pressione Enter para aplicar";
        }}
        .st-key-auth_shell [data-testid="stForm"] [data-testid="InputInstructions"]::after {{
          content:"Pressione Enter para enviar o formulário";
        }}
        .st-key-auth_shell [data-baseweb="select"] > div {{
          background:var(--field-bg) !important;
          color:var(--text) !important; border:1px solid var(--field-border) !important;
          border-radius:9px !important;
        }}
        .st-key-auth_shell hr {{
          border-color:var(--line) !important; border-top-color:var(--line) !important;
          opacity:1 !important;
        }}
        .st-key-auth_shell label, .st-key-auth_shell p,
        .st-key-auth_shell [data-testid="stMarkdownContainer"] {{
          color:var(--text);
        }}
        .st-key-auth_shell [data-testid="stButton"] button {{
          border-radius:11px !important;
        }}
        .st-key-auth_google_login [data-testid="stButton"] button {{
          display:flex !important; align-items:center; justify-content:center; gap:10px;
          min-height:48px; background:#f1f3f4 !important; color:#202124 !important;
          border:1px solid #dadce0 !important; border-radius:8px !important;
          font-family:Arial,sans-serif !important; font-size:15px !important;
          font-weight:500 !important; box-shadow:0 1px 2px #0002 !important;
        }}
        .st-key-auth_google_login [data-testid="stButton"] button:hover {{
          background:#e8eaed !important; border-color:#c6c9cc !important;
        }}
        .st-key-auth_google_login [data-testid="stButton"] button::before {{
          content:"G"; font:bold 20px Arial,sans-serif;
          background:conic-gradient(from -45deg,#4285f4 0 25%,#34a853 25% 48%,#fbbc05 48% 68%,#ea4335 68% 83%,#4285f4 83%);
          -webkit-background-clip:text; background-clip:text; color:transparent;
        }}
        div[data-testid="stElementContainer"].st-key-auth_theme_float,
        div[data-testid="stElementContainer"]:has(.st-key-auth_theme_float) {{
          position:fixed !important; top:16px; right:18px; z-index:9999;
          width:max-content !important; height:auto !important; margin:0 !important;
        }}
        .st-key-auth_theme_float {{
          position:fixed !important; top:16px; right:18px; z-index:10000;
          width:max-content; padding:4px 7px; border:1px solid var(--line);
          border-radius:18px; background:color-mix(in srgb,var(--panel) 90%,transparent);
          backdrop-filter:blur(12px); box-shadow:0 8px 28px #0003;
        }}
        .st-key-auth_theme_float [data-testid="stHorizontalBlock"] {{
          width:max-content !important; gap:2px;
        }}
        .st-key-auth_theme_float [data-testid="stColumn"] {{
          min-width:0 !important; width:42px !important; flex:0 0 42px !important;
        }}
        .st-key-auth_theme_float [data-testid="stButton"] button {{
          width:48px !important; min-width:48px !important;
          height:44px !important; min-height:44px !important;
          padding:0 !important; border:1px solid transparent !important;
          border-radius:13px !important; background:transparent !important;
          color:var(--text) !important; box-shadow:none !important;
          font-size:1.35rem !important;
        }}
        .st-key-auth_theme_{selected} [data-testid="stButton"] button {{
          border-color:var(--green) !important; background:#32cb7918 !important;
        }}
        .auth-brand {{ display:flex; align-items:center; justify-content:center; gap:14px; margin:0 auto 14px; }}
        .auth-brand img {{ display:block; width:58px; height:58px; object-fit:contain; }}
        .auth-brand h1 {{ margin:0; text-align:left !important; font-size:clamp(1.8rem,4vw,2.6rem); line-height:1.1; color:var(--text); }}
        .st-key-auth_landing {{
          width:min(1180px,100%); margin:1rem auto 3rem; padding:0 clamp(8px,3vw,30px);
          color:var(--text);
        }}
        .st-key-auth_landing_header {{ padding:10px 0 24px; border-bottom:1px solid var(--line); }}
        .st-key-auth_landing_header [data-testid="stHorizontalBlock"] {{ align-items:center; }}
        .st-key-auth_home_desktop_links {{ display:block; }}
        .st-key-auth_home_mobile_links {{ display:none !important; }}
        .st-key-auth_home_desktop_links [data-testid="stHorizontalBlock"] {{ justify-content:flex-end; gap:10px; }}
        .st-key-auth_home_login_button [data-testid="stButton"] button,
        .st-key-auth_home_register_button [data-testid="stButton"] button {{
          min-height:46px; padding:0 20px !important; border-radius:10px !important;
          font-weight:700 !important; transition:transform .15s ease,box-shadow .15s ease,background .15s ease;
        }}
        .st-key-auth_home_login_button [data-testid="stButton"] button {{
          background:var(--panel) !important; color:var(--text) !important;
          border:1px solid var(--line) !important; box-shadow:none !important;
        }}
        .st-key-auth_home_login_button [data-testid="stButton"] button:hover {{
          background:var(--panel-hover) !important; border-color:var(--green) !important;
          transform:translateY(-2px);
        }}
        .st-key-auth_home_register_button [data-testid="stButton"] button {{
          background:var(--green) !important; color:#fff !important; border:1px solid var(--green) !important;
          box-shadow:0 5px 16px #32cb7933 !important;
        }}
        .st-key-auth_home_register_button [data-testid="stButton"] button:hover {{
          background:var(--green-hover) !important; border-color:var(--green-hover) !important;
          box-shadow:0 8px 22px #32cb7955 !important; transform:translateY(-2px);
        }}
        .st-key-auth_home_mobile_login [data-testid="stPageLink"] a,
        .st-key-auth_home_mobile_register [data-testid="stPageLink"] a {{
          display:flex; align-items:center; justify-content:center; min-height:46px;
          padding:0 16px !important; border:1px solid var(--line); border-radius:10px;
          color:var(--text) !important; text-decoration:none !important; font-weight:700;
        }}
        .st-key-auth_home_mobile_register [data-testid="stPageLink"] a {{
          background:var(--green); border-color:var(--green); color:#fff !important;
        }}
        .auth-landing-brand {{ display:flex; align-items:center; gap:12px; font-size:1.25rem; font-weight:700; color:var(--text); }}
        .auth-landing-brand img {{ width:44px; height:44px; object-fit:contain; }}
        .auth-landing-links {{ display:flex; align-items:center; gap:22px; }}
        .auth-landing-links a {{
          display:inline-flex; align-items:center; justify-content:center; min-height:46px;
          padding:0 20px; border:1px solid var(--line); border-radius:10px;
          color:var(--text) !important; font-weight:700; text-decoration:none !important;
          transition:transform .15s ease,background .15s ease,border-color .15s ease,box-shadow .15s ease;
        }}
        .auth-landing-links a:hover {{ transform:translateY(-2px); border-color:var(--green); box-shadow:0 6px 18px #0003; }}
        .auth-landing-links .auth-link-login {{ background:var(--panel); }}
        .auth-landing-links .auth-link-login:hover {{ background:var(--panel-hover); }}
        .auth-landing-links .auth-link-register {{
          background:var(--green); border-color:var(--green); color:#fff !important;
          box-shadow:0 5px 16px #32cb7933;
        }}
        .auth-landing-links .auth-link-register:hover {{
          background:var(--green-hover); border-color:var(--green-hover); color:#fff !important;
          box-shadow:0 8px 22px #32cb7955;
        }}
        .auth-landing-hero {{ display:grid; grid-template-columns:1.1fr .9fr; align-items:center; gap:clamp(24px,5vw,64px); padding:clamp(44px,8vw,100px) 0 56px; }}
        .auth-landing-eyebrow {{ color:var(--green); font-weight:700; letter-spacing:.16em; text-transform:uppercase; font-size:.82rem; }}
        .auth-landing-hero h1 {{ margin:16px 0; font-size:clamp(2.4rem,5.6vw,4.6rem); line-height:1.04; letter-spacing:-.04em; color:var(--text); }}
        .auth-landing-hero p {{ max-width:640px; color:var(--muted); font-size:clamp(1.1rem,1.7vw,1.35rem); line-height:1.6; }}
        .auth-landing-signup {{ text-align:center; }}
        .auth-landing-announcement {{ display:inline-flex; align-items:center; gap:10px; padding:9px 16px; border:1px solid var(--line); border-radius:999px; color:var(--text); background:color-mix(in srgb,var(--panel) 78%,var(--bg)); font-weight:600; }}
        .auth-landing-announcement span {{ color:var(--green); }}
        .auth-landing-signup h2 {{ margin:18px auto 26px; max-width:760px; color:var(--text); font-size:clamp(2rem,4.8vw,3.6rem); line-height:1.08; letter-spacing:-.035em; }}
        .st-key-auth_landing_signup {{ box-sizing:border-box; max-width:900px; margin:8px auto 46px; padding:clamp(24px,5vw,48px); background:var(--panel); border:1px solid var(--line); border-radius:22px; box-shadow:0 18px 50px #0002; }}
        .st-key-auth_landing_signup [data-testid="stForm"] {{ border:0; padding:0; background:transparent; }}
        .st-key-auth_landing_signup [data-testid="stTextInput"] [data-baseweb="input"],
        .st-key-auth_landing_signup [data-testid="stTextInput"] [data-baseweb="base-input"],
        .st-key-auth_landing_signup [data-testid="stTextInput"] input {{
          min-height:44px; background:transparent !important; color:var(--text) !important;
          border:0 !important; outline:0 !important; border-radius:0 !important;
          box-shadow:none !important;
        }}
        .st-key-auth_landing_email [data-baseweb="input"],
        .st-key-auth_landing_email [data-baseweb="base-input"],
        .st-key-auth_landing_email input,
        .st-key-auth_landing_email [class*="st-emotion-cache"] {{
          background:transparent !important; border:0 !important; outline:0 !important;
          border-radius:0 !important; box-shadow:none !important;
        }}
        .st-key-auth_landing_signup [data-testid="stForm"] [data-testid="stHorizontalBlock"] {{
          box-sizing:border-box; width:80%; margin:0 auto; padding:4px; gap:0 !important;
          align-items:stretch; border:1px solid var(--field-border); border-radius:10px;
          background:color-mix(in srgb,var(--field-bg) 94%,var(--line));
        }}
        .st-key-auth_landing_signup [data-testid="stForm"] [data-testid="stColumn"]:first-child {{ padding-right:0 !important; }}
        .st-key-auth_landing_signup [data-testid="stForm"] [data-testid="stColumn"]:last-child {{ padding-left:0 !important; }}
        .st-key-auth_landing_signup [data-testid="stFormSubmitButton"] button {{
          min-height:44px; border-radius:7px !important; background:#078b36 !important;
          color:#fff !important; border:0 !important; font-size:1rem !important; font-weight:700 !important;
        }}
        .st-key-auth_landing_signup [data-testid="stFormSubmitButton"] button:hover {{ background:#117a3b !important; border-color:#117a3b !important; }}
        .st-key-auth_landing_cta {{ max-width:560px; }}
        .st-key-auth_landing_cta [data-testid="stPageLink"] a {{ min-height:52px; border-radius:12px !important; font-size:1.08rem !important; font-weight:700 !important; }}
        .auth-landing-cta {{ display:flex; gap:14px; flex-wrap:wrap; margin-top:28px; }}
        .auth-landing-preview {{ border:1px solid var(--line); border-radius:22px; padding:22px; background:var(--panel); box-shadow:0 22px 60px #0003; transform:rotate(1deg); }}
        .auth-preview-top {{ color:var(--muted); font-size:.95rem; margin-bottom:18px; }}
        .auth-preview-card {{ border:1px solid var(--line); border-radius:14px; padding:16px; margin-top:12px; background:color-mix(in srgb,var(--panel) 85%,var(--bg)); }}
        .auth-preview-card strong {{ display:block; margin-bottom:7px; font-size:1rem; color:var(--text); }}
        .auth-preview-card span {{ color:var(--muted); }}
        .auth-preview-status {{ color:var(--green) !important; font-weight:700; }}
        .auth-landing-features {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; padding:20px 0 50px; }}
        .auth-feature {{ padding:22px; background:var(--panel); border:1px solid var(--line); border-radius:16px; }}
        .auth-feature b {{ display:block; margin-bottom:8px; color:var(--text); font-size:1.1rem; }}
        .auth-feature p {{ margin:0; color:var(--muted); line-height:1.5; }}
        .auth-password-feedback {{ margin:-.2rem 0 1rem; padding:15px 16px; border:1px solid color-mix(in srgb,var(--line) 78%,var(--green) 22%); border-radius:15px; background:linear-gradient(145deg,color-mix(in srgb,var(--panel) 92%,var(--bg)),color-mix(in srgb,var(--panel) 82%,var(--bg))); box-shadow:0 7px 20px #0002; }}
        .auth-password-heading {{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:10px; }}
        .auth-password-heading strong {{ font-size:.98rem; letter-spacing:.01em; }}
        .auth-password-count {{ color:var(--muted); font-size:.8rem; white-space:nowrap; }}
        .auth-password-feedback.weak .auth-password-heading strong {{ color:#e8ad55 !important; }}
        .auth-password-feedback.strong .auth-password-heading strong {{ color:var(--green) !important; }}
        .auth-password-meter {{ height:5px; margin-bottom:13px; overflow:hidden; border-radius:999px; background:color-mix(in srgb,var(--line) 85%,var(--bg)); }}
        .auth-password-meter span {{ display:block; height:100%; border-radius:inherit; background:linear-gradient(90deg,#e8ad55,#32cb79); transition:width .2s ease; }}
        .auth-password-feedback ul {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px 16px; margin:0; padding:0; list-style:none; color:var(--muted); font-size:.88rem; line-height:1.4; }}
        .auth-password-feedback li {{ display:flex; align-items:flex-start; gap:8px; min-width:0; }}
        .auth-password-feedback li.passed {{ color:var(--green) !important; }}
        .auth-password-feedback li.pending {{ color:var(--muted) !important; }}
        .st-key-auth_crop_controls [data-testid="stButton"] button {{ min-height:54px; border-radius:13px !important; font-size:1.05rem !important; font-weight:700 !important; }}
        .st-key-auth_photo_crop [data-testid="stSlider"] {{ padding-top:0; }}
        @media (max-width:768px) {{
          [data-testid="stMainBlockContainer"] {{ padding:.5rem .65rem 1.5rem !important; }}
          .st-key-auth_shell {{
            width:100% !important; min-width:0 !important; max-width:560px;
            margin:1vh auto !important; padding:18px 14px;
            border-radius:18px;
          }}
          .st-key-auth_shell [data-testid="stForm"] {{ padding:.6rem .65rem; }}
          .st-key-auth_theme_float {{ top:calc(env(safe-area-inset-top, 0px) + 10px); right:10px; }}
          .auth-brand {{ gap:10px; margin-bottom:12px; }}
          .auth-brand img {{ width:48px; height:48px; }}
          .st-key-auth_landing_header [data-testid="stHorizontalBlock"] {{ flex-direction:column; align-items:stretch; gap:12px; }}
          .auth-landing-brand {{ font-size:1.05rem; }}
          .st-key-auth_home_desktop_links {{ display:none !important; }}
          .st-key-auth_home_mobile_links {{ display:block !important; }}
          .st-key-auth_home_mobile_links [data-testid="stHorizontalBlock"] {{ gap:10px; }}
          .st-key-auth_home_mobile_login [data-testid="stPageLink"] a,
          .st-key-auth_home_mobile_register [data-testid="stPageLink"] a {{ width:100%; box-sizing:border-box; }}
          .auth-landing-hero {{ grid-template-columns:1fr; padding:42px 0 30px; }}
          .auth-landing-hero h1 {{ font-size:clamp(2.25rem,11vw,3.5rem); }}
          .auth-landing-cta {{ flex-direction:column; }}
          .auth-landing-cta [data-testid="stPageLink"] a {{ width:100%; justify-content:center; }}
          .auth-landing-preview {{ transform:none; }}
          .st-key-auth_landing_signup {{ padding:22px 16px; margin-bottom:30px; }}
          .st-key-auth_landing_signup [data-testid="stForm"] [data-testid="stHorizontalBlock"] {{
            width:100%; padding:0; border:0; border-radius:0; background:transparent;
            flex-direction:column; gap:10px !important;
          }}
          .st-key-auth_landing_signup [data-testid="stForm"] [data-testid="stColumn"] {{ width:100% !important; flex:1 1 100% !important; padding:0 !important; }}
          .st-key-auth_landing_signup [data-baseweb="input"] {{ border:1px solid var(--field-border) !important; border-radius:10px !important; }}
          .st-key-auth_landing_signup [data-testid="stFormSubmitButton"] button {{ border-radius:10px !important; }}
          .auth-landing-features {{ grid-template-columns:1fr; padding-top:0; }}
          .st-key-auth_crop_controls [data-testid="stButton"] button {{ min-height:60px; }}
          .auth-password-feedback ul {{ grid-template-columns:1fr; }}
        }}
        </style>""",
        unsafe_allow_html=True,
    )


def _render_auth_brand():
    logo = Path(__file__).resolve().parent / "assets" / "findimob.svg"
    encoded_logo = base64.b64encode(logo.read_bytes()).decode("ascii")
    st.markdown(
        f'<div class="auth-brand"><img src="data:image/svg+xml;base64,{encoded_logo}" '
        'alt="Logo Find Imob"><h1>Find Imob</h1></div>',
        unsafe_allow_html=True,
    )


def _select_auth_theme(theme):
    _save_theme(theme)
    st.rerun()


def _render_theme_picker():
    if "auth_theme_open" not in st.session_state:
        st.session_state.auth_theme_open = True
    with st.container(key="auth_theme_float"):
        if st.session_state.auth_theme_open:
            cols = st.columns(3, gap="small")
            selected = _current_theme()
            for col, (theme, data) in zip(cols[:2], THEMES.items()):
                with col:
                    st.button(data["icon"], key=f"auth_theme_{data['key']}",
                              help=f"Usar o esquema {theme}",
                              type="primary" if theme == selected else "secondary",
                              on_click=_select_auth_theme, args=(theme,))
            with cols[2]:
                if st.button("×", key="auth_theme_close", help="Ocultar esquemas de cores"):
                    st.session_state.auth_theme_open = False
                    st.rerun()
        else:
            if st.button("🎨", key="auth_theme_open", help="Mostrar esquemas de cores"):
                st.session_state.auth_theme_open = True
                st.rerun()


def _decode_uploaded_photo(data):
    if not data or len(data) > MAX_AVATAR_BYTES:
        return None, "A foto precisa ter até 2 MB."
    try:
        Image.MAX_IMAGE_PIXELS = 16_000_000
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Use uma imagem JPEG, PNG ou WebP.")
                if source.width * source.height > 16_000_000:
                    raise ValueError("A imagem excede a resolução permitida.")
                image = ImageOps.exif_transpose(source)
                image.load()
                return image.convert("RGB"), None
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
            Image.DecompressionBombWarning):
        return None, "Não foi possível abrir essa imagem."
    except ValueError as error:
        return None, str(error)


def _make_cropped_photo(image, widget_prefix):
    width, height = image.size
    zoom = float(st.session_state.get(f"{widget_prefix}_crop_zoom", 1.0))
    x_position = int(st.session_state.get(f"{widget_prefix}_crop_x", 50))
    y_position = int(st.session_state.get(f"{widget_prefix}_crop_y", 50))
    side = max(1, int(min(width, height) / zoom))
    left = int((width - side) * x_position / 100)
    top = int((height - side) * y_position / 100)
    preview = image.crop((left, top, left + side, top + side))
    output = preview.resize((150, 150), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    output.save(buffer, format="JPEG", quality=90, optimize=True)
    cropped = buffer.getvalue()
    st.session_state[f"{widget_prefix}_cropped_photo"] = cropped
    return cropped


def _open_photo_crop_dialog(widget_prefix):
    st.session_state[f"{widget_prefix}_crop_dialog_open"] = True
    st.session_state["_active_photo_crop_prefix"] = widget_prefix


def _close_photo_crop_dialog():
    prefix = st.session_state.pop("_active_photo_crop_prefix", None)
    if prefix:
        st.session_state.pop(f"{prefix}_crop_dialog_open", None)


@st.dialog("Ajuste a foto do perfil", width="small", on_dismiss=_close_photo_crop_dialog)
def _render_photo_crop_dialog(widget_prefix, data):
    image, error = _decode_uploaded_photo(data)
    if error:
        st.error(error)
        return
    st.write("Aproxime e mova a foto até o rosto ficar dentro do quadrado.")
    st.slider(
        "Aproximar ou afastar", min_value=1.0, max_value=3.0, value=1.0, step=0.1,
        key=f"{widget_prefix}_crop_zoom",
    )
    st.caption("Use as setas para ajustar o enquadramento.")
    x_key, y_key = f"{widget_prefix}_crop_x", f"{widget_prefix}_crop_y"
    st.session_state.setdefault(x_key, 50)
    st.session_state.setdefault(y_key, 50)
    with st.container(key="auth_crop_controls"):
        top = st.columns([1, 1, 1])
        with top[1]:
            st.button(
                "Cima", key=f"{widget_prefix}_crop_up", use_container_width=True,
                on_click=lambda: st.session_state.__setitem__(y_key, min(100, st.session_state[y_key] + 8)),
            )
        middle = st.columns([1, 1, 1])
        with middle[0]:
            st.button(
                "Esquerda", key=f"{widget_prefix}_crop_left", use_container_width=True,
                on_click=lambda: st.session_state.__setitem__(x_key, min(100, st.session_state[x_key] + 8)),
            )
        with middle[1]:
            st.button(
                "Centralizar", key=f"{widget_prefix}_crop_center", use_container_width=True,
                on_click=lambda: (st.session_state.__setitem__(x_key, 50), st.session_state.__setitem__(y_key, 50)),
            )
        with middle[2]:
            st.button(
                "Direita", key=f"{widget_prefix}_crop_right", use_container_width=True,
                on_click=lambda: st.session_state.__setitem__(x_key, max(0, st.session_state[x_key] - 8)),
            )
        bottom = st.columns([1, 1, 1])
        with bottom[1]:
            st.button(
                "Baixo", key=f"{widget_prefix}_crop_down", use_container_width=True,
                on_click=lambda: st.session_state.__setitem__(y_key, max(0, st.session_state[y_key] - 8)),
            )
    cropped = _make_cropped_photo(image, widget_prefix)
    st.image(cropped, width=210, caption="Prévia quadrada de 150 x 150 px")
    if st.button("Usar esta foto", key=f"{widget_prefix}_crop_confirm", type="primary", use_container_width=True):
        st.session_state.pop(f"{widget_prefix}_crop_dialog_open", None)
        st.session_state.pop("_active_photo_crop_prefix", None)
        st.rerun()


def _crop_uploaded_photo(upload, widget_prefix):
    state_key = f"{widget_prefix}_cropped_photo"
    original_key = f"{widget_prefix}_original_photo"
    if upload is None:
        st.session_state.pop(state_key, None)
        st.session_state.pop(original_key, None)
        st.session_state.pop(f"{widget_prefix}_crop_dialog_open", None)
        return None, None
    data = upload.getvalue()
    image, error = _decode_uploaded_photo(data)
    if error:
        st.session_state.pop(state_key, None)
        st.session_state.pop(original_key, None)
        return None, error
    if st.session_state.get(original_key) != data:
        st.session_state[original_key] = data
        st.session_state[f"{widget_prefix}_crop_zoom"] = 1.0
        st.session_state[f"{widget_prefix}_crop_x"] = 50
        st.session_state[f"{widget_prefix}_crop_y"] = 50
        st.session_state.pop(f"{widget_prefix}_crop_dialog_open", None)
    cropped = _make_cropped_photo(image, widget_prefix)
    st.image(cropped, width=96, caption="Prévia")
    st.button(
        "Ajustar foto", key=f"{widget_prefix}_crop_open",
        on_click=_open_photo_crop_dialog, args=(widget_prefix,),
    )
    if st.session_state.get(f"{widget_prefix}_crop_dialog_open"):
        st.session_state["_active_photo_crop_prefix"] = widget_prefix
        _render_photo_crop_dialog(widget_prefix, data)
    return cropped, None


def _password_requirements(password):
    return (
        ("Pelo menos 8 caracteres", len(password) >= 8),
        ("Uma letra minúscula", any(char.islower() for char in password)),
        ("Uma letra maiúscula", any(char.isupper() for char in password)),
        ("Um número", any(char.isdigit() for char in password)),
        ("Um símbolo (por exemplo: !, @ ou #)", any(not char.isalnum() for char in password)),
    )


def _render_password_feedback(password):
    if not password:
        return
    requirements = _password_requirements(password)
    passed_count = sum(passed for _, passed in requirements)
    requirement_count = len(requirements)
    is_strong = passed_count == requirement_count and len(password) <= 128
    strength = "Senha forte" if is_strong else "Senha fraca"
    strength_class = "strong" if is_strong else "weak"
    progress = round(passed_count / requirement_count * 100)
    items = "".join(
        f'<li class="{"passed" if passed else "pending"}">'
        f'<span aria-hidden="true">{"✓" if passed else "○"}</span>'
        f'<span>{label}</span></li>'
        for label, passed in requirements
    )
    st.markdown(
        f'<div class="auth-password-feedback {strength_class}" aria-live="polite">'
        f'<div class="auth-password-heading"><strong>{strength}</strong>'
        f'<span class="auth-password-count">{passed_count} de {requirement_count} requisitos</span></div>'
        f'<div class="auth-password-meter" role="meter" aria-valuemin="0" '
        f'aria-valuemax="{requirement_count}" aria-valuenow="{passed_count}">'
        f'<span style="width:{progress}%"></span></div>'
        f'<ul>{items}</ul></div>',
        unsafe_allow_html=True,
    )


def _password_message(password):
    if len(password) < 8:
        return "A senha precisa ter pelo menos 8 caracteres."
    if len(password) > 128:
        return "A senha pode ter no máximo 128 caracteres."
    if not store.valid_password(password):
        return "Inclua maiúscula, minúscula, número e símbolo."
    return None


def _phone_message(phone):
    digits = re.sub(r"\D", "", phone)
    if not 8 <= len(digits) <= 15:
        return "Informe um telefone com 8 a 15 dígitos."
    return None


def _email_message(email):
    if not store.valid_email(email):
        return "Informe um e-mail válido."
    return None


def _set_authenticated(user):
    st.session_state.auth_user_id = user["id"]
    st.session_state.auth_last_activity = time.time()
    st.session_state.auth_avatar = user.get("avatar")


def _logout():
    for key in ("auth_user_id", "auth_last_activity", "auth_avatar"):
        st.session_state.pop(key, None)


def _show_error(slot, message):
    if message:
        slot.error(f"⚠️  {message}")


def _render_auth_route_links(active):
    with st.container(key="auth_route_nav"):
        left, right = st.columns([1, 1], gap="small")
        with left:
            with st.container(key="auth_route_login" if active == "login" else "auth_route_login_inactive"):
                st.page_link("pages/entrar.py", label="Entrar")
        with right:
            with st.container(key="auth_route_cadastrar" if active == "register" else "auth_route_cadastrar_inactive"):
                st.page_link("pages/cadastrar.py", label="Criar conta")


def _render_login():
    st.subheader("Entrar")
    with st.form("auth_login_form"):
        identifier = st.text_input("Usuário ou e-mail", key="auth_login_identifier")
        password = st.text_input("Senha", type="password", key="auth_login_password")
        submitted = st.form_submit_button(
            "Entrar", type="primary", use_container_width=True,
        )
    identifier_error = st.empty()
    password_error = st.empty()
    if submitted:
        if not identifier.strip():
            _show_error(identifier_error, "Informe seu usuário ou e-mail.")
        elif not password:
            _show_error(password_error, "Informe sua senha.")
        else:
            user, result = store.authenticate(identifier, password)
            if user:
                st.session_state.auth_user_id = user["id"]
                st.session_state.auth_last_activity = time.time()
                st.session_state.auth_avatar = user.get("avatar")
                st.rerun()
            if result == "locked":
                _show_error(password_error, "Muitas tentativas. Aguarde 15 minutos.")
            elif result == "pending":
                _show_error(password_error, "Conta ainda aguarda aprovação do administrador.")
            else:
                _show_error(password_error, "Usuário/e-mail ou senha inválidos.")

    st.divider()
    if st.button("Continuar com Google", key="auth_google_login", use_container_width=True):
        try:
            config = st.secrets.get("auth", {})
            required = ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url")
            if not all(config.get(key) for key in required):
                st.warning("Login Google ainda não configurado. Configure as credenciais OIDC em .streamlit/secrets.toml.")
            else:
                st.login()
        except Exception:
            st.error("⚠️  Não foi possível iniciar o login Google. Confira a configuração OIDC em .streamlit/secrets.toml e reinicie o app.")


def _render_photo_upload(prefix, label, optional=False):
    st.markdown(f"**{label}{' (opcional)' if optional else ''}**")
    upload = st.file_uploader(
        "Escolha uma imagem",
        type=["jpg", "jpeg", "png", "webp"],
        key=f"{prefix}_avatar_upload",
        label_visibility="collapsed",
    )
    crop, error = _crop_uploaded_photo(upload, prefix)
    error_slot = st.empty()
    _show_error(error_slot, error)
    return crop, error_slot, error


def _render_initial_profile(user):
    with st.container(key="initial_password_notice"):
        st.info("A senha inicial é provisória. Complete seu perfil e crie uma nova senha para continuar.")
    full_name = st.text_input(
        "Nome completo", value=user["full_name"], key="initial_full_name"
    )
    full_name_error = st.empty()
    display_name = st.text_input(
        "Como quer ser chamado", value=user["display_name"],
        key="initial_display_name",
    )
    display_name_error = st.empty()
    default_email = "" if user["email"] == "admin@localhost" else user["email"]
    email = st.text_input("E-mail", value=default_email, key="initial_email")
    email_error = st.empty()
    phone = st.text_input("Telefone", value=user["phone"], key="initial_phone")
    phone_error = st.empty()
    photo, photo_error_slot, photo_error = _render_photo_upload(
        "initial", "Foto do perfil", optional=True
    )
    password = st.text_input("Nova senha", type="password", key="initial_password", live=True)
    _render_password_feedback(password)
    password_error = st.empty()
    confirmation = st.text_input(
        "Confirme a nova senha", type="password", key="initial_password_confirm"
    )
    confirmation_error = st.empty()
    if not st.button("Salvar e entrar", type="primary", key="initial_profile_submit", use_container_width=True):
        return False

    errors = {
        "full_name": "Informe seu nome completo." if len(full_name.strip()) < 2 else None,
        "display_name": "Informe como quer ser chamado." if len(display_name.strip()) < 2 else None,
        "email": _email_message(email),
        "phone": _phone_message(phone),
        "password": _password_message(password),
        "confirmation": "As senhas não coincidem." if password != confirmation else None,
        "photo": photo_error,
    }
    for message, slot in (
        (errors["full_name"], full_name_error),
        (errors["display_name"], display_name_error),
        (errors["email"], email_error),
        (errors["phone"], phone_error),
        (errors["password"], password_error),
        (errors["confirmation"], confirmation_error),
    ):
        _show_error(slot, message)
    if errors["photo"]:
        _show_error(photo_error_slot, errors["photo"])
        return False
    if any(errors[key] for key in (
        "full_name", "display_name", "email", "phone", "password", "confirmation"
    )):
        return False
    if not store.update_profile(
        user["id"], full_name, display_name, email, phone,
        avatar=photo, password=password,
    ):
        _show_error(email_error, "Este e-mail já está em uso.")
        return False
    _set_authenticated(store.get_user(user["id"]))
    st.rerun()
    return False


def _render_registration():
    full_name = st.text_input("Nome", key="signup_full_name")
    full_name_error = st.empty()
    email = st.text_input("E-mail", key="signup_email")
    email_error = st.empty()
    password = st.text_input("Senha", type="password", key="signup_password", live=True)
    _render_password_feedback(password)
    password_error = st.empty()
    if not st.button("Solicitar acesso", type="primary", key="signup_submit",
                     use_container_width=True):
        return
    errors = {
        "full_name": "Informe seu nome." if len(full_name.strip()) < 2 else None,
        "email": _email_message(email),
        "password": _password_message(password),
    }
    for message, slot in ((errors["full_name"], full_name_error),
                          (errors["email"], email_error),
                          (errors["password"], password_error)):
        _show_error(slot, message)
    if any(errors.values()):
        return
    if not store.create_user(full_name, full_name, email, "", password, None):
        _show_error(email_error, "Este e-mail já está em uso.")
        return
    st.success("Solicitação enviada. Complete os dados do perfil após a aprovação.")


def _open_home_auth_popup(route):
    st.session_state.auth_home_popup = route


def _close_home_auth_popup():
    st.session_state.pop("auth_home_popup", None)


@st.dialog("Acesse o Find Imob", width="small", on_dismiss=_close_home_auth_popup)
def _render_home_auth_popup(route):
    if route == "login":
        _render_login()
    elif route == "register":
        _render_registration()


def _auth_route_from_url():
    """Use the actual URL so the homepage works even after navigating between pages."""
    try:
        from urllib.parse import urlparse
        path = urlparse(st.context.url).path.rstrip("/")
        route = path.rsplit("/", 1)[-1]
        if route in {"entrar", "cadastrar"}:
            return "login" if route == "entrar" else "register"
        if not path:
            return None
    except (AttributeError, TypeError, ValueError):
        pass
    route = st.session_state.get("_auth_route_mode")
    return route if route in {"login", "register"} else None


def _render_homepage():
    logo = Path(__file__).resolve().parent / "assets" / "findimob.svg"
    encoded_logo = base64.b64encode(logo.read_bytes()).decode("ascii")
    with st.container(key="auth_landing"):
        with st.container(key="auth_landing_header"):
            brand_col, actions_col = st.columns([1, 1.25], vertical_alignment="center")
            with brand_col:
                st.markdown(
                    f'<div class="auth-landing-brand"><img src="data:image/svg+xml;base64,{encoded_logo}" alt="">Find Imob</div>',
                    unsafe_allow_html=True,
                )
            with actions_col:
                with st.container(key="auth_home_desktop_links"):
                    login_col, register_col = st.columns([.8, 1.2], gap="small")
                    with login_col:
                        st.button(
                            "Entrar", key="auth_home_login_button", use_container_width=True,
                            on_click=_open_home_auth_popup, args=("login",),
                        )
                    with register_col:
                        st.button(
                            "Criar minha conta", key="auth_home_register_button", use_container_width=True,
                            on_click=_open_home_auth_popup, args=("register",),
                        )
                with st.container(key="auth_home_mobile_links"):
                    login_col, register_col = st.columns([.8, 1.2], gap="small")
                    with login_col:
                        with st.container(key="auth_home_mobile_login"):
                            st.page_link("pages/entrar.py", label="Entrar")
                    with register_col:
                        with st.container(key="auth_home_mobile_register"):
                            st.page_link("pages/cadastrar.py", label="Criar minha conta")
        st.markdown(
            """<section class="auth-landing-hero">
              <div><div class="auth-landing-eyebrow">Find Imob · Operações imobiliárias</div>
              <h1>Anúncios organizados. Decisões mais fáceis.</h1>
              <p>Acompanhe portais imobiliários em um só lugar. Encontre anúncios coletados, veja novidades e consulte o histórico sem complicação.</p></div>
              <div class="auth-landing-preview" aria-label="Prévia do painel Find Imob">
                <div class="auth-preview-top">Seu painel de acompanhamento</div>
                <div class="auth-preview-card"><strong>Imóveis encontrados</strong><span>Seus anúncios ficam reunidos em uma lista clara.</span></div>
                <div class="auth-preview-card"><strong>Novas oportunidades</strong><span class="auth-preview-status">● Atualizações fáceis de identificar</span></div>
                <div class="auth-preview-card"><strong>Histórico organizado</strong><span>Consulte as coletas quando precisar.</span></div>
              </div>
            </section>""",
            unsafe_allow_html=True,
        )
        with st.container(key="auth_landing_signup"):
            st.markdown(
                '<section class="auth-landing-signup">'
                '<div class="auth-landing-announcement"><span>✦</span> Find Imob · oportunidades em um só lugar</div>'
                '<h2>Seu próximo imóvel começa com uma boa busca.</h2>'
                '</section>',
                unsafe_allow_html=True,
            )
            with st.form("auth_landing_signup_form", border=False):
                email_col, submit_col = st.columns([1.2, 1], gap="small", vertical_alignment="bottom")
                with email_col:
                    email = st.text_input(
                        "Seu e-mail", placeholder="Insira seu e-mail",
                        label_visibility="collapsed", key="auth_landing_email",
                    )
                with submit_col:
                    submitted = st.form_submit_button(
                        "Cadastrar-se no Find Imob", type="primary", use_container_width=True,
                    )
            if submitted:
                message = _email_message(email.strip())
                st.session_state.auth_landing_email_error = message
                if not message:
                    st.session_state.signup_email = email.strip()
                    st.switch_page("pages/cadastrar.py")
            if st.session_state.get("auth_landing_email_error"):
                st.error(f"⚠️  {st.session_state.auth_landing_email_error}")
        st.markdown(
            """<section class="auth-landing-features">
              <div class="auth-feature"><b>🔎 Encontre com facilidade</b><p>Pesquise entre os portais cadastrados sem precisar abrir cada site.</p></div>
              <div class="auth-feature"><b>📋 Tudo bem organizado</b><p>Veja os resultados e os favoritos em telas simples e diretas.</p></div>
              <div class="auth-feature"><b>🕒 Acompanhe no seu ritmo</b><p>O histórico ajuda você a conferir o que mudou, quando quiser.</p></div>
            </section>""",
            unsafe_allow_html=True,
        )
    popup_route = st.session_state.get("auth_home_popup")
    if popup_route in {"login", "register"}:
        _render_home_auth_popup(popup_route)


def render_auth_gate():
    store.initialize()
    try:
        identity = st.user
        if identity.is_logged_in and not st.session_state.get("auth_user_id"):
            user, status = store.authenticate_google(
                identity.get("sub"), identity.get("email"), identity.get("name"),
                identity.get("email_verified", False),
            )
            if user:
                _set_authenticated(user)
                st.rerun()
            if status == "pending":
                st.session_state.auth_google_pending = True
            elif status != "ok":
                st.session_state.auth_google_error = "Use uma conta Google com e-mail verificado."
    except (AttributeError, KeyError):
        pass
    user_id = st.session_state.get("auth_user_id")
    timed_out = False
    if user_id:
        user = store.get_user(user_id)
        last_activity = st.session_state.get("auth_last_activity", 0)
        if not user or not user["active"] or time.time() - last_activity > SESSION_TIMEOUT:
            timed_out = bool(user and user["active"])
            _logout()
        elif user["must_change_password"]:
            _render_auth_styles()
            with st.container(key="auth_shell"):
                _render_auth_brand()
                st.subheader("Proteja sua conta")
                _render_initial_profile(user)
            _render_theme_picker()
            return False
        else:
            st.session_state.auth_last_activity = time.time()
            return True

    _render_auth_styles()
    auth_route = _auth_route_from_url()
    if auth_route is None:
        _render_homepage()
        _render_theme_picker()
        return False
    with st.container(key="auth_shell"):
        with st.container(key="auth_back"):
            st.page_link("app.py", label="Voltar")
        _render_auth_brand()
        st.caption("Entre para acessar o painel ou solicite a criação da sua conta.")
        if timed_out:
            st.warning("Sua sessão expirou. Entre novamente.")
        if st.session_state.pop("auth_google_pending", False):
            st.info("Conta Google registrada. O acesso aguarda aprovação do administrador.")
        if st.session_state.pop("auth_google_error", None):
            st.error("⚠️  Use uma conta Google com e-mail verificado.")
        _render_auth_route_links(auth_route)
        if auth_route == "register":
            _render_registration()
        else:
            _render_login()
    _render_theme_picker()
    return False



def render_profile_page():
    user_id = st.session_state.get("auth_user_id")
    user = store.get_user(user_id) if user_id else None
    if not user:
        st.info("Entre para editar seu perfil.")
        return
    st.subheader("Meu perfil")
    if user.get("avatar"):
        st.image(user["avatar"], width=100)
    full_name = st.text_input("Nome completo", value=user["full_name"], key="profile_full_name")
    full_error = st.empty()
    display_name = st.text_input("Como quer ser chamado", value=user["display_name"], key="profile_display_name")
    display_error = st.empty()
    email = st.text_input("E-mail", value=user["email"], key="profile_email")
    email_error = st.empty()
    phone = st.text_input("Telefone", value=user["phone"], key="profile_phone")
    phone_error = st.empty()
    photo, photo_slot, photo_error = _render_photo_upload("profile", "Foto do perfil", optional=True)
    new_password = st.text_input("Nova senha (opcional)", type="password", key="profile_password")
    password_error = st.empty()
    confirmation = st.text_input("Confirme a nova senha", type="password", key="profile_password_confirm")
    confirmation_error = st.empty()
    if not st.button("Salvar perfil", type="primary", key="profile_save"):
        return
    errors = {
        "full": "Informe seu nome completo." if len(full_name.strip()) < 2 else None,
        "display": "Informe como quer ser chamado." if len(display_name.strip()) < 2 else None,
        "email": _email_message(email),
        "phone": _phone_message(phone) if phone.strip() else None,
        "password": _password_message(new_password) if new_password else None,
        "confirmation": "As senhas não coincidem." if new_password != confirmation else None,
        "photo": photo_error,
    }
    for message, slot in ((errors["full"], full_error), (errors["display"], display_error),
                          (errors["email"], email_error), (errors["phone"], phone_error),
                          (errors["password"], password_error),
                          (errors["confirmation"], confirmation_error),
                          (errors["photo"], photo_slot)):
        _show_error(slot, message)
    if any(errors.values()):
        return
    if not store.update_profile(user_id, full_name, display_name, email, phone,
                                avatar=photo, password=new_password or None):
        _show_error(email_error, "Este e-mail já está em uso.")
        return
    _set_authenticated(store.get_user(user_id))
    st.success("Perfil atualizado.")


def render_sidebar_account():
    user_id = st.session_state.get("auth_user_id")
    user = store.get_user(user_id) if user_id else None
    if not user:
        return
    st.divider()
    if user.get("avatar"):
        st.image(user["avatar"], width=48)
    st.caption(f"{user['display_name']} · {user['email']}")
    if st.button("Sair", key="auth_logout", use_container_width=True):
        _logout()
        try:
            if st.user.is_logged_in:
                st.logout()
        except (AttributeError, KeyError):
            pass
        st.rerun()
    if user["role"] != "admin":
        return
    pending = store.pending_users()
    with st.expander(f"Aprovar acessos ({len(pending)})", expanded=False):
        if not pending:
            st.caption("Nenhuma solicitação pendente.")
        for applicant in pending:
            st.write(applicant["display_name"])
            st.caption(f"{applicant['full_name']} · {applicant['email']} · {applicant['phone']}")
            if applicant.get("avatar"):
                st.image(applicant["avatar"], width=64)
            approve_col, reject_col = st.columns(2)
            with approve_col:
                if st.button("Aprovar", key=f"approve_user_{applicant['id']}"):
                    store.set_user_active(applicant["id"], True)
                    st.rerun()
            with reject_col:
                if st.button("Recusar", key=f"reject_user_{applicant['id']}"):
                    store.delete_pending_user(applicant["id"])
                    st.rerun()
