"""
Módulo Extractor de Capas de Contenido (Texto e Imágenes de Alta Resolución).
Extrae texto ordenado de .text_layer y descarga imágenes vectoriales/renders de .image_layer.
"""

import os
import re
import requests
from pathlib import Path
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from playwright.sync_api import Page, Locator
from bs4 import BeautifulSoup


class ExtractedPage(BaseModel):
    """Representación estructurada de una página extraída."""
    page_number: int
    text_content: str = ""
    lines: List[str] = Field(default_factory=list)
    image_urls: List[str] = Field(default_factory=list)
    local_image_paths: List[str] = Field(default_factory=list)
    is_blurred: bool = False


class DocumentExtractor:
    """Gestiona el escaneo del DOM y la descarga de recursos por página."""

    def __init__(self, page: Page, output_dir: Path, user_agent: str):
        self.page = page
        self.output_dir = output_dir
        self.images_dir = output_dir / "imagenes"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = user_agent
        self.extracted_pages: Dict[int, ExtractedPage] = {}

        # Sesión HTTP configurada para descargas de CDN
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Referer": "https://www.scribd.com/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
        })

    def extract_visible_pages(self) -> List[ExtractedPage]:
        """
        Escanea todos los contenedores .outer_page actualmente hidratados en el DOM
        y extrae el contenido de aquellas páginas que aún no han sido procesadas.
        """
        new_pages: List[ExtractedPage] = []

        try:
            page_elements = self.page.locator(".outer_page").all()
        except Exception:
            return new_pages

        for idx, el in enumerate(page_elements, start=1):
            try:
                # 1. Determinar número de página
                page_attr = el.get_attribute("data-page-number") or el.get_attribute("id")
                page_num = idx
                if page_attr:
                    m = re.search(r"\d+", page_attr)
                    if m:
                        page_num = int(m.group(0))

                # Si ya la procesamos y tiene texto, omitir
                if page_num in self.extracted_pages and self.extracted_pages[page_num].text_content:
                    continue

                # 2. Verificar si está difuminada (blurred)
                classes = el.get_attribute("class") or ""
                is_blurred = "blurred_page" in classes

                # 3. Extraer Capa de Texto (.text_layer)
                html_snippet = el.inner_html()
                soup = BeautifulSoup(html_snippet, "lxml")
                
                text_layer = soup.find(class_=re.compile(r"text_layer"))
                lines: List[str] = []
                if text_layer:
                    # Extraer spans de texto
                    spans = text_layer.find_all(["span", "div"])
                    for sp in spans:
                        txt = sp.get_text(strip=True)
                        if txt and len(txt) > 0:
                            lines.append(txt)

                text_content = "\n".join(lines).strip()

                # 4. Extraer Capa de Imágenes (.image_layer)
                image_urls: List[str] = []
                local_paths: List[str] = []

                img_tags = soup.find_all("img")
                for img_idx, img in enumerate(img_tags, start=1):
                    src = img.get("src") or img.get("data-src")
                    if src and src.startswith("http") and "scribdassets.com" in src:
                        # Excluir iconos pequeños o avatares
                        if "avatar" in src or "icon" in src:
                            continue
                        
                        image_urls.append(src)
                        # Descargar la imagen de alta resolución
                        local_file = self._download_image(src, page_num, img_idx)
                        if local_file:
                            local_paths.append(str(local_file))

                # 5. Si hay imagen pero no hubo spans de texto, capturar screenshot como respaldo
                if not local_paths:
                    screenshot_file = self._capture_page_screenshot(el, page_num)
                    if screenshot_file:
                        local_paths.append(str(screenshot_file))

                extracted = ExtractedPage(
                    page_number=page_num,
                    text_content=text_content,
                    lines=lines,
                    image_urls=image_urls,
                    local_image_paths=local_paths,
                    is_blurred=is_blurred
                )

                self.extracted_pages[page_num] = extracted
                new_pages.append(extracted)

            except Exception:
                continue

        return new_pages

    def _download_image(self, url: str, page_num: int, img_idx: int) -> Optional[Path]:
        """Descarga una imagen de la página desde el CDN de Scribd y la guarda localmente."""
        try:
            # Obtener extensión del archivo
            ext = ".webp"
            if ".png" in url:
                ext = ".png"
            elif ".jpg" in url or ".jpeg" in url:
                ext = ".jpg"

            dest_file = self.images_dir / f"pag_{page_num:03d}_img_{img_idx}{ext}"
            if dest_file.exists() and dest_file.stat().st_size > 500:
                return dest_file

            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 500:
                with open(dest_file, "wb") as f:
                    f.write(resp.content)
                return dest_file
        except Exception:
            pass
        return None

    def _capture_page_screenshot(self, locator: Locator, page_num: int) -> Optional[Path]:
        """Captura un render directo del contenedor de página en caso de no hallar enlace img directo."""
        try:
            dest_file = self.images_dir / f"pag_{page_num:03d}_render.png"
            if dest_file.exists():
                return dest_file
            locator.screenshot(path=str(dest_file))
            return dest_file
        except Exception:
            pass
        return None
