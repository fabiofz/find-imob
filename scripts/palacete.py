        if len(spans) >= 2 and "aluguel" in texto_do(spans[0]).lower():
            valor = limpar_preco(texto_do(spans[1]))
            if valor:
                return valor

    # Alternativa: localizar textos que indiquem o valor do aluguel.
    for elemento in card.find_all(["span", "div", "p"]):
        conteudo = texto_do(elemento) or ""
        if re.search(r"aluguel", conteudo, re.IGNORECASE):
            match = re.search(
                r"R\$\s*[\d.]+(?:,\d{2})?",
                conteudo,
                re.IGNORECASE,
            )
            if match:
                valor = limpar_preco(match.group(0))
                if valor:
                    return valor
    return None


def extrair_titulo(card):
    # Mantém a preferência original pelo alt da imagem.
    img = card.find("img", alt=True)
    titulo = (img.get("alt") or "").strip() if img else ""
    if titulo:
        return titulo

    for seletor in (
        "[class*='colorOfTitleCondominium']",
        "[class*='Title']",
        "h2",
        "h3",
    ):
        elemento = card.select_one(seletor)
        titulo = texto_do(elemento)
        if titulo:
            return titulo
    return None


def executar():
    json_data = pegar_json(GERAL_JSON)
    ids = set(json_data.get("ids", []))
    dados = json_data.get("dados", [])
    if not isinstance(dados, list):
        raise ValueError("O campo 'dados' do JSON precisa ser uma lista.")

    try:
        resposta = requests.get(URL, headers=HEADERS, timeout=30)
        resposta.raise_for_status()
    except requests.RequestException as erro:
        raise RuntimeError(f"Falha ao acessar o site da Palacete: {erro}") from erro

    soup = BeautifulSoup(resposta.text, "html.parser")
    cards = encontrar_cards(soup)

    if not cards:
        titulo_pagina = texto_do(soup.title) or "(sem título)"
        trecho = soup.get_text(" ", strip=True)[:400]
        raise RuntimeError(
            "Nenhum card de imóvel foi encontrado no HTML recebido. "
            f"Título da página: {titulo_pagina}. Conteúdo inicial: {trecho}"
        )

    imoveis = []
    pg = 1

    for card in cards:
        tag_link = card.find("a", href=True)
        link = urljoin(URL, tag_link["href"]) if tag_link else None
        titulo = extrair_titulo(card)
        preco = extrair_preco(card)

        # Não concatena valores ausentes: isso causava TypeError.
        if not titulo or not link or not preco:
            continue

        chave = f"{titulo}|{preco}|{link}"
        _id = hashlib.md5(chave.encode("utf-8")).hexdigest()

        if _id in ids:
            continue

        imov = {
            "id": _id,
            "titulo": titulo,
            "preco": preco,
            "link": link,
            "pagina": pg,
        }
        imoveis.append(imov)
        dados.append(imov)
        ids.add(_id)

    # Se nenhum anúncio foi extraído, não altera o JSON nem gera planilha vazia.
    if not imoveis:
        print(
            f"Palacete: {len(cards)} cards encontrados, mas nenhum anúncio novo "
            "com título, preço de aluguel e link válidos."
        )
        return

    with open(GERAL_JSON, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)

    dados_sem_id = [
        {chave: valor for chave, valor in item.items() if chave != "id"}
        for item in imoveis
    ]
    gerar_excel(dados_sem_id, f"{PATH_GD}{EXCEL_FINAL}")
    print(f"Palacete: {len(imoveis)} novo(s) imóvel(is) adicionado(s).")


if __name__ == "__main__":
    executar()
