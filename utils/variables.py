from datetime import datetime
import os
import re
import unicodedata

data_hoje = datetime.now().strftime("%Y-%m-%d-%H")

def _lista_env(nome, padrao):
    texto = os.environ.get(nome)
    return [parte.strip().lower() for parte in texto.split(",") if parte.strip()] if texto else list(padrao)


PRECO_MIN = float(os.environ.get("FINDIMOB_PRECO_MIN", "1500"))
PRECO_MAX = float(os.environ.get("FINDIMOB_PRECO_MAX", "4500"))
TIPOS_BUSCA = _lista_env(
    "FINDIMOB_TIPOS",
    ("apartamento", "casa", "casa-em-condominio", "casa-terrea", "sobrado", "duplex"),
)
CIDADES_BUSCA = _lista_env(
    "FINDIMOB_CIDADES", ("pindamonhangaba", "tremembe", "taubate")
)
IMOVEIS_ACEITOS = TIPOS_BUSCA
GERAL_JSON = "geral.json"
_diretorio_exportacao = os.environ.get("IMOVEIS_OUTPUT_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports"
)
PATH_GD = os.path.join(
    _diretorio_exportacao, ""
)
EXCEL_FINAL = f"imoveis_{data_hoje}.xlsx"


_TIPO_ALIASES = {
    "apartamento": ("apartamento", "apto"),
    "casa": ("casa",),
    "casa-em-condominio": ("casa em condominio", "casa de condominio", "casa condominio"),
    "casa-terrea": ("casa terrea",),
    "sobrado": ("sobrado",),
    "duplex": ("duplex",),
    "kitnet": ("kitnet", "quitinete", "studio", "loft"),
    "comercial": ("comercial", "sala", "ponto comercial"),
    "terreno": ("terreno", "lote"),
    "chacara": ("chacara", "sitio"),
    "galpao": ("galpao",),
}


def normalizar_filtro(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    return " ".join(re.sub(r"[^a-zA-Z0-9]+", " ", texto).casefold().split())


def cidade_selecionada(cidade):
    slug = normalizar_filtro(cidade).replace(" ", "")
    return slug in {normalizar_filtro(item).replace(" ", "") for item in CIDADES_BUSCA}


def imovel_atende_filtros(titulo, preco, link="", cidade=None):
    texto = normalizar_filtro(f"{titulo} {link}")
    # Este painel deve exibir apenas imóveis residenciais. A verificação
    # central vale para os coletores antigos e para o coletor genérico.
    termos_comerciais = (
        "comercial", "comerciais", "ponto comercial", "sala comercial",
        "conjunto comercial", "predio comercial", "galpao", "loja",
        "escritorio", "consultorio",
    )
    if any(termo in texto for termo in termos_comerciais):
        return False
    if TIPOS_BUSCA:
        tipo_encontrado = any(
            alias in texto
            for tipo in TIPOS_BUSCA
            for alias in _TIPO_ALIASES.get(tipo, (normalizar_filtro(tipo),))
        )
        if not tipo_encontrado:
            return False
    if cidade is not None and not cidade_selecionada(cidade):
        return False
    if preco is None:
        return False
    texto_preco = re.sub(r"[^\d,.-]", "", str(preco))
    if "," in texto_preco:
        texto_preco = texto_preco.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", texto_preco):
        texto_preco = texto_preco.replace(".", "")
    try:
        valor = float(texto_preco)
    except ValueError:
        return False
    if not PRECO_MIN <= valor <= PRECO_MAX:
        return False
    return True
