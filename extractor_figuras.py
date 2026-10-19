"""
Extractor de Figuras y Diagramas de Alta Fidelidad (extractor_figuras.py)

Analiza las capas 'image_layer' de los JSONPs de Scribd y los archivos atlas locales.
Aplica detección precisa de contornos de 4 bordes (top, bottom, left, right) para:
  1. Extraer exclusivamente figuras, diagramas y tarjetas UI reales.
  2. Suprimir callouts de texto (Warning, Tip, Note) y fragmentos de código.
  3. Recortar limpiamente los cuadros UI eliminando botones huérfanos y texto exterior.
  4. Desacoplar rebanadas compuestas en figuras individuales (ej: página 57).
  5. Almacenar resultados en output/goanywhere_mft_user_guide_7_7_0/figuras/ y figuras_paginas.json.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote

# Configurar codificación UTF-8 para consola Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from bs4 import BeautifulSoup
from PIL import Image, ImageStat
import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

console = Console(force_terminal=True)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Extractor refinado de figuras y diagramas desde insumo Scribd")
    parser.add_argument(
        "--origen",
        type=Path,
        default=Path("output/goanywhere_mft_user_guide_7_7_0"),
        help="Directorio de salida principal (default: output/goanywhere_mft_user_guide_7_7_0)"
    )
    parser.add_argument(
        "--mirror-reporte",
        action="store_true",
        default=True,
        help="Sincronizar una copia espejo en reporte/goanywhere_mft_user_guide_7_7_0 (default: True)"
    )
    parser.add_argument(
        "--insumo",
        type=Path,
        default=None,
        help="Ruta al archivo HTML de insumo"
    )
    parser.add_argument(
        "--desde",
        type=int,
        default=1,
        help="Página inicial (default: 1)"
    )
    parser.add_argument(
        "--hasta",
        type=int,
        default=100,
        help="Página final (default: 100)"
    )
    parser.add_argument(
        "--pagina",
        type=int,
        default=None,
        help="Procesar exclusivamente una página puntual (ej: --pagina 44)"
    )
    parser.add_argument(
        "--forzar-toc",
        action="store_true",
        help="Si se establece, intenta buscar figuras en páginas de TOC (< 39)"
    )
    return parser.parse_args()


def localizar_insumo(insumo_arg: Optional[Path]) -> Tuple[Path, Optional[Path]]:
    """Localiza el archivo HTML de insumo y su carpeta _files asociada."""
    if insumo_arg and insumo_arg.is_file():
        html_file = insumo_arg
    else:
        insumo_dir = Path("insumo")
        html_files = list(insumo_dir.glob("*.html"))
        if not html_files:
            raise FileNotFoundError("No se encontró ningún archivo HTML en la carpeta 'insumo/'")
        html_file = html_files[0]

    files_dir = None
    expected_files_dir = html_file.parent / f"{html_file.stem}_files"
    if expected_files_dir.is_dir():
        files_dir = expected_files_dir

    return html_file, files_dir


def cargar_mapa_hashes(html_file: Path) -> Tuple[str, Dict[int, str]]:
    """Lee las URLs de páginas del insumo y mapea numero_pagina -> hash."""
    raw = html_file.read_text(encoding="utf-8", errors="ignore")
    matches = re.findall(r'scribdassets\.com/([^/]+)/pages/(\d+)-([a-f0-9]+)\.jsonp', raw)
    if not matches:
        return "2v8yixh6bkejepzg", {}
    doc_hash = matches[0][0]
    page_hashes = {int(p): h for _, p, h in matches}
    return doc_hash, page_hashes


def composite_on_white(im: Image.Image) -> Image.Image:
    """Compone imágenes con canal alfa o paleta transparente sobre un fondo blanco puro."""
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im_rgba = im.convert("RGBA")
        bg = Image.new("RGB", im_rgba.size, (255, 255, 255))
        bg.paste(im_rgba, mask=im_rgba.split()[3])
        return bg
    return im.convert("RGB")


def detectar_tarjetas_ui(crop_im: Image.Image) -> List[Tuple[int, int, int, int]]:
    """
    Inspecciona una rebanada gráfica del atlas.
    Aplica análisis de bordes horizontales y verticales para detectar cajas UI
    rectangulares cerradas (4 bordes), eliminando texto exterior o separando tarjetas compuestas.
    Si es un diagrama complejo (ej: p39), lo mantiene íntegro.
    """
    gray = crop_im.convert("L")
    w, h = gray.size
    pixels = gray.load()

    # Si es un diagrama grande de arquitectura o proceso (ej: página 39)
    stat = ImageStat.Stat(crop_im)
    if w >= 550 and h >= 350 and stat.stddev[0] > 30:
        return [(0, 0, w, h)]

    # Si más del 75% es un fondo monocromático no-blanco (Callouts de Warning/Tip), descartar
    colors = sorted(crop_im.getcolors(maxcolors=200000) or [], reverse=True)
    if colors:
        top_cnt, top_col = colors[0]
        pct = top_cnt / (w * h)
        is_pure_white = all(c >= 245 for c in top_col)
        if pct >= 0.70 and not is_pure_white:
            # Fondo de callout tintado
            return []

    # Detectar líneas horizontales con racha continua oscura
    min_line_len = max(60, int(w * 0.40))
    horizontal_lines = []
    for y in range(h):
        dark_streak = 0
        max_streak = 0
        for x in range(w):
            if pixels[x, y] < 140:
                dark_streak += 1
                if dark_streak > max_streak:
                    max_streak = dark_streak
            else:
                dark_streak = 0
        if max_streak >= min_line_len:
            horizontal_lines.append((y, max_streak))

    if not horizontal_lines:
        # Si no hay bordes horizontales pero tiene alta varianza y buen tamaño, podría ser gráfico libre
        if stat.stddev[0] >= 32 and w >= 220 and h >= 90:
            return [(0, 0, w, h)]
        return []

    # Agrupar líneas consecutivas en bordes discretos
    edges = []
    curr = [horizontal_lines[0]]
    for (y, s) in horizontal_lines[1:]:
        if y - curr[-1][0] <= 4:
            curr.append((y, s))
        else:
            edges.append((int(sum(p[0] for p in curr) / len(curr)), max(p[1] for p in curr)))
            curr = [(y, s)]
    if curr:
        edges.append((int(sum(p[0] for p in curr) / len(curr)), max(p[1] for p in curr)))

    # Emparejar bordes top y bottom que delimiten una tarjeta cerrada
    valid_cards = []
    i = 0
    while i < len(edges) - 1:
        top_y, top_len = edges[i]
        found_card = None

        for j in range(i + 1, len(edges)):
            bot_y, bot_len = edges[j]
            box_h = bot_y - top_y
            if 35 <= box_h <= 600:
                # Comprobar si las longitudes de trazo son consistentes
                if abs(top_len - bot_len) <= max(top_len, bot_len) * 0.40:
                    # Encontrar límites horizontales (x1, x2)
                    x_starts = []
                    x_ends = []
                    for y_test in [top_y, bot_y]:
                        cur_start = None
                        max_s = 0
                        best_start = 0
                        streak = 0
                        for x in range(w):
                            if pixels[x, y_test] < 140:
                                if cur_start is None:
                                    cur_start = x
                                streak += 1
                                if streak > max_s:
                                    max_s = streak
                                    best_start = cur_start
                            else:
                                streak = 0
                                cur_start = None
                        x_starts.append(best_start)
                        x_ends.append(best_start + max_s)

                    bx1 = max(0, min(x_starts))
                    bx2 = min(w, max(x_ends))
                    box_w = bx2 - bx1

                    if box_w >= min_line_len:
                        # VALIDACIÓN DE CIERRE VERTICAL (Bordes izquierdo y derecho)
                        # Una tarjeta real tiene bordes laterales oscuros (> 45% de altura)
                        left_dark = [pixels[bx1, y] < 155 for y in range(top_y, bot_y)].count(True)
                        right_dark = [pixels[min(w - 1, bx2 - 1), y] < 155 for y in range(top_y, bot_y)].count(True)

                        ratio_left = left_dark / box_h
                        ratio_right = right_dark / box_h

                        # Si ambos bordes laterales están presentes (caja cerrada)
                        if ratio_left >= 0.40 and ratio_right >= 0.40:
                            found_card = (bx1, top_y, bx2, bot_y + 1, j)
                            break
                        # Si no hay borde derecho (como en callouts que solo tienen barra izquierda), se descarta

        if found_card:
            bx1, top_y, bx2, bot_y_p1, j_idx = found_card
            valid_cards.append((bx1, top_y, bx2, bot_y_p1))
            i = j_idx  # Avanzar más allá de esta tarjeta
        else:
            i += 1

    if not valid_cards:
        # Si no hubo tarjetas cerradas, verificar si es un diagrama libre
        if stat.stddev[0] >= 30 and w >= 200 and h >= 80:
            return [(0, 0, w, h)]
        return []

    return valid_cards


def procesar_pagina_figuras(
    p_num: int,
    p_hash: str,
    doc_hash: str,
    session: requests.Session,
    files_dir: Optional[Path],
    figuras_out_dir: Path
) -> List[dict]:
    """Extrae las figuras de una página individual a partir del atlas local de Scribd."""
    url = f"https://html.scribdassets.com/{doc_hash}/pages/{p_num}-{p_hash}.jsonp"
    try:
        r = session.get(url, timeout=5)
        if r.status_code != 200:
            return []
        m = re.search(r'window\.page\d+_callback\(\[(.*)\]\);?', r.text, re.DOTALL)
        if not m:
            return []
        html_content = json.loads("[" + m.group(1) + "]")[0]
    except Exception:
        return []

    soup = BeautifulSoup(html_content, "html.parser")

    # Localizar archivo atlas en _files
    atlas_cand = list(files_dir.glob(f"{p_num}-{p_hash}.*")) if files_dir else []
    if not atlas_cand:
        return []

    try:
        atlas_im = Image.open(atlas_cand[0])
        atlas_white = composite_on_white(atlas_im)
    except Exception:
        return []

    page_figs = []
    imgs = soup.find_all("img")

    for idx, img in enumerate(imgs):
        style = img.get("style", "")
        clip_m = re.search(
            r'clip:\s*rect\(\s*([\d\.]+)px[,\s]+([\d\.]+)px[,\s]+([\d\.]+)px[,\s]+([\d\.]+)px\s*\)',
            style
        )
        if not clip_m:
            continue

        c_top, c_right, c_bottom, c_left = [int(float(x)) for x in clip_m.groups()]
        cw = c_right - c_left
        ch = c_bottom - c_top

        top_m = re.search(r'(?:^|;\s*)top:\s*(-?[\d\.]+)px', style)
        elem_top = float(top_m.group(1)) if top_m else 0.0
        abs_top = elem_top + c_top
        left_m = re.search(r'(?:^|;\s*)left:\s*(-?[\d\.]+)px', style)
        elem_left = float(left_m.group(1)) if left_m else 0.0
        abs_left = elem_left + c_left

        # 1. Supresión de cabeceras superiores repetitivas
        if abs_top < 90 and cw > 650:
            continue

        # 2. Supresión de iconos y glifos diminutos
        if cw < 120 or ch < 35:
            continue

        # Validar límites de recorte en el atlas
        if c_right > atlas_white.width or c_bottom > atlas_white.height:
            continue

        crop_raw = atlas_white.crop((c_left, c_top, c_right, c_bottom))
        stat = ImageStat.Stat(crop_raw.convert("L"))
        if stat.stddev[0] < 15:
            continue

        cards = detectar_tarjetas_ui(crop_raw)
        for (bx1, by1, bx2, by2) in cards:
            bw = bx2 - bx1
            bh = by2 - by1
            if bw >= 120 and bh >= 35:
                final_crop = crop_raw.crop((bx1, by1, bx2, by2))
                f_stat = ImageStat.Stat(final_crop.convert("L"))
                if f_stat.stddev[0] >= 16:
                    fig_idx = len(page_figs) + 1
                    fname = f"fig_p{p_num:04d}_{fig_idx}.png"
                    fpath = figuras_out_dir / fname
                    final_crop.save(fpath, format="PNG", optimize=True)

                    page_figs.append({
                        "id": f"fig_{p_num:04d}_{fig_idx}",
                        "archivo": f"figuras/{fname}",
                        "archivo_absoluto": str(fpath.resolve()),
                        "ancho": bw,
                        "alto": bh,
                        "posicion_top_px": int(abs_top + by1),
                        "posicion_left_px": int(abs_left + bx1)
                    })

    return page_figs


def main():
    args = parse_arguments()

    console.print(Panel(
        f"[bold cyan]Destino Extracción (Output):[/bold cyan] {args.origen.resolve()}\n"
        f"[bold cyan]Rango a procesar:[/bold cyan] {f'Página {args.pagina}' if args.pagina else f'Páginas {args.desde} a {args.hasta}'}\n"
        f"[bold cyan]Copia espejo en reporte:[/bold cyan] {'Activada' if args.mirror_reporte else 'Desactivada'}",
        title="[bold green]Extractor Refinado de Figuras y Diagramas Scribd[/bold green]",
        border_style="green"
    ))

    # 1. Localizar Insumo
    try:
        html_file, files_dir = localizar_insumo(args.insumo)
        console.print(f"  [green][OK][/green] Insumo HTML: [dim]{html_file.name}[/dim]")
        if files_dir:
            console.print(f"  [green][OK][/green] Recursos _files: [dim]{files_dir.name}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error al localizar insumo:[/bold red] {e}")
        sys.exit(1)

    # 2. Cargar hashes
    doc_hash, page_hashes = cargar_mapa_hashes(html_file)
    console.print(f"  [green][OK][/green] Total páginas catalogadas en insumo: [bold]{len(page_hashes)}[/bold]")

    # 3. Preparar directorios de salida en output/
    figuras_dir = args.origen / "figuras"
    figuras_dir.mkdir(parents=True, exist_ok=True)
    json_salida = args.origen / "figuras_paginas.json"

    # Preparar espejo en reporte/ si está activo
    reporte_dir = Path("reporte/goanywhere_mft_user_guide_7_7_0")
    reporte_fig_dir = reporte_dir / "figuras"
    if args.mirror_reporte and reporte_dir.is_dir():
        reporte_fig_dir.mkdir(parents=True, exist_ok=True)

    # Determinar páginas objetivo
    if args.pagina:
        paginas_objetivo = [args.pagina]
    else:
        paginas_objetivo = [p for p in range(args.desde, args.hasta + 1)]

    # Si no se fuerzan TOC, excluir páginas < 39 (TOC son tablas de líneas punteadas)
    if not args.forzar_toc and not args.pagina:
        paginas_objetivo = [p for p in paginas_objetivo if p >= 39]

    console.print(f"  [green][OK][/green] Páginas a inspeccionar: [bold]{len(paginas_objetivo)}[/bold]")

    # 4. Cargar catálogo existente si ya existe para fusión incremental
    catalogo = {"total_figuras": 0, "paginas": {}}
    if json_salida.is_file():
        try:
            catalogo = json.loads(json_salida.read_text(encoding="utf-8"))
        except Exception:
            pass

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0",
        "Referer": "https://www.scribd.com/"
    })

    console.print("\n[bold yellow]Extrayendo y recortando figuras de alta fidelidad...[/bold yellow]")

    resumen_extraccion = {}

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Procesando...", total=len(paginas_objetivo))

        for p_num in paginas_objetivo:
            p_hash = page_hashes.get(p_num)
            if not p_hash:
                progress.advance(task)
                continue

            figs = procesar_pagina_figuras(
                p_num=p_num,
                p_hash=p_hash,
                doc_hash=doc_hash,
                session=session,
                files_dir=files_dir,
                figuras_out_dir=figuras_dir
            )

            if figs:
                catalogo["paginas"][str(p_num)] = figs
                resumen_extraccion[p_num] = figs
                # Sincronizar espejo si está activo
                if args.mirror_reporte and reporte_fig_dir.is_dir():
                    for f_item in figs:
                        src_f = Path(f_item["archivo_absoluto"])
                        dst_f = reporte_fig_dir / src_f.name
                        dst_f.write_bytes(src_f.read_bytes())
            elif str(p_num) in catalogo["paginas"]:
                # Si una página ya no contiene figuras válidas, eliminarla del catálogo
                del catalogo["paginas"][str(p_num)]

            progress.advance(task)

    # Actualizar contador total
    total_figs = sum(len(v) for v in catalogo["paginas"].values())
    catalogo["total_figuras"] = total_figs

    # Guardar figuras_paginas.json en output/
    with open(json_salida, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)

    # Espejo de json en reporte/
    if args.mirror_reporte and reporte_dir.is_dir():
        with open(reporte_dir / "figuras_paginas.json", "w", encoding="utf-8") as f:
            json.dump(catalogo, f, ensure_ascii=False, indent=2)

    console.print(f"\n[green][OK] Catálogo consolidado guardado en:[/green] [bold cyan]{json_salida}[/bold cyan]")
    console.print(f"[green][OK] Total figuras almacenadas en el catálogo:[/green] [bold]{total_figs}[/bold]")

    # 5. Generar Tabla Resumen
    if resumen_extraccion:
        table = Table(title=f"Resumen de Figuras Validadas (Páginas {args.desde} a {args.hasta})", border_style="cyan")
        table.add_column("Pág.", justify="center", style="bold")
        table.add_column("Cant.", justify="center")
        table.add_column("Detalle de Figuras (Ancho x Alto -> Archivo)", style="dim")

        for p_num in sorted(resumen_extraccion.keys()):
            figs = resumen_extraccion[p_num]
            detalles = []
            for f in figs:
                detalles.append(f"{f['ancho']}x{f['alto']} -> {Path(f['archivo']).name}")
            table.add_row(
                str(p_num),
                str(len(figs)),
                "; ".join(detalles)
            )
        console.print(table)
    else:
        console.print("[yellow]No se detectaron nuevas figuras en el rango especificado.[/yellow]")


if __name__ == "__main__":
    main()
