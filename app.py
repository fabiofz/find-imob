"""Painel local para acompanhar e executar os coletores de imóveis."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st


ROOT = Path(__file__).resolve().parent
HISTORY_FILE = ROOT / ".execucoes.json"
LOCAL_TZ = ZoneInfo("America/Sao_Paulo")

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
]
MESES_PT = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)

st.set_page_config(
    page_title="Find Imob | Central de coleta",
    page_icon="⌂",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
      :root { --bg:#0a0d12; --panel:#111720; --line:#202a36; --muted:#8b98a9; --text:#edf2f7; --orange:#f08b3e; --red:#ef5252; }
      html, body, [data-testid="stAppViewContainer"] { background:var(--bg); color:var(--text); font-family:'DM Sans',sans-serif; }
      [data-testid="stHeader"] { background:transparent; }
      [data-testid="stSidebar"] { background:#0e131a; border-right:1px solid var(--line); }
      .block-container { padding-top:2rem; padding-bottom:3rem; max-width:1500px; }
      h1,h2,h3,p,span,label { font-family:'DM Sans',sans-serif; }
      h1 { letter-spacing:-.04em; }
      .eyebrow { text-transform:uppercase; letter-spacing:.16em; color:var(--orange); font-size:.72rem; font-weight:700; }
      .subtle { color:var(--muted); }
      .metric-card { background:linear-gradient(145deg,#141c27,#10151d); border:1px solid var(--line); border-radius:16px; padding:18px 20px; min-height:100px; }
      .metric-label { color:var(--muted); font-size:.82rem; }
      .metric-value { color:var(--text); font-size:1.7rem; font-weight:700; margin-top:5px; }
      .agency-card { background:#111720; border:1px solid #202a36; border-radius:15px; padding:16px 17px 11px; min-height:124px; margin-bottom:8px; }
      .agency-name { font-weight:700; font-size:.98rem; min-height:25px; }
      .agency-type { color:#8290a1; font-size:.75rem; margin-top:2px; }
      .terminal { background:#070a0e; border:1px solid #25313d; border-radius:14px; padding:14px 16px; }
      .terminal-head { color:#97a7b8; font:700 .75rem 'Space Mono',monospace; border-bottom:1px solid #1a2430; padding-bottom:10px; margin-bottom:10px; }
      .terminal-body { color:#c2f4d0; font: .78rem/1.6 'Space Mono',monospace; white-space:pre-wrap; overflow-wrap:anywhere; max-height:360px; overflow-y:auto; }
      .month-label { color:var(--orange); font-weight:700; letter-spacing:.04em; border-bottom:1px solid var(--line); padding:12px 0 7px; }
      div[data-testid="stButton"] button { background:var(--orange); color:#22150b; border:0; border-radius:10px; font-weight:700; transition:all .15s ease; }
      div.st-key-run_all button { background:var(--red); color:white; min-height:48px; }
      div.st-key-run_all button:hover { background:#d94343; color:white; border:0; }
      div[data-testid="stButton"] button:hover { transform:translateY(-1px); }
      div[data-testid="stTextInput"] input { background:#111720; border-color:#273342; }
      [data-testid="stExpander"] { border:1px solid var(--line); border-radius:12px; }
    </style>
    """,
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


