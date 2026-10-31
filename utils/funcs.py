import json
import os
import tempfile
from pathlib import Path


class RegistrosUnicos(list):
    """Lista que mantém o conjunto de IDs sincronizado quando um coletor insere."""

    def __init__(self, registros=(), ids=None):
        super().__init__(registros)
        self.ids = ids if ids is not None else set()
        self.record_ids = {
            registro.get("id")
            for registro in self
            if isinstance(registro, dict) and registro.get("id")
        }
        self.record_links = {
            registro.get("link")
            for registro in self
            if isinstance(registro, dict) and registro.get("link")
        }

    def append(self, registro):
        identificador = registro.get("id") if isinstance(registro, dict) else None
        link = registro.get("link") if isinstance(registro, dict) else None
        if (identificador and identificador in self.record_ids) or (
            link and link in self.record_links
        ):
            return
        super().append(registro)
        if identificador:
            self.ids.add(identificador)
            self.record_ids.add(identificador)
        if link:
            self.record_links.add(link)

def salvar_json(dados, caminho):
    """Grava o estado da coleta atomicamente para evitar JSON truncado."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    arquivo_temporario = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=caminho.parent,
            delete=False, suffix=".tmp"
        ) as arquivo:
            arquivo_temporario = Path(arquivo.name)
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(arquivo_temporario, caminho)
    finally:
        if arquivo_temporario and arquivo_temporario.exists():
            arquivo_temporario.unlink()

def preco_para_float(preco_str):
    if not preco_str:
        return None
    preco_str = preco_str.replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(preco_str)
    except:
        return None

def pegar_json(geral):
    if not os.path.exists(geral) or os.stat(geral).st_size == 0:
        dados = []
    else:
        with open(geral, "r", encoding="utf-8") as f:
            dados = json.load(f)

    if not isinstance(dados, list):
        raise ValueError(f"O arquivo {geral} precisa conter uma lista JSON.")
    if any(not isinstance(item, dict) or not item.get("id") for item in dados):
        raise ValueError(f"O arquivo {geral} contém anúncio inválido ou sem ID.")

    ids = {item["id"] for item in dados}
    registros = RegistrosUnicos(dados, ids)
    return {"ids": ids, "dados": registros}

def limpar_preco(texto):
    if not texto:
        return None
    return (
        texto
        .replace("\xa0", " ")
        .replace("/mês", "")
        .replace("/mes", "")
        .replace("/total", "")
        .replace("/ mês", "")
        .replace("A ", "")
        .replace(" L", "")
        .replace("R$ R$ ", "R$ ")
        .strip()
    )

def br_to_float(v):
    return float(v.replace('.', '').replace(',', '.'))
