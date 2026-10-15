"""
Módulo de Exportación y Ensamblaje de Salidas (Markdown y JSON Estructurado).
Genera la documentación enriquecida combinando texto, enlaces relativos a imágenes locales y metadatos.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from core.extractor import ExtractedPage


class DocumentExporter:
    """Gestiona la exportación de páginas extraídas a formatos Markdown y JSON."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def export_metadata(self, metadata: Dict[str, Any], filename: str = "metadata.json") -> Path:
        """Guarda la información global del documento en formato JSON."""
        dest_file = self.output_dir / filename
        with open(dest_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        return dest_file

    def export_pages_json(self, pages: Dict[int, ExtractedPage], filename: str = "paginas.json") -> Path:
        """Serializa todas las páginas extraídas con sus rutas y textos a un JSON consolidado."""
        dest_file = self.output_dir / filename
        data = [pages[num].model_dump() for num in sorted(pages.keys())]
        with open(dest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return dest_file

    def export_markdown(
        self,
        pages: Dict[int, ExtractedPage],
        title: str,
        author: str,
        source_url: str,
        filename: str = "contenido.md"
    ) -> Path:
        """
        Genera un archivo Markdown enriquecido con el texto de cada página y las
        referencias relativas a las imágenes y capturas descargadas.
        """
        dest_file = self.output_dir / filename
        sorted_page_nums = sorted(pages.keys())

        lines = [
            f"# {title}",
            "",
            f"- **Fuente:** [{source_url}]({source_url})",
            f"- **Autor / Subido por:** {author or 'Desconocido'}",
            f"- **Total Páginas Extraídas:** {len(sorted_page_nums)}",
            f"- **Fecha de Extracción:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            ""
        ]

        for page_num in sorted_page_nums:
            page = pages[page_num]
            lines.append(f"## Página {page_num}")
            lines.append("")

            # Vincular imágenes locales de esta página
            if page.local_image_paths:
                for img_path_str in page.local_image_paths:
                    img_path = Path(img_path_str)
                    rel_path = f"imagenes/{img_path.name}"
                    lines.append(f"![Diagrama Página {page_num}]({rel_path})")
                    lines.append("")

            # Texto extraído
            if page.text_content:
                lines.append(page.text_content)
                lines.append("")
            else:
                lines.append("*(Página visual sin capa de texto estructurada)*")
                lines.append("")

            lines.append("---")
            lines.append("")

        with open(dest_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return dest_file
