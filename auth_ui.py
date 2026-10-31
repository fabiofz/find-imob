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
        "line": "#d2e2d7", "text": "#17241b", "muted": "#52645a",
    },
    "Azul escuro e verde": {
        "icon": "🌌", "key": "azul_verde", "bg": "#0c1727", "panel": "#12233a",
        "line": "#29415d", "text": "#f1f6fc", "muted": "#b2c3d7",
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
          --text:{theme['text']}; --muted:{theme['muted']}; --green:#32cb79;
          --green-hover:#51d891;
        }}
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
          background:var(--bg) !important; color:var(--text) !important;
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
          box-sizing:border-box; width:40vw; max-width:700px; min-width:0;
          margin:4vh auto !important; padding:clamp(22px,3.5vw,44px);
          color:var(--text); background:var(--panel);
          border:1px solid var(--line); border-radius:22px;
          box-shadow:0 20px 70px #0002;
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
        .st-key-auth_shell input, .st-key-auth_shell [data-baseweb="select"] > div {{
          background:color-mix(in srgb,var(--bg) 75%,var(--panel)) !important;
          color:var(--text) !important; border-color:var(--line) !important;
        }}
        .st-key-auth_shell label, .st-key-auth_shell p,
        .st-key-auth_shell [data-testid="stMarkdownContainer"] {{
          color:var(--text);
        }}
        .st-key-auth_shell [data-testid="stButton"] button {{
          border-radius:11px !important;
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
        .st-key-auth_photo_crop [data-testid="stHorizontalBlock"] {{
          align-items:center; gap:1rem;
        }}
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
            cols = st.columns(4, gap="small")
            selected = _current_theme()
            for col, (theme, data) in zip(cols[:3], THEMES.items()):
                with col:
                    st.button(data["icon"], key=f"auth_theme_{data['key']}",
                              help=f"Usar o esquema {theme}",
                              type="primary" if theme == selected else "secondary",
                              on_click=_select_auth_theme, args=(theme,))
            with cols[3]:
                if st.button("×", key="auth_theme_close", help="Ocultar esquemas de cores"):
                    st.session_state.auth_theme_open = False
                    st.rerun()
        else:
            if st.button("🎨", key="auth_theme_open", help="Mostrar esquemas de cores"):
                st.session_state.auth_theme_open = True
                st.rerun()


def _crop_uploaded_photo(upload, widget_prefix):
    state_key = f"{widget_prefix}_cropped_photo"
    if upload is None:
        st.session_state.pop(state_key, None)
        return None, None
    data = upload.getvalue()
    if not data or len(data) > MAX_AVATAR_BYTES:
        st.session_state.pop(state_key, None)
        return None, "A foto precisa ter até 2 MB."
    try:
        Image.MAX_IMAGE_PIXELS = 16_000_000
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Use uma imagem JPEG, PNG ou WebP.")
                image = ImageOps.exif_transpose(source)
                if image.width * image.height > 16_000_000:
                    raise ValueError("A imagem excede a resolução permitida.")
                image.load()
                image = image.convert("RGB")
        width, height = image.size
        if not width or not height:
            raise ValueError("A imagem não tem dimensões válidas.")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        st.session_state.pop(state_key, None)
        return None, "Não foi possível abrir essa imagem."
    except ValueError as error:
        st.session_state.pop(state_key, None)
        return None, str(error)

    with st.container(key="auth_photo_crop"):
        st.caption("Ajuste o recorte quadrado da foto (saída 150 × 150 px).")
        zoom = st.slider(
            "Zoom", min_value=1.0, max_value=3.0, value=1.0, step=0.1,
            key=f"{widget_prefix}_crop_zoom",
        )
        horizontal, vertical = st.columns(2)
        with horizontal:
            x_position = st.slider(
                "Enquadramento horizontal", 0, 100, 50, 1,
                key=f"{widget_prefix}_crop_x",
            )
        with vertical:
            y_position = st.slider(
                "Enquadramento vertical", 0, 100, 50, 1,
                key=f"{widget_prefix}_crop_y",
            )

        side = max(1, int(min(width, height) / zoom))
        left = int((width - side) * x_position / 100)
        top = int((height - side) * y_position / 100)
        preview = image.crop((left, top, left + side, top + side))
        output = preview.resize((150, 150), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        output.save(buffer, format="JPEG", quality=90, optimize=True)
        cropped = buffer.getvalue()
        st.session_state[state_key] = cropped
        st.image(cropped, width=150, caption="Prévia final: 150 × 150 px")
    return cropped, None


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
        slot.error(message)


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
    identifier = st.text_input("Usuário ou e-mail", key="auth_login_identifier")
    identifier_error = st.empty()
    password = st.text_input("Senha", type="password", key="auth_login_password")
    password_error = st.empty()
    if st.button("Entrar", key="auth_login_submit", type="primary",
                 use_container_width=True):
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
        if not identifier.strip():
            _show_error(identifier_error, "Informe seu usuário ou e-mail.")

    st.divider()
    if st.button("🌐  Continuar com Google", key="auth_google_login", use_container_width=True):
        try:
            config = st.secrets.get("auth", {})
            required = ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url")
            if not all(config.get(key) for key in required):
                st.warning("Login Google ainda não configurado. Configure as credenciais OIDC em .streamlit/secrets.toml.")
            else:
                st.login()
        except Exception:
            st.error("Não foi possível iniciar o login Google. Confira a configuração OIDC em .streamlit/secrets.toml e reinicie o app.")


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
    password = st.text_input("Nova senha", type="password", key="initial_password")
    password_error = st.empty()
    confirmation = st.text_input(
        "Confirme a nova senha", type="password", key="initial_password_confirm"
    )
    confirmation_error = st.empty()
    if not st.button("Salvar e entrar", type="primary", key="initial_profile_submit"):
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
    password = st.text_input("Senha", type="password", key="signup_password")
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
    with st.container(key="auth_shell"):
        _render_auth_brand()
        st.caption("Entre para acessar o painel ou solicite a criação da sua conta.")
        if timed_out:
            st.warning("Sua sessão expirou. Entre novamente.")
        if st.session_state.pop("auth_google_pending", False):
            st.info("Conta Google registrada. O acesso aguarda aprovação do administrador.")
        if st.session_state.pop("auth_google_error", None):
            st.error("Use uma conta Google com e-mail verificado.")
        auth_route = st.session_state.get("_auth_route_mode") or "login"
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
