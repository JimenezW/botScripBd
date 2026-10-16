"""
Módulo de Configuración y Parámetros del Bot Scribd (Modo Insumo Offline)
Define modelos Pydantic, opciones de línea de comandos y parámetros de renderizado local.
"""

import argparse
import os
import re
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class InsumoConfig(BaseModel):
    """Configuración operativa del bot de procesamiento offline de insumos."""
    insumo_path: Path = Field(default_factory=lambda: Path("insumo"))
    output_dir: Path = Field(default_factory=lambda: Path("output"))
    max_pages: Optional[int] = None
    device_scale_factor: float = 2.0
    headless: bool = True
    export_pdf: bool = False
    export_md: bool = False


def parse_arguments() -> InsumoConfig:
    """
    Parsea los argumentos pasados por la línea de comandos y retorna un InsumoConfig validado.
    """
    parser = argparse.ArgumentParser(
        description="Bot de Extracción y Reconstrucción Offline de Documentos Scribd desde Insumos Locales"
    )

    parser.add_argument(
        "--insumo",
        type=str,
        default="insumo",
        help="Ruta al archivo .html o carpeta con insumos guardados (por defecto: 'insumo/')"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directorio raíz para almacenar las salidas del bot (por defecto: 'output/')"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Límite opcional de páginas a procesar (None para procesar todas las páginas detectadas)"
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=2.0,
        help="Factor de escala para renderizado de imágenes Retina (por defecto: 2.0)"
    )
    parser.add_argument(
        "--export-pdf",
        action="store_true",
        help="Exportar documento a formato PDF (opcional, postergado)"
    )
    parser.add_argument(
        "--export-md",
        action="store_true",
        help="Exportar documento a formato Markdown (opcional, postergado)"
    )

    args = parser.parse_args()

    return InsumoConfig(
        insumo_path=Path(args.insumo),
        output_dir=Path(args.output_dir),
        max_pages=args.max_pages,
        device_scale_factor=args.scale,
        export_pdf=args.export_pdf,
        export_md=args.export_md
    )


if __name__ == "__main__":
    cfg = parse_arguments()
    print(f"[OK] InsumoConfig cargada: insumo={cfg.insumo_path}, output={cfg.output_dir}, scale={cfg.device_scale_factor}")