def listar_anuncios():
    caminho = ROOT / "geral.json"
    if not caminho.exists():
        return []
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return dados if isinstance(dados, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def executar(rotulo, tipo, identificador):
    if st.session_state.get("coletando", False):
        st.warning("Já existe uma coleta em andamento nesta sessão.")
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
    log = []
    terminal = st.empty()
    status = st.status(f"Executando: {rotulo}", expanded=True)
    terminal.markdown(
        '<div class="terminal"><div class="terminal-head">● LIVE OUTPUT &nbsp; · &nbsp; '
        + rotulo
        + '</div><div class="terminal-body">Preparando processo...</div></div>',
        unsafe_allow_html=True,
    )

    ambiente = os.environ.copy()
    ambiente["PYTHONUNBUFFERED"] = "1"
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
            log.append(linha.rstrip())
            corpo = "\n".join(log[-400:]) or "Aguardando saída..."
            terminal.markdown(
                '<div class="terminal"><div class="terminal-head">● LIVE OUTPUT &nbsp; · &nbsp; '
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
    status.update(
        label=(f"Concluído em {duracao}s" if codigo == 0 else f"Finalizado com erro ({codigo})"),
        state=("complete" if codigo == 0 else "error"),
        expanded=(codigo != 0),
    )
    historico = ler_historico()
    historico.append(
        {
            "inicio": instante.isoformat(),
            "rotulo": rotulo,
            "resultado": resultado,
            "codigo": codigo,
            "duracao": duracao,
            "log": log[-80:],
        }
    )
    salvar_historico(historico)
    st.session_state.ultimo_resultado = resultado
    st.rerun()


historico = ler_historico()
anuncios = listar_anuncios()
ultima_execucao = historico[-1]["inicio"] if historico else None

with st.sidebar:
    st.markdown("### ⌂ Find Imob")
    st.caption("PAINEL DE OPERAÇÕES")
    st.divider()
    st.markdown("**Coleta**")
    st.caption(f"{len(AGENCIES)} imobiliárias conectadas")
    st.caption("Execuções agrupadas por mês")
    st.divider()
    st.markdown("**Armazenamento**")
    st.caption("Catálogo: geral.json")
    st.caption("Planilha: pasta configurada do projeto")

st.markdown('<div class="eyebrow">Find Imob &nbsp; / &nbsp; Operações</div>', unsafe_allow_html=True)
st.title("Central de coleta")
st.markdown('<p class="subtle">Acompanhe os portais, execute coletas e consulte o histórico mensal.</p>', unsafe_allow_html=True)

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
    executar("Todas as imobiliárias", "all", None)

st.write("")
aba_coleta, aba_historico = st.tabs(["Imobiliárias", "Histórico mensal"])
with aba_coleta:
    busca = st.text_input("Buscar imobiliária", placeholder="Digite o nome do portal…", label_visibility="collapsed")
    agencias_visiveis = [item for item in AGENCIES if busca.casefold() in item[0].casefold()]
    st.markdown(f'<p class="subtle">{len(agencias_visiveis)} portal(is) disponíveis</p>', unsafe_allow_html=True)
    for inicio_grade in range(0, len(agencias_visiveis), 3):
        grade = st.columns(3, gap="medium")
        for coluna, agencia in zip(grade, agencias_visiveis[inicio_grade:inicio_grade + 3]):
            nome, tipo, identificador = agencia
            with coluna:
                st.markdown(
                    f'<div class="agency-card"><div class="agency-name">{nome}</div>'
                    f'<div class="agency-type">Coletor pronto · aluguel</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Executar imobiliária",
                    key=f"run_agency_{identificador}",
                    use_container_width=True,
                ):
                    executar(nome, tipo, identificador)

with aba_historico:
    if not historico:
        st.info("As execuções aparecerão aqui, agrupadas por mês.")
    else:
        agrupado = {}
        for item in reversed(historico):
            momento = datetime.fromisoformat(item["inicio"]).astimezone(LOCAL_TZ)
            chave_mes = momento.strftime("%Y-%m")
            rotulo_mes = f"{MESES_PT[momento.month - 1].capitalize()} {momento.year}"
            agrupado.setdefault((chave_mes, rotulo_mes), []).append((momento, item))
        for (_, rotulo_mes), itens in sorted(agrupado.items(), reverse=True):
            st.markdown(f'<div class="month-label">{rotulo_mes}</div>', unsafe_allow_html=True)
            for momento, item in itens:
                icone = "✅" if item["resultado"] == "sucesso" else "⚠️"
                with st.expander(f"{icone}  {momento.strftime('%d %b · %H:%M')}  —  {item['rotulo']}  ·  {item['duracao']}s"):
                    st.code("\n".join(item.get("log", [])) or "Sem saída registrada.", language="text")
