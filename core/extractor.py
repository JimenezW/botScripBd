"""
Módulo Extractor de Capas de Contenido (Texto e Imágenes de Alta Resolución).
Intercepta las peticiones JSONP de cada página hacia el CDN de Scribd y descarga
las capas de texto vectorizado y las imágenes originales de alta definición (.jpg/.webp).
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Page, Request
from pydantic import BaseModel, Field


class ExtractedPage(BaseModel):
    """Representación estructurada de una página extraída."""
    page_number: int
    text_content: str = ""
    lines: List[str] = Field(default_factory=list)
    image_urls: List[str] = Field(default_factory=list)
    local_image_paths: List[str] = Field(default_factory=list)
    is_blurred: bool = False


class DocumentExtractor:
    """Gestiona la intercepción de red, parseo de JSONP y descarga de recursos de alta resolución."""

    def __init__(self, page: Page, output_dir: Path, user_agent: str):
        self.page = page
        self.output_dir = output_dir
        self.images_dir = output_dir / "imagenes"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = user_agent
        self.extracted_pages: Dict[int, ExtractedPage] = {}

        # Sesión HTTP persistente para descargar imágenes de alta resolución del CDN
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Referer": "https://www.scribd.com/",
            "Accept": "*/*"
        })

        # Configurar intercepción en tiempo real de peticiones de red
        self.setup_network_interceptor()

    def setup_network_interceptor(self):
        """Escucha las peticiones salientes del navegador para capturar los chunks JSONP de cada página."""
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

                # Si ya fue extraída, omitir
                if page_num in self.extracted_pages and self.extracted_pages[page_num].text_content:
                    return

                # Descargar payload JSONP directamente
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    self._parse_jsonp_payload(page_num, resp.text)
        except Exception:
            pass

    def _parse_jsonp_payload(self, page_num: int, jsonp_text: str):
        """Parsea el callback JSONP de Scribd, extrayendo texto e imágenes."""
        try:
            # Formato típico: window.page1_callback(["<html>..."]);
            m = re.search(r'callback\(\s*\["(.*)"\]\s*\);', jsonp_text, re.DOTALL)
            if not m:
                m = re.search(r'\["(.*)"\]', jsonp_text, re.DOTALL)
                if not m:
                    return

            raw_html = m.group(1)
            # Reemplazar escapes comunes de JavaScript
            clean_html = (
                raw_html.replace(r'\"', '"')
                .replace(r"\'", "'")
                .replace(r"\n", "\n")
                .replace(r"\/", "/")
            )

            soup = BeautifulSoup(clean_html, "lxml")

            # 1. Extraer Capa de Texto (.text_layer)
            lines: List[str] = []
            text_layer = soup.find(class_=re.compile(r"text_layer"))
            if text_layer:
                spans = text_layer.find_all(["span", "div"])
                for sp in spans:
                    txt = sp.get_text(strip=True)
                    if txt and len(txt) > 0 and txt not in lines:
                        lines.append(txt)

            text_content = "\n".join(lines).strip()

            # 2. Extraer Capa de Imagen de Alta Resolución (.image_layer)
            image_urls: List[str] = []
            local_paths: List[str] = []

            img_tags = soup.find_all("img")
            for img_idx, img in enumerate(img_tags, start=1):
                src = img.get("orig") or img.get("src") or img.get("data-src")
                if src:
                    # Asegurar protocolo HTTPS
                    if src.startswith("http://"):
                        src = src.replace("http://", "https://")
                    if src.startswith("//"):
                        src = "https:" + src

                    image_urls.append(src)
                    local_img = self._download_image(src, page_num, img_idx)
                    if local_img:
                        local_paths.append(str(local_img))

            extracted = ExtractedPage(
                page_number=page_num,
                text_content=text_content,
                lines=lines,
                image_urls=image_urls,
                local_image_paths=local_paths,
                is_blurred=False
            )

            self.extracted_pages[page_num] = extracted

        except Exception:
            pass

    def _download_image(self, url: str, page_num: int, img_idx: int) -> Optional[Path]:
        """Descarga la imagen original en alta definición desde el CDN de Scribd."""
        try:
            ext = ".jpg"
            if ".png" in url:
                ext = ".png"
            elif ".webp" in url:
                ext = ".webp"

            dest_file = self.images_dir / f"pag_{page_num:04d}_img_{img_idx}{ext}"
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

    def extract_visible_pages(self) -> List[ExtractedPage]:
        """Retorna las páginas extraídas hasta el momento."""
        return list(self.extracted_pages.values())
