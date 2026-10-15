"""
Módulo de Construcción de PDF Consolidado de Alta Resolución (1:1).
Ensambla las imágenes descargadas de cada página en un único PDF y superpone
la capa de texto extraída para generar un documento idéntico al original, buscable y seleccionable.
"""

from pathlib import Path
from typing import Dict, List, Optional
import pymupdf as fitz  # PyMuPDF
from PIL import Image
from core.extractor import ExtractedPage


class PDFBuilder:
    """Compila las imágenes y textos extraídos en un archivo PDF idéntico al manual original."""

    def __init__(self, output_pdf_path: Path):
        self.output_pdf_path = output_pdf_path

    def build_searchable_pdf(self, pages: Dict[int, ExtractedPage]) -> Optional[Path]:
        """
        Crea un PDF a partir del diccionario de páginas ordenadas numéricamente.
        Inserta la imagen en alta definición y añade la capa de texto invisible
        para permitir búsqueda interna y selección de texto.
        """
        if not pages:
            return None

        # Ordenar páginas por número
        sorted_page_nums = sorted(pages.keys())
        doc = fitz.open()

        for page_num in sorted_page_nums:
            page_data = pages[page_num]

            # Buscar imagen local disponible para esta página
            image_path_str = None
            if page_data.local_image_paths:
                for img_p in page_data.local_image_paths:
                    if Path(img_p).exists() and Path(img_p).stat().st_size > 500:
                        image_path_str = img_p
                        break

            if not image_path_str:
                continue

            img_path = Path(image_path_str)

            try:
                # Obtener dimensiones reales de la imagen con PIL
                with Image.open(img_path) as pil_img:
                    width, height = pil_img.size

                # Crear página en el documento con las mismas dimensiones
                rect = fitz.Rect(0, 0, width, height)
                pdf_page = doc.new_page(width=width, height=height)

                # Si es formato webp, convertir a PNG en memoria para compatibilidad PyMuPDF
                if img_path.suffix.lower() == ".webp":
                    import io
                    with Image.open(img_path) as pil_img:
                        png_buffer = io.BytesIO()
                        pil_img.save(png_buffer, format="PNG")
                        png_bytes = png_buffer.getvalue()
                    pdf_page.insert_image(rect, stream=png_bytes)
                else:
                    pdf_page.insert_image(rect, filename=str(img_path))

                # Inyectar texto en modo invisible (render_mode=3) si hay texto disponible
                if page_data.text_content:
                    try:
                        # Insertar caja de texto para habilitar búsqueda
                        pdf_page.insert_textbox(
                            rect,
                            page_data.text_content,
                            fontsize=10,
                            fontname="helv",
                            render_mode=3  # Modo 3: texto invisible pero seleccionable
                        )
                    except Exception:
                        pass

            except Exception:
                continue

        if len(doc) > 0:
            self.output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(self.output_pdf_path), garbage=4, deflate=True)
            doc.close()
            return self.output_pdf_path

        doc.close()
        return None
