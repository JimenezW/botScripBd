"""
Módulo de Renderizado Offline de Alta Fidelidad (InsumoRenderer)
Utiliza Playwright local en modo headless a 2x Retina para componer y capturar cada
página de insumo como una imagen PNG nítida con sus fuentes y estilos CSS originales,
sirviendo todos los recursos gráficos y tipográficos de forma 100% offline.
"""

import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from pydantic import BaseModel

from core.insumo_parser import InsumoDocument, InsumoPage


class RenderResult(BaseModel):
    """Resultado del renderizado de una página."""
    page_num: int
    image_path: str
    width: int
    height: int
    text_content: str
    text_lines_count: int


class InsumoRenderer:
    """Renderiza páginas aisladas de Scribd en imágenes PNG de alta resolución."""

    def __init__(self, device_scale_factor: float = 2.0, headless: bool = True):
        self.device_scale_factor = device_scale_factor
        self.headless = headless

    def render_document_pages(
        self,
        document: InsumoDocument,
        output_dir: Path,
        max_pages: Optional[int] = None
    ) -> Dict[int, RenderResult]:
        """
        Renderiza todas las páginas pobladas del documento y las guarda en el directorio de salida.
        """
        doc_output_dir = Path(output_dir) / document.slug
        images_dir = doc_output_dir / "imagenes"
        images_dir.mkdir(parents=True, exist_ok=True)

        pages_to_render = sorted(list(document.populated_pages.keys()))
        if max_pages is not None:
            pages_to_render = pages_to_render[:max_pages]

        # Mapear todos los archivos locales en la carpeta _files para resolución offline inmediata
        asset_map: Dict[str, Path] = {}
        if document.files_dir and document.files_dir.is_dir():
            for f in document.files_dir.iterdir():
                if f.is_file():
                    asset_map[f.name.lower()] = f

        # Sesión HTTP auxiliar para autodescarga de assets faltantes en el insumo
        import requests
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.scribd.com/"
        })

        results: Dict[int, RenderResult] = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=["--disable-web-security", "--allow-file-access-from-files"]
            )
            context = browser.new_context(
                viewport={"width": 1200, "height": 1600},
                device_scale_factor=self.device_scale_factor
            )
            page = context.new_page()

            # Enrutador offline: intercepta todas las peticiones a imágenes y fuentes
            def handle_route(route):
                req_url = route.request.url
                filename = unquote(req_url.split("/")[-1].split("?")[0]).lower()
                if filename in asset_map:
                    target_file = asset_map[filename]
                    content_type = "image/jpeg" if target_file.suffix.lower() in [".jpg", ".jpeg"] else \
                                   "image/png" if target_file.suffix.lower() == ".png" else \
                                   "text/css" if target_file.suffix.lower() == ".css" else \
                                   "font/woff2" if target_file.suffix.lower() == ".woff2" else "application/octet-stream"
                    route.fulfill(path=str(target_file), content_type=content_type)
                else:
                    route.abort()

            page.route("**/*", handle_route)

            for page_num in pages_to_render:
                insumo_page = document.populated_pages[page_num]
                out_path = images_dir / f"pagina_{page_num:04d}.png"

                w = insumo_page.width or 902
                h = insumo_page.height or 1167

                # Normalizar fragmento HTML y corregir atributos
                soup = BeautifulSoup(insumo_page.html_snippet, "html.parser")
                
                # Limpiar cualquier transform: scale inline heredado del zoom al guardar
                for target_box in soup.find_all(class_=["newpage", "outer_page"]):
                    curr_style = target_box.get("style", "")
                    if "transform:" in curr_style:
                        new_style = re.sub(r"transform:\s*scale\([^)]+\);?", "transform: none !important;", curr_style)
                        target_box["style"] = new_style

                for img in soup.find_all("img"):
                    orig_url = img.get("orig") or img.get("src")
                    if orig_url:
                        fname = unquote(orig_url.split("/")[-1].split("?")[0])
                        fname_lower = fname.lower()
                        # Si no existe localmente en el insumo, descargarlo y guardarlo en _files
                        if fname_lower not in asset_map and document.files_dir:
                            cdn_url = orig_url.replace("http://html.scribd.com/", "https://html.scribdassets.com/")
                            if not cdn_url.startswith("http"):
                                cdn_url = f"https://html.scribdassets.com/{cdn_url}"
                            try:
                                r = session.get(cdn_url, timeout=5)
                                if r.status_code == 200:
                                    local_saved = document.files_dir / fname
                                    local_saved.write_bytes(r.content)
                                    asset_map[fname_lower] = local_saved
                            except Exception:
                                pass

                        img["src"] = f"http://offline-assets/{fname}"

                normalized_snippet = str(soup)

                full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <base href="http://offline-assets/">
    <style>
        {document.css_content}
        html, body {{
            margin: 0 !important;
            padding: 0 !important;
            background-color: #ffffff !important;
        }}
    </style>
</head>
<body>
    {normalized_snippet}
</body>
</html>"""

                page.set_content(full_html, wait_until="load")
                page.evaluate("() => document.fonts.ready")
                time.sleep(0.15)

                target = page.locator(".newpage, .outer_page").first
                if target.count() > 0:
                    target.screenshot(path=str(out_path))
                else:
                    page.screenshot(path=str(out_path), full_page=True)

                results[page_num] = RenderResult(
                    page_num=page_num,
                    image_path=str(out_path.resolve()),
                    width=int(w * self.device_scale_factor),
                    height=int(h * self.device_scale_factor),
                    text_content=insumo_page.text_content,
                    text_lines_count=len(insumo_page.text_lines)
                )

            browser.close()

        return results


if __name__ == "__main__":
    from core.insumo_parser import InsumoParser
    parser = InsumoParser(Path("insumo"))
    doc = parser.parse()
    renderer = InsumoRenderer(device_scale_factor=2.0)
    res = renderer.render_document_pages(doc, Path("output"), max_pages=2)
    for p_num, r in res.items():
        print(f"[OK] Pagina {p_num} renderizada: {r.image_path} ({r.width}x{r.height})")
