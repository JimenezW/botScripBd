"""
Orquestador Principal del Bot de Extracción y Reconstrucción en Scribd.
Ejecución: python main.py [--url URL] [--batch ARCHIVO] [--output-dir DIR] [--no-headless] [--max-pages N]
"""

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
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

from config import parse_arguments, extract_document_info, BotConfig
from core.browser import BrowserManager
from core.navigator import DocumentNavigator
from core.extractor import DocumentExtractor
from core.pdf_builder import PDFBuilder
from core.exporter import DocumentExporter

console = Console(force_terminal=True)


def process_document(url: str, config: BotConfig):
    """Procesa la extracción y reconstrucción completa de un documento de Scribd."""
    start_time = time.time()
    target = extract_document_info(url)
    doc_output_dir = config.output_dir / f"{target.document_id}_{target.slug}"
    doc_output_dir.mkdir(parents=True, exist_ok=True)

    console.print(Panel(
        f"[bold cyan]Documento:[/bold cyan] {target.slug}\n"
        f"[bold cyan]ID:[/bold cyan] {target.document_id}\n"
        f"[bold cyan]URL:[/bold cyan] {target.canonical_url}\n"
        f"[bold cyan]Destino:[/bold cyan] {doc_output_dir}",
        title="[bold green]Iniciando Extraccion en Scribd[/bold green]",
        border_style="green"
    ))

    bm = None
    try:
        if config.insumo_html and config.insumo_html.exists():
            console.print(f"[bold cyan]Modo Insumo:[/bold cyan] Extrayendo páginas directamente de {config.insumo_html}...")
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            br = pw.chromium.launch(headless=True)
            ctx = br.new_context(viewport={"width": 1200, "height": 1600}, device_scale_factor=2.0)
            render_pg = ctx.new_page()

            extractor = DocumentExtractor(render_pg, doc_output_dir, config.user_agent)
            exporter = DocumentExporter(doc_output_dir)
            
            target_limit = config.max_pages or 5
            extractor.extract_from_insumo_html(config.insumo_html, max_pages=target_limit)
            exporter.export_pages_json(extractor.extracted_pages)

            doc_title = "GoAnywhere MFT User Guide 7.7.0"
            doc_author = "Fortra, LLC"
            br.close()
            pw.stop()
        else:
            bm = BrowserManager(config)
            console.print("[yellow]Iniciando navegador Chromium con perfil Stealth...[/yellow]")
            page = bm.start()

            extractor = DocumentExtractor(page, doc_output_dir, config.user_agent)
            exporter = DocumentExporter(doc_output_dir)

            console.print(f"[yellow]Navegando a:[/yellow] {target.canonical_url}")
            page.goto(target.canonical_url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(3.0)

            bm.dismiss_cookie_banners()

            doc_title = page.title().split("|")[0].strip() or target.slug
            doc_author = "Autor Scribd"
            try:
                author_el = page.locator("a[data-testid='author-link'], [itemprop='author']").first
                if author_el.is_visible(timeout=1000):
                    doc_author = author_el.inner_text().strip()
            except Exception:
                pass

            navigator = DocumentNavigator(page, config)
            total_pages = navigator.get_total_pages() or 3712
            target_limit = config.max_pages if (config.max_pages and config.max_pages < total_pages) else total_pages

            console.print(f"[bold green]Titulo detectado:[/bold green] {doc_title}")
            console.print(f"[bold green]Paginas estimadas:[/bold green] {target_limit}")

            stuck_count = 0
            last_page_count = 0

            with Progress(
                TextColumn("[bold cyan]{task.description}"),
                BarColumn(bar_width=40),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total} pags)"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Extrayendo paginas...", total=target_limit)

                while True:
                    current_extracted = len(extractor.extracted_pages)
                    progress.update(task, completed=current_extracted)

                    if current_extracted > 0:
                        exporter.export_pages_json(extractor.extracted_pages)

                    if current_extracted >= target_limit:
                        break

                    page.mouse.wheel(0, 900)
                    time.sleep(1.2)

                    if len(extractor.extracted_pages) == current_extracted:
                        navigator.advance_next_page()

                    if len(extractor.extracted_pages) == last_page_count:
                        stuck_count += 1
                        if stuck_count >= 8:
                            console.print("\n[yellow]No se detectaron nuevas paginas tras 8 intentos. Finalizando avance.[/yellow]")
                            break
                    else:
                        stuck_count = 0
                        last_page_count = len(extractor.extracted_pages)

        # Fase de Consolidación
        console.print("\n[bold yellow]Consolidando salidas finales...[/bold yellow]")

        # 1. Metadatos
        meta_dict = {
            "document_id": target.document_id,
            "titulo": doc_title,
            "autor": doc_author,
            "url_origen": target.canonical_url,
            "paginas_extraidas": len(extractor.extracted_pages),
            "paginas_totales_estimadas": target_limit,
            "tiempo_segundos": round(time.time() - start_time, 2),
            "fecha": datetime.now().isoformat()
        }
        exporter.export_metadata(meta_dict)
        exporter.export_pages_json(extractor.extracted_pages)

        # 2. Markdown enriquecido (condicional)
        md_file = None
        if config.export_md:
            md_file = exporter.export_markdown(
                extractor.extracted_pages,
                title=doc_title,
                author=doc_author,
                source_url=target.canonical_url
            )

        # 3. PDF Reconstruido (condicional)
        pdf_file = None
        if config.export_pdf:
            pdf_path = doc_output_dir / f"{target.slug}.pdf"
            pdf_builder = PDFBuilder(pdf_path)
            pdf_file = pdf_builder.build_searchable_pdf(extractor.extracted_pages)

        elapsed = round(time.time() - start_time, 2)
        console.print(Panel(
            f"[bold green]Extraccion completada con exito en {elapsed} segundos.[/bold green]\n\n"
            f"[bold cyan]Paginas extraidas e integradas:[/bold cyan] {len(extractor.extracted_pages)}\n"
            f"[bold cyan]Metadatos & JSON:[/bold cyan] {doc_output_dir / 'paginas.json'}\n"
            f"[bold cyan]Imagenes de Paginas (HD 2x):[/bold cyan] {doc_output_dir / 'imagenes'}\n"
            f"[bold cyan]PDF Reconstruido:[/bold cyan] {pdf_file or 'Pospuesto para fase final'}\n"
            f"[bold cyan]Markdown:[/bold cyan] {md_file or 'Pospuesto para fase final'}",
            title="[bold green]Resumen de Resultados[/bold green]",
            border_style="green"
        ))

    finally:
        if bm:
            bm.close()


def main():
    config = parse_arguments()

    if config.batch_file and config.batch_file.exists():
        console.print(f"[bold cyan]Procesando archivo por lotes:[/bold cyan] {config.batch_file}")
        with open(config.batch_file, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        for idx, u in enumerate(urls, start=1):
            console.print(f"\n[bold magenta]=== Procesando Documento {idx}/{len(urls)} ===[/bold magenta]")
            try:
                process_document(u, config)
            except Exception as e:
                console.print(f"[bold red]Error procesando {u}: {e}[/bold red]")
            time.sleep(5.0)  # Cool-down entre documentos
    else:
        if not config.target_url:
            console.print("[bold red]Error: Debes proporcionar una URL mediante --url o un archivo mediante --batch.[/bold red]")
            sys.exit(1)
        process_document(config.target_url, config)


if __name__ == "__main__":
    main()
