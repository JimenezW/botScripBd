"""
Módulo Extractor de Capas de Contenido y Compositor de Páginas en Alta Resolución.
Reconstruye las páginas de Scribd con precisión 1:1 integrando capas de imágenes (.image_layer),
hojas de sprites con recortes CSS (clip: rect) y capa de texto tipográfico (.text_layer con escala 0.2).
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Page, Request
from pydantic import BaseModel, Field


SCRIBD_OFFICIAL_CSS = """
body {
    margin: 0;
    padding: 0;
    background: #fff;
    display: flex;
    justify-content: center;
    align-items: flex-start;
}
.newpage {
    white-space: nowrap;
    position: relative;
    top: 0;
    left: 0;
    text-rendering: auto;
    color: #000;
    background-color: #fff;
    overflow: hidden;
    box-sizing: border-box;
}
.image_layer {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1;
}
.image_layer .absimg {
    position: absolute;
    pointer-events: none;
    border: none;
    left: 0;
    -webkit-user-drag: none;
}
.image_layer .absimg::selection {
    background-color: transparent;
}
.link_layer, .text_layer {
    width: 0;
    height: 0;
    position: absolute;
    top: 0;
    left: 0;
    z-index: 2;
}
.text_layer {
    transform: scale(.2);
    transform-origin: top left;
}
.text_layer div, .text_layer span {
    white-space: nowrap;
    padding: 0;
    margin: 0;
    border: none;
    line-height: 1;
}
.text_layer span {
    height: 1px;
}
.text_layer span.a, .text_layer span.g {
    position: absolute;
    border: none;
    left: 0;
}
.text_layer span.w {
    white-space: nowrap;
    padding: 0;
    margin: 0;
    border: none;
    height: 1px;
    line-height: 1;
    display: inline-block;
}
.text_layer a.ll {
    position: absolute;
    display: block;
    color: inherit;
    text-decoration: none;
}
.text_layer span.l {
    display: inline;
    margin: 0;
}
.text_layer span.l, .text_layer span.l1 { white-space: nowrap; padding: 0; border: none; height: 1px; line-height: 1; display: inline; }
.text_layer span.l1 { margin: 0 0 0 -1px; }
.text_layer span.l2 { margin: 0 0 0 -2px; }
.text_layer span.l3 { margin: 0 0 0 -3px; }
.text_layer span.l4 { margin: 0 0 0 -4px; }
.text_layer span.l5 { margin: 0 0 0 -5px; }
.text_layer span.l6 { margin: 0 0 0 -6px; }
.text_layer span.l7 { margin: 0 0 0 -7px; }
.text_layer span.l8 { margin: 0 0 0 -8px; }
.text_layer span.l9 { margin: 0 0 0 -9px; }
.text_layer span.l10 { margin: 0 0 0 -10px; }
.text_layer span.l11 { margin: 0 0 0 -11px; }
.text_layer span.l12 { margin: 0 0 0 -12px; }

