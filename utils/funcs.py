import os
from openpyxl import Workbook, load_workbook
import json

def gerar_excel(dados, caminho_saida):
    if not dados:
        print("Nada para exportar")
        return

    if os.path.exists(caminho_saida):
        wb = load_workbook(caminho_saida)
        ws = wb.active
        print("Arquivo existente encontrado, adicionando dados...")
        
        headers = [cell.value for cell in ws[1]]
    else:
        # os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)

        wb = Workbook()
        ws = wb.active
        ws.title = "Imoveis"
        print("Arquivo não existe, criando novo...")

        headers = list(dados[0].keys())
        ws.append(headers)

    for item in dados:
        ws.append([item.get(h, "") for h in headers])

    wb.save(caminho_saida)
    print(f"Excel atualizado com sucesso: {caminho_saida}")

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

    ids = {item["id"] for item in dados}
    return {"ids": ids, "dados": dados}

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