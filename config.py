"""
Módulo de Configuración y Parámetros del Bot Scribd
Define constantes, opciones de línea de comandos, modelos Pydantic y utilidades de normalización de URLs.
"""

import argparse
import os
import re
from pathlib import Path
from typing import Optional, Tuple
from pydantic import BaseModel, Field


class DocumentTarget(BaseModel):
    """Información estructurada extraída de una URL de Scribd."""
    raw_url: str
    document_id: str
    slug: str
    canonical_url: str


class BotConfig(BaseModel):
    """Configuración operativa del bot de extracción."""
    target_url: Optional[str] = None
    batch_file: Optional[Path] = None
    output_dir: Path = Field(default_factory=lambda: Path("output"))
    headless: bool = True
    min_delay: float = 1.2
    max_delay: float = 2.8
    ad_timeout: int = 12
    max_pages: Optional[int] = None
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    viewport_width: int = 1920
    viewport_height: int = 1080
    insumo_html: Optional[Path] = None
    export_pdf: bool = False
    export_md: bool = False


def extract_document_info(url: str) -> DocumentTarget:
    """
    Extrae el document_id numérico y el slug descriptivo de una URL de Scribd.
    Soporta múltiples variantes:
      - https://es.scribd.com/document/855660163/ga7-7-0-user-guide
      - https://www.scribd.com/document/855660163/ga7-7-0-user-guide
      - https://www.scribd.com/doc/855660163
      - https://es.scribd.com/doc/855660163/anything
    """
    clean_url = url.strip()
    match = re.search(r"/(?:document|doc)/(\d+)(?:/([^/?#]+))?", clean_url, re.IGNORECASE)
    if not match:
        raise ValueError(
            f"No se pudo identificar un ID de documento válido en la URL: '{clean_url}'. "
            "Asegúrate de que contenga el patrón '/document/<id>' o '/doc/<id>'."
        )

    doc_id = match.group(1)
    slug = match.group(2) or f"doc_{doc_id}"
    canonical_url = f"https://www.scribd.com/document/{doc_id}/{slug}"

    return DocumentTarget(
        raw_url=clean_url,
        document_id=doc_id,
        slug=slug,
        canonical_url=canonical_url
    )


def parse_arguments() -> BotConfig:
    """
    Parsea los argumentos pasados por la línea de comandos y retorna un BotConfig validado.
    """
    parser = argparse.ArgumentParser(
        description="Bot Automatizado de Extracción y Reconstrucción de Documentos de Scribd (Sin Login)"
    )

    parser.add_argument(
        "--url",
        type=str,
        default="https://es.scribd.com/document/855660163/ga7-7-0-user-guide",
        help="URL del documento de Scribd a extraer (por defecto: GoAnywhere MFT 7.7.0 User Guide)"
    )
    parser.add_argument(
        "--batch",
        type=str,
        default=None,
        help="Ruta a un archivo .txt con una lista de URLs de Scribd a procesar en lote"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directorio raíz para almacenar las salidas del bot (por defecto: 'output/')"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Ejecutar el navegador con interfaz gráfica visible (útil para depuración)"
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=1.2,
        help="Retardo mínimo en segundos entre acciones (por defecto: 1.2s)"
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=2.8,
        help="Retardo máximo en segundos entre acciones (por defecto: 2.8s)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Límite opcional de páginas a extraer (None para extraer todo el documento)"
    )
    parser.add_argument(
        "--insumo-html",
        type=str,
        default=None,
        help="Ruta a un archivo .html guardado en disco para extraer directamente sin navegar"
    )
    parser.add_argument(
        "--export-pdf",
        action="store_true",
        help="Exportar documento reconstruido a formato PDF (opcional)"
    )
    parser.add_argument(
        "--export-md",
        action="store_true",
        help="Exportar documento estructurado a formato Markdown (opcional)"
    )

    args = parser.parse_args()

    batch_path = Path(args.batch) if args.batch else None
    insumo_path = Path(args.insumo_html) if args.insumo_html else None
    output_path = Path(args.output_dir)

    return BotConfig(
        target_url=args.url if not batch_path else None,
        batch_file=batch_path,
        output_dir=output_path,
        headless=not args.no_headless,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        max_pages=args.max_pages,
        insumo_html=insumo_path,
        export_pdf=args.export_pdf,
        export_md=args.export_md
    )


if __name__ == "__main__":
    # Prueba de normalización de URLs
    test_urls = [
        "https://es.scribd.com/document/855660163/ga7-7-0-user-guide",
        "https://www.scribd.com/document/855660163/ga7-7-0-user-guide",
        "https://www.scribd.com/doc/855660163",
        "https://es.scribd.com/document/12345/some-title?query=1#section"
    ]
    for u in test_urls:
        info = extract_document_info(u)
        print(f"[OK] {u} -> ID: {info.document_id}, Slug: {info.slug}, Canonical: {info.canonical_url}")