/* Tipografía Scribd estándar */
div.ff0 span { font-family: Arial, Helvetica, sans-serif; font-weight: normal; font-style: normal; }
div.ff1 span { font-family: Georgia, serif; font-weight: normal; font-style: italic; }
div.ff2 span { font-family: Arial, Helvetica, sans-serif; font-weight: bold; }
div.ff3 span { font-family: Arial, Helvetica, sans-serif; font-weight: normal; }
div.ff4 span { font-family: Arial, Helvetica, sans-serif; font-weight: bold; }
div.ff5 span { font-family: Arial, Helvetica, sans-serif; }
div.ff6 span { font-family: Arial, Helvetica, sans-serif; }
div.ff7 span { font-family: Arial, Helvetica, sans-serif; font-weight: normal; }
.ff0, .ff1, .ff2, .ff3, .ff4, .ff5, .ff6, .ff7 { display: unset; }
"""


class ExtractedPage(BaseModel):
    """Representación estructurada de una página extraída e integrada."""
    page_number: int
    text_content: str = ""
    lines: List[str] = Field(default_factory=list)
    image_path: str = ""
    local_image_paths: List[str] = Field(default_factory=list)
    is_blurred: bool = False


class DocumentExtractor:
    """Gestiona la intercepción de red, parseo de capas y renderizado 1:1 de páginas en alta resolución."""

    def __init__(self, page: Optional[Page], output_dir: Path, user_agent: str, doc_hash: Optional[str] = None):
        self.page = page
        self.output_dir = output_dir
        self.images_dir = output_dir / "imagenes"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = user_agent
        self.doc_hash = doc_hash
        self.extracted_pages: Dict[int, ExtractedPage] = {}

        # Sesión HTTP para descargas CDN
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Referer": "https://www.scribd.com/",
            "Accept": "*/*"
        })

        self.render_page: Optional[Page] = None
        if self.page:
            try:
                self.render_page = self.page.context.new_page()
            except Exception:
                pass
            self.setup_network_interceptor()

    def setup_network_interceptor(self):
        """Escucha peticiones salientes para capturar payloads JSONP de cada página."""
        if self.page:
            self.page.on("request", self._handle_network_request)

    def _handle_network_request(self, request: Request):
        """Procesa peticiones dirigidas a los chunks JSONP de página."""
        try:
            url = request.url
            if "scribdassets.com" in url and "/pages/" in url and url.endswith(".jsonp"):
                match = re.search(r"/pages/(\d+)-", url)
                if not match:
                    return
                page_num = int(match.group(1))

                # Extraer doc_hash de la URL si aún no se determinó
                if not self.doc_hash:
                    hash_match = re.search(r"scribdassets\.com/([^/]+)/pages/", url)
                    if hash_match:
                        self.doc_hash = hash_match.group(1)

                if page_num in self.extracted_pages and self.extracted_pages[page_num].image_path:
                    return

                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    self._process_jsonp_payload(page_num, resp.text)
        except Exception:
            pass

    def _process_jsonp_payload(self, page_num: int, jsonp_text: str):
        """Parsea el callback JSONP de Scribd y renderiza la imagen integrada de la página."""
        try:
            m = re.search(r'callback\(\s*\["(.*)"\]\s*\);', jsonp_text, re.DOTALL)
            if not m:
                m = re.search(r'\["(.*)"\]', jsonp_text, re.DOTALL)
                if not m:
                    return

            raw_html = m.group(1)
            clean_html = (
                raw_html.replace(r'\"', '"')
                .replace(r"\'", "'")
                .replace(r"\n", "\n")
                .replace(r"\/", "/")
            )

            self.render_page_html(page_num, clean_html)
        except Exception:
            pass

    def render_page_html(self, page_num: int, html_snippet: str) -> Optional[Path]:
        """
        Renderiza la página completa combinando capas de imagen y texto en alta resolución (PNG 2x Retina).
        """
        try:
            soup = BeautifulSoup(html_snippet, "html.parser")

            # Normalizar imágenes a HTTPS
            for img in soup.find_all("img"):
                src = img.get("orig") or img.get("src")
                if src:
                    if src.startswith("http://"):
                        src = src.replace("http://", "https://")
                    if src.startswith("//"):
                        src = "https:" + src
                    img["src"] = src

            # Extraer líneas de texto legibles sin duplicidad recursiva
            lines: List[str] = []
            text_layer = soup.find(class_=re.compile(r"text_layer"))
            if text_layer:
                # Los spans con clase 'a' representan los renglones principales
                row_spans = text_layer.find_all("span", class_="a")
                if row_spans:
                    for sp in row_spans:
                        txt = " ".join(sp.get_text().split())
                        if txt and txt not in lines:
                            lines.append(txt)
                else:
                    for block in text_layer.find_all(["div", "span"]):
                        txt = " ".join(block.get_text().split())
                        if txt and len(txt) > 2 and txt not in lines:
                            lines.append(txt)

            text_content = "\n".join(lines).strip()

            out_image_path = self.images_dir / f"pag_{page_num:04d}.png"

            # Renderizar con motor Chromium
            doc_hash_str = self.doc_hash or "2v8yixh6bkejepzg"
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <base href="https://html.scribdassets.com/{doc_hash_str}/">
    <style>
{SCRIBD_OFFICIAL_CSS}
    </style>
</head>
<body>
{str(soup)}
</body>
</html>"""

            render_target = self.render_page or self.page
            if render_target:
                render_target.set_content(full_html, wait_until="networkidle")
                page_el = render_target.locator(".newpage").first
                page_el.screenshot(path=str(out_image_path))

            extracted = ExtractedPage(
                page_number=page_num,
                text_content=text_content,
                lines=lines,
                image_path=str(out_image_path),
                local_image_paths=[str(out_image_path)],
                is_blurred=False
            )
            self.extracted_pages[page_num] = extracted
            return out_image_path

        except Exception:
            return None

    def extract_from_insumo_html(self, html_path: Path, max_pages: int = 5) -> Dict[int, ExtractedPage]:
        """
        Extrae y renderiza páginas disponibles directamente desde un archivo de insumo HTML descargado.
        """
        if not html_path.exists():
            return self.extracted_pages

        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Detectar hash del documento si existe en los enlaces
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("orig") or ""
            m = re.search(r"scribdassets\.com/([^/]+)/", src)
            if m:
                self.doc_hash = m.group(1)
                break

        page_divs = soup.find_all("div", class_=re.compile(r"newpage"))
        count = 0
        for p_div in page_divs:
            pid = p_div.get("id", "")
            m = re.search(r"page(\d+)", pid)
            if not m:
                continue
            p_num = int(m.group(1))
            self.render_page_html(p_num, str(p_div))
            count += 1
            if count >= max_pages:
                break

        return self.extracted_pages

    def extract_visible_pages(self) -> List[ExtractedPage]:
        """Retorna las páginas extraídas hasta el momento."""
        return list(self.extracted_pages.values())
