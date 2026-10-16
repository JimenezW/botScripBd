"""
Módulo de Parseo y Extracción de Insumos Locales de Scribd
Analiza archivos HTML guardados en disco, resuelve referencias a la carpeta _files/
y extrae las capas de contenido (.newpage, .text_layer, imágenes) y metadatos.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field


class InsumoPage(BaseModel):
    """Representación de una página extraída desde el HTML de insumo."""
    page_num: int
    text_content: str = ""
    text_lines: List[str] = Field(default_factory=list)
    html_snippet: str = ""
    image_sources: List[str] = Field(default_factory=list)
    width: Optional[int] = None
    height: Optional[int] = None


class InsumoDocument(BaseModel):
    """Representación global del documento obtenido desde el insumo."""
    title: str
    slug: str
    html_path: Path
    files_dir: Optional[Path] = None
    css_content: str = ""
    total_document_pages: int = 0
    populated_pages: Dict[int, InsumoPage] = Field(default_factory=dict)


class InsumoParser:
    """Parser especializado en procesar HTMLs de Scribd guardados en local."""

    def __init__(self, target_path: Path):
        self.target_path = Path(target_path)
        self.html_file = self._resolve_html_file(self.target_path)
        self.files_dir = self._resolve_files_dir(self.html_file)

    def _resolve_html_file(self, path: Path) -> Path:
        """Determina el archivo HTML principal a partir de una ruta de archivo o directorio."""
        if path.is_file() and path.suffix.lower() == ".html":
            return path
        if path.is_dir():
            html_files = list(path.glob("*.html"))
            if not html_files:
                raise FileNotFoundError(f"No se encontraron archivos .html en el directorio: {path}")
            # Priorizar el archivo más grande o representativo
            html_files.sort(key=lambda f: f.stat().st_size, reverse=True)
            return html_files[0]
        raise FileNotFoundError(f"La ruta de insumo no existe o no es válida: {path}")

    def _resolve_files_dir(self, html_path: Path) -> Optional[Path]:
        """Localiza la carpeta complementaria de recursos (_files o .files)."""
        stem = html_path.stem
        parent = html_path.parent

        candidate_names = [
            f"{stem}_files",
            f"{stem}.files",
            f"{stem}_archivos",
            f"{stem}.archivos"
        ]
        for name in candidate_names:
            candidate = parent / name
            if candidate.is_dir():
                return candidate
        return None

    def _extract_css(self, soup: BeautifulSoup) -> str:
        """Extrae y compila las reglas CSS necesarias desde las etiquetas <style> y fonts.css."""
        css_blocks = []

        # 1. Leer fonts.css si existe en files_dir
        if self.files_dir:
            fonts_css_path = self.files_dir / "fonts.css"
            if fonts_css_path.is_file():
                try:
                    css_blocks.append(fonts_css_path.read_text(encoding="utf-8", errors="ignore"))
                except Exception:
                    pass

        # 2. Extraer bloques <style> inline en el HTML
        for style_tag in soup.find_all("style"):
            content = style_tag.string or style_tag.get_text()
            if content:
                css_blocks.append(content)

        # 3. Reglas obligatorias de Scribd para alineación exacta
        required_overrides = """
        /* Sobrescrituras obligatorias de renderizado Scribd */
        .text_layer {
            transform: scale(0.2) !important;
            transform-origin: top left !important;
            -webkit-font-smoothing: antialiased;
        }
        .newpage {
            position: relative !important;
            overflow: hidden !important;
            background-color: #ffffff !important;
        }
        body {
            margin: 0 !important;
            padding: 0 !important;
            background-color: #ffffff !important;
        }
        """
        css_blocks.append(required_overrides)

        return "\n\n".join(css_blocks)

    def parse(self) -> InsumoDocument:
        """Realiza el parseo integral del archivo HTML de insumo."""
        raw_html = self.html_file.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(raw_html, "html.parser")

        # Metadatos del documento
        title_tag = soup.find("title")
        raw_title = title_tag.get_text().strip() if title_tag else self.html_file.stem
        # Limpiar sufijos típicos de Scribd como " | PDF | Internet Protocols..."
        title = re.sub(r"\s*\|\s*PDF.*$", "", raw_title).strip()
        slug = re.sub(r"[^\w\-_]", "_", title.lower())
        slug = re.sub(r"_+", "_", slug).strip("_")

        # Extraer CSS global consolidado
        css_content = self._extract_css(soup)

        # Buscar contenedores de páginas
        outer_pages = soup.find_all(class_="outer_page")
        total_document_pages = len(outer_pages)

        populated_pages: Dict[int, InsumoPage] = {}

        for p_elem in outer_pages:
            p_id = p_elem.get("id", "")
            match = re.search(r"outer_page_(\d+)", p_id)
            if not match:
                continue
            page_num = int(match.group(1))

            newpage_elem = p_elem.find(class_="newpage")
            text_layer_elem = p_elem.find(class_="text_layer")
            img_elems = p_elem.find_all("img")

            # Descartar contenedores vacíos no cargados en el DOM guardado
            if not newpage_elem and not text_layer_elem and not img_elems:
                continue

            # Extraer líneas de texto ordenadas
            text_lines = []
            if text_layer_elem:
                for span in text_layer_elem.find_all("span"):
                    text = span.get_text().strip()
                    if text:
                        text_lines.append(text)
            text_content = "\n".join(text_lines)

            # Extraer URLs / rutas de imágenes
            img_sources = []
            for img in img_elems:
                src = img.get("src") or img.get("orig")
                if src:
                    img_sources.append(src)

            # Extraer dimensiones de página
            width = None
            height = None
            target_for_dim = newpage_elem or p_elem
            style_attr = target_for_dim.get("style", "")
            w_match = re.search(r"width:\s*(\d+)px", style_attr)
            h_match = re.search(r"height:\s*(\d+)px", style_attr)
            if w_match:
                width = int(w_match.group(1))
            if h_match:
                height = int(h_match.group(1))

            # HTML snippet del elemento newpage (o del contenedor completo si no hay newpage)
            html_snippet = str(newpage_elem) if newpage_elem else str(p_elem)

            # Corregir rutas relativas en caso de que apunten a carpetas locales
            if self.files_dir:
                files_dir_name = self.files_dir.name
                # Si el HTML ya tiene referencias a ./files_dir_name/ o files_dir_name/
                # nos aseguramos de que sean accesibles con base_url
                pass

            populated_pages[page_num] = InsumoPage(
                page_num=page_num,
                text_content=text_content,
                text_lines=text_lines,
                html_snippet=html_snippet,
                image_sources=img_sources,
                width=width,
                height=height
            )

        return InsumoDocument(
            title=title,
            slug=slug,
            html_path=self.html_file,
            files_dir=self.files_dir,
            css_content=css_content,
            total_document_pages=total_document_pages,
            populated_pages=populated_pages
        )


if __name__ == "__main__":
    import sys
    test_path = Path("insumo")
    parser = InsumoParser(test_path)
    doc = parser.parse()
    print(f"[OK] Documento: {doc.title} ({doc.slug})")
    print(f"[OK] Total páginas en el documento: {doc.total_document_pages}")
    print(f"[OK] Páginas pobladas en insumo: {sorted(list(doc.populated_pages.keys()))}")
    for p_num in sorted(doc.populated_pages.keys())[:3]:
        p = doc.populated_pages[p_num]
        print(f"  - Pagina {p_num}: {len(p.text_lines)} lineas texto, {len(p.image_sources)} imagenes, dim: {p.width}x{p.height}")
