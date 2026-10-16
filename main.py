"""
Orquestador Principal del Bot de Extracción y Reconstrucción Offline desde Insumos (Scribd).
Procesa archivos HTML guardados en disco y genera imágenes de alta fidelidad 2x Retina y metadatos.

Uso:
    python main.py [--insumo INSUMO_PATH] [--output-dir OUTPUT_DIR] [--max-pages N] [--scale S]
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Configurar codificación UTF-8 para consola Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

from config import parse_arguments, InsumoConfig
from core.insumo_parser import InsumoParser, InsumoDocument
from core.insumo_renderer import InsumoRenderer, RenderResult

console = Console(force_terminal=True)


def save_paginas_json(doc: InsumoDocument, render_results: dict, output_dir: Path) -> Path:
    """Genera y guarda el índice estructurado paginas.json."""
    doc_dir = output_dir / doc.slug
    doc_dir.mkdir(parents=True, exist_ok=True)
    json_path = doc_dir / "paginas.json"

    data = {
        "documento": {
            "titulo": doc.title,
            "slug": doc.slug,
            "total_paginas_documento": doc.total_document_pages,
            "paginas_procesadas": len(render_results),
            "fecha_procesamiento": datetime.now().isoformat(),
            "modo": "offline_insumo"
        },
        "paginas": []
    }

    for p_num in sorted(render_results.keys()):
        res: RenderResult = render_results[p_num]
        insumo_p = doc.populated_pages.get(p_num)
        
        rel_img_path = Path(res.image_path).name
        page_entry = {
            "numero_pagina": p_num,
            "imagen_relativa": f"imagenes/{rel_img_path}",
            "imagen_absoluta": res.image_path,
            "dimensiones": {
                "ancho": res.width,
                "alto": res.height
            },
            "lineas_texto_count": res.text_lines_count,
            "lineas_texto": insumo_p.text_lines if insumo_p else [],
            "texto_completo": res.text_content
        }
        data["paginas"].append(page_entry)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return json_path


def main():
    start_time = time.time()
    config = parse_arguments()

    console.print(Panel(
        f"[bold cyan]Origen Insumo:[/bold cyan] {config.insumo_path.resolve()}\n"
        f"[bold cyan]Directorio Salida:[/bold cyan] {config.output_dir.resolve()}\n"
        f"[bold cyan]Escala Renderizado:[/bold cyan] {config.device_scale_factor}x (Retina)\n"
        f"[bold cyan]Limite Paginas:[/bold cyan] {config.max_pages or 'Todas las detectadas'}",
        title="[bold green]Bot Scribd - Extractor Offline de Insumos[/bold green]",
        border_style="green"
    ))

    # Fase 1: Parseo de Insumo
    console.print("\n[bold yellow]Fase 1: Escaneando y analizando HTML de insumo...[/bold yellow]")
    try:
        parser = InsumoParser(config.insumo_path)
        doc = parser.parse()
    except Exception as e:
        console.print(f"[bold red]Error al parsear insumo:[/bold red] {e}")
        sys.exit(1)

    console.print(f"  [green]✓[/green] Documento: [bold]{doc.title}[/bold] ({doc.slug})")
    console.print(f"  [green]✓[/green] Total páginas documento original: [bold]{doc.total_document_pages}[/bold]")
    all_available = sorted(list(set(list(doc.populated_pages.keys()) + list(doc.page_hashes.keys()))))
    console.print(f"  [green]✓[/green] Páginas catalogadas en insumo: [bold]{len(all_available)}[/bold] (Pre-renderizadas en DOM: {len(doc.populated_pages)})")
    if doc.files_dir:
        console.print(f"  [green]✓[/green] Carpeta de recursos asociada: [bold]{doc.files_dir.name}[/bold]")

    if not all_available:
        console.print("[yellow]No se encontraron páginas catalogadas en el insumo. Finalizando.[/yellow]")
        return

    # Fase 2: Renderizado de Páginas
    console.print("\n[bold yellow]Fase 2: Renderizando páginas en alta resolución 2x Retina...[/bold yellow]")
    renderer = InsumoRenderer(
        device_scale_factor=config.device_scale_factor,
        headless=config.headless
    )

    pages_to_render = all_available
    if config.max_pages is not None:
        pages_to_render = pages_to_render[:config.max_pages]

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Renderizando paginas...", total=len(pages_to_render))
        results = renderer.render_document_pages(
            document=doc,
            output_dir=config.output_dir,
            max_pages=config.max_pages
        )
        progress.update(task, completed=len(results))

    # Fase 3: Generación de Metadatos
    console.print("\n[bold yellow]Fase 3: Generando catálogo de metadatos...[/bold yellow]")
    json_path = save_paginas_json(doc, results, config.output_dir)
    console.print(f"  [green]✓[/green] Metadatos guardados en: [bold cyan]{json_path}[/bold cyan]")

    # Tabla Resumen Final
    elapsed = time.time() - start_time
    table = Table(title=f"Resumen de Extracción - {doc.title}", border_style="cyan")
    table.add_column("Pág.", justify="center", style="bold")
    table.add_column("Dimensiones", justify="center")
    table.add_column("Líneas Texto", justify="right")
    table.add_column("Archivo Imagen", style="dim")

    for p_num in sorted(results.keys()):
        r = results[p_num]
        table.add_row(
            str(p_num),
            f"{r.width}x{r.height}",
            str(r.text_lines_count),
            Path(r.image_path).name
        )

    console.print(table)
    console.print(f"\n[bold green]✓ Proceso finalizado exitosamente en {elapsed:.2f} segundos.[/bold green]")
    console.print(f"[bold cyan]Salidas disponibles en:[/bold cyan] {config.output_dir.resolve() / doc.slug}\n")


if __name__ == "__main__":
    main()
