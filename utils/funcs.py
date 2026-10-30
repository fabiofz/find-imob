import json
import os
import tempfile
from pathlib import Path

from openpyxl import Workbook, load_workbook


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

def gerar_excel(dados, caminho_saida):
    if not dados:
        print("Nada para exportar")
        return

    caminho_configurado = Path(caminho_saida)
    caminho_saida = caminho_configurado
    caminho_local = Path(__file__).resolve().parents[1] / "exports" / caminho_configurado.name
    try:
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    except OSError as erro_destino:
        caminho_saida = caminho_local
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        print(
            f"Aviso: destino indisponível ({erro_destino}); "
            f"usando exportação local: {caminho_saida}"
        )

    if caminho_saida.exists():
        try:
            wb = load_workbook(caminho_saida)
        except OSError as erro_destino:
            caminho_saida = caminho_local
            caminho_saida.parent.mkdir(parents=True, exist_ok=True)
            print(
                f"Aviso: não foi possível abrir o Excel no destino configurado "
                f"({erro_destino}); usando: {caminho_saida}"
            )
            wb = load_workbook(caminho_saida) if caminho_saida.exists() else Workbook()
            if not caminho_saida.exists():
                ws = wb.active
                ws.title = "Imoveis"
                headers = list(dados[0].keys())
                ws.append(headers)
            else:
                ws = wb.active
                headers = [cell.value for cell in ws[1]]
        else:
            ws = wb.active
            print("Arquivo existente encontrado, adicionando dados...")
            headers = [cell.value for cell in ws[1]]
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Imoveis"
        print("Arquivo não existe, criando novo...")

        headers = list(dados[0].keys())
        ws.append(headers)

    # Cada scraper exporta os anúncios novos encontrados até aquele ponto.
    # Como o runner executa vários scrapers no mesmo arquivo/hora, ignora
    # novamente os links que já foram escritos na planilha.
    link_coluna = headers.index("link") + 1 if "link" in headers else None
    links_existentes = set()
    if link_coluna:
        links_existentes = {
            ws.cell(row=linha, column=link_coluna).value
            for linha in range(2, ws.max_row + 1)
            if ws.cell(row=linha, column=link_coluna).value
        }

    adicionados = 0
    for item in dados:
        link = item.get("link")
        if link_coluna and link and link in links_existentes:
            continue
        ws.append([item.get(h, "") for h in headers])
        if link_coluna and link:
            links_existentes.add(link)
        adicionados += 1

    if not adicionados:
        print("Nenhum anúncio novo para adicionar ao Excel")
        return

    try:
        wb.save(caminho_saida)
    except OSError as erro_destino:
        if caminho_saida == caminho_local:
            raise
        caminho_local.parent.mkdir(parents=True, exist_ok=True)
        wb.save(caminho_local)
        caminho_saida = caminho_local
        print(
            f"Aviso: falha ao salvar no destino configurado ({erro_destino}); "
            f"arquivo salvo localmente: {caminho_saida}"
        )
    print(f"Excel atualizado com sucesso: {caminho_saida}")


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
