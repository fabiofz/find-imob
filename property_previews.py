"""Property keys and preview metadata without any Streamlit dependency."""
from datetime import datetime
import re
from urllib.parse import urlparse, urljoin
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
LOCAL_TZ = ZoneInfo("America/Sao_Paulo")

def chave_anuncio(anuncio):
    link = str(anuncio.get("link") or "").strip()
    if link:
        try:
            parsed = urlparse(link)
            if parsed.hostname:
                return parsed._replace(
                    netloc=parsed.hostname.lower(),
                    path=parsed.path.rstrip("/"),
                    query="",
                    fragment="",
                ).geturl()
        except (TypeError, ValueError):
            pass
        return link.casefold()
    return str(anuncio.get("id") or "")

def validar_imagem_preview(url, referer=None):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False
        with requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; FindImobPreview/1.0)", "Referer": referer or ""},
            timeout=(2, 3),
            allow_redirects=True,
            stream=True,
        ) as resposta:
            resposta.raise_for_status()
            tipo = resposta.headers.get("Content-Type", "").split(";", 1)[0].lower()
            cabecalho = next(resposta.iter_content(1024), b"")
            assinaturas = (
                cabecalho.startswith(b"\xff\xd8\xff"),
                cabecalho.startswith(b"\x89PNG\r\n\x1a\n"),
                cabecalho.startswith((b"GIF87a", b"GIF89a")),
                cabecalho.startswith(b"BM"),
                cabecalho.startswith((b"II*\x00", b"MM\x00*")),
                cabecalho.startswith(b"RIFF") and cabecalho[8:12] == b"WEBP",
                b"ftypavif" in cabecalho or b"ftypavis" in cabecalho,
            )
            svg_valido = tipo == "image/svg+xml" and b"<svg" in cabecalho.lower()
            return any(assinaturas) or svg_valido
    except (requests.RequestException, ValueError, TypeError):
        return False

def buscar_metadados_preview(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return {}
        resposta = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; FindImobPreview/1.0)"},
            timeout=(3, 6),
            allow_redirects=True,
        )
        resposta.raise_for_status()
        soup = BeautifulSoup(resposta.text, "html.parser")

        def meta(*chaves):
            for chave in chaves:
                tag = soup.find("meta", attrs={"property": chave}) or soup.find(
                    "meta", attrs={"name": chave}
                )
                conteudo = tag.get("content", "").strip() if tag else ""
                if conteudo:
                    return conteudo
            return ""

        titulo = meta("og:title", "twitter:title")
        descricao = meta("og:description", "description", "twitter:description")
        imagem = meta("og:image", "twitter:image")
        termos_excluir_imagem = ("logo", "icon", "avatar", "placeholder", "banner")
        if imagem and any(termo in imagem.lower() for termo in termos_excluir_imagem):
            imagem = ""
        candidatas = []
        if imagem:
            candidatas.append((10, imagem))
        for img in soup.find_all("img"):
            src = next((img.get(atributo, "") for atributo in (
                    "src", "data-src", "data-lazy-src", "data-original"
            ) if img.get(atributo)), "")
            srcset = img.get("srcset", "")
            if not src and srcset:
                src = srcset.split(",", 1)[0].strip().split(" ", 1)[0]
            alt = " ".join((img.get("alt", ""), img.get("title", ""))).lower()
            if not src or any(termo in (src + alt).lower() for termo in termos_excluir_imagem):
                continue
            try:
                largura = int(img.get("width", 0))
                altura = int(img.get("height", 0))
            except (TypeError, ValueError):
                largura = altura = 0
            if (largura and largura < 120) or (altura and altura < 90):
                continue
            pontuacao = (2 if largura >= 300 or altura >= 220 else 0) + (
                1 if any(termo in alt for termo in ("imóvel", "imovel", "casa", "fachada", "sala")) else 0
            )
            candidatas.append((pontuacao, src))
        # Muitos portais montam galerias com divs estilizadas em vez de
        # elementos <img>; nesse caso a URL fica no atributo style.
        for elemento in soup.select("[style]"):
            estilo = elemento.get("style", "")
            fundos = re.findall(
                r"background(?:-image)?\s*:\s*url\([\"']?([^\"')]+)",
                estilo,
                flags=re.IGNORECASE,
            )
            for src in fundos:
                if any(termo in src.lower() for termo in termos_excluir_imagem):
                    continue
                pontuacao = 4 if "/imoveis/" in src.lower() else 1
                if "sf-item" in elemento.get("class", []):
                    pontuacao += 2
                candidatas.append((pontuacao, src))
        # Alguns sites guardam as fotos em atributos de dados ou em JSON
        # inline, sem inserir <img> nem style no HTML inicial.
        for elemento in soup.find_all(True):
            for atributo in ("data-bg", "data-background", "data-image", "data-src", "data-original"):
                src = elemento.get(atributo, "")
                if src and re.search(r"\.(?:jpe?g|png|webp|gif|avif)(?:[?#]|$)", src, re.I):
                    if not any(termo in src.lower() for termo in termos_excluir_imagem):
                        candidatas.append((3, src))
        for src in re.findall(
            r"(?:https?:)?//[^\"'\s<>]+?\.(?:jpe?g|png|webp|gif|avif)(?:\?[^\"'\s<>]*)?|/[^\"'\s<>]+?\.(?:jpe?g|png|webp|gif|avif)(?:\?[^\"'\s<>]*)?",
            resposta.text,
            flags=re.IGNORECASE,
        ):
            if not any(termo in src.lower() for termo in termos_excluir_imagem):
                candidatas.append((2 + (3 if "/imoveis/" in src.lower() else 0), src))
        imagem_url = ""
        imagem_validada = False
        vistos = set()
        for tentativa, (_, candidata) in enumerate(
            sorted(candidatas, key=lambda item: item[0], reverse=True)
        ):
            if tentativa >= 4:
                break
            candidata_url = urljoin(resposta.url, candidata)
            if candidata_url in vistos:
                continue
            vistos.add(candidata_url)
            if validar_imagem_preview(candidata_url, resposta.url):
                imagem_url = candidata_url
                imagem_validada = True
                break
        return {
            "titulo": titulo,
            "descricao": descricao,
            "imagem": imagem_url if imagem_validada else "",
            "imagem_validada": imagem_validada,
            "consultado": datetime.now(LOCAL_TZ).isoformat(),
        }
    except (requests.RequestException, ValueError, TypeError):
        return {"consultado": datetime.now(LOCAL_TZ).isoformat()}
