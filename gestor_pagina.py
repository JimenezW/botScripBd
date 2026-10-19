"""
Gestor de Páginas Puntuales (Extractor, Compilador y Auditor Unipágina)

Permite re-extraer, inspeccionar, previsualizar e integrar páginas específicas
sin necesidad de re-procesar todo el catálogo de páginas (ideal para documentos 100+).

Uso:
    python gestor_pagina.py --pagina 43 --extraer
    python gestor_pagina.py --pagina 43 --preview
    python gestor_pagina.py --pagina 43 --ver-texto
    python gestor_pagina.py --pagina 43 --integrar
    python gestor_pagina.py --pagina 43 --auto
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Configurar consola UTF-8 en Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("gestor_pagina")


def _cargar_doc_hashes(insumo_dir: Path) -> tuple[str, dict[int, str]]:
    """Descubre el doc_hash y el mapa de hashes de páginas desde el archivo de insumo."""
    html_files = list(insumo_dir.glob("*.html")) if insumo_dir.is_dir() else ([insumo_dir] if insumo_dir.is_file() else [])
    if not html_files:
        return "2v8yixh6bkejepzg", {}

    target = html_files[0]
    try:
        raw = target.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "2v8yixh6bkejepzg", {}

    doc_hash = ""
    page_hashes: dict[int, str] = {}
    matches = re.findall(r'scribdassets\.com/([^/]+)/pages/(\d+)-([a-f0-9]+)\.jsonp', raw)
    for m_hash, m_num, m_phash in matches:
        if not doc_hash:
            doc_hash = m_hash
        page_hashes[int(m_num)] = m_phash

    return doc_hash or "2v8yixh6bkejepzg", page_hashes


def extraer_pagina_puntual(
    num_pagina: int,
    origen_reporte: Path,
    insumo_dir: Path,
    doc_hash_fijo: Optional[str] = None
) -> bool:
    """Descarga e hidrata la página puntual con todas sus capas de texto y actualiza paginas.json."""
    doc_hash, page_hashes = _cargar_doc_hashes(insumo_dir)
    if doc_hash_fijo:
        doc_hash = doc_hash_fijo

    p_hash = page_hashes.get(num_pagina)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.scribd.com/"
    })

    log.info("Extrayendo página %d...", num_pagina)

    # Si no tenemos el hash específico registrado en el HTML estático, intentar consultar o pedir
    url_jsonp = None
    if p_hash:
        url_jsonp = f"https://html.scribdassets.com/{doc_hash}/pages/{num_pagina}-{p_hash}.jsonp"
    else:
        # Intentar consultar si existe en el cache o en el insumo
        log.warning("Hash específico no catalogado en insumo para la página %d. Buscando alternativas...", num_pagina)

    resp_text = None
    if url_jsonp:
        try:
            resp = session.get(url_jsonp, timeout=12)
            if resp.status_code == 200:
                resp_text = resp.text
        except Exception as e:
            log.error("Error al descargar JSONP de página %d: %s", num_pagina, e)

    if not resp_text:
        log.error("No se pudo obtener el payload JSONP para la página %d.", num_pagina)
        return False

    # Extraer contenido HTML empaquetado en el callback JSONP
    m = re.search(r'\["(.*)"\]', resp_text, re.DOTALL)
    if not m:
        log.error("Formato JSONP inválido para la página %d.", num_pagina)
        return False

    raw_html = (
        m.group(1)
        .replace(r'\"', '"')
        .replace(r"\'", "'")
        .replace(r"\n", "\n")
        .replace(r"\/", "/")
    )

    soup = BeautifulSoup(raw_html, "html.parser")

    # Extraer todas las capas de texto multi-capa
    text_lines = []
    text_layers = soup.find_all(class_=re.compile(r"text_layer"))
    for layer in text_layers:
        row_spans = layer.find_all("span", class_="a")
        if row_spans:
            for sp in row_spans:
                txt = " ".join(sp.get_text().split())
                if txt:
                    text_lines.append(txt)
        else:
            for sp in layer.find_all("span"):
                txt = " ".join(sp.get_text().split())
                if txt:
                    text_lines.append(txt)

    log.info("Líneas de texto extraídas para página %d: %d líneas (en %d capas)",
             num_pagina, len(text_lines), len(text_layers))

    # Actualizar en paginas.json (en origen_reporte y en output/ si existe)
    rutas_json = [origen_reporte / "paginas.json", Path("output/goanywhere_mft_user_guide_7_7_0/paginas.json")]
    for ruta in rutas_json:
        if not ruta.is_file():
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)
            paginas = data.get("paginas", [])
            encontrada = False
            for p in paginas:
                if p.get("numero_pagina") == num_pagina:
                    p["lineas_texto"] = text_lines
                    p["lineas_texto_count"] = len(text_lines)
                    p["texto_completo"] = "\n".join(text_lines)
                    encontrada = True
                    break
            if not encontrada:
                paginas.append({
                    "numero_pagina": num_pagina,
                    "imagen_relativa": f"imagenes/pagina_{num_pagina:04d}.png",
                    "imagen_absoluta": "",
                    "dimensiones": {"ancho": 1786, "alto": 2526},
                    "lineas_texto_count": len(text_lines),
                    "lineas_texto": text_lines,
                    "texto_completo": "\n".join(text_lines)
                })
                paginas.sort(key=lambda x: x.get("numero_pagina", 0))

            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log.info("paginas.json actualizado exitosamente en %s", ruta)
        except Exception as e:
            log.error("Error al actualizar %s: %s", ruta, e)

    return True


def compilar_preview_puntual(num_pagina: int, origen_reporte: Path) -> Path:
    """Compila aisladamente la página a preview_pagina_XXXX.html usando compilador.py."""
    import subprocess
    cmd = [
        sys.executable,
        "compilador.py",
        "--fase", "1",
        "--pagina", str(num_pagina),
        "--origen", str(origen_reporte)
    ]
    log.info("Compilando vista previa aislada para página %d...", num_pagina)
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    if res.returncode != 0:
        log.error("Fallo al compilar página puntual:\n%s", res.stderr)
        raise RuntimeError(f"compilador.py falló con código {res.returncode}")

    preview_path = origen_reporte / f"preview_pagina_{num_pagina:04d}.html"
    log.info("Vista previa generada exitosamente en %.2f s: %s", dt, preview_path)
    return preview_path


def integrar_documento_maestro(origen_reporte: Path) -> Path:
    """Recompila el documento maestro preview.html sincronizando todas las páginas."""
    import subprocess
    cmd = [
        sys.executable,
        "compilador.py",
        "--fase", "1",
        "--origen", str(origen_reporte)
    ]
    log.info("Sincronizando documento maestro preview.html...")
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    if res.returncode != 0:
        log.error("Fallo al compilar documento maestro:\n%s", res.stderr)
        raise RuntimeError(f"compilador.py falló con código {res.returncode}")

    maestro_path = origen_reporte / "preview.html"
    log.info("Documento maestro actualizado en %.2f s: %s", dt, maestro_path)
    return maestro_path


def ver_texto_pagina(num_pagina: int, origen_reporte: Path) -> None:
    """Muestra en consola las líneas de texto extraídas para la página solicitada."""
    ruta_json = origen_reporte / "paginas.json"
    if not ruta_json.is_file():
        log.error("No se encontró %s", ruta_json)
        return
    with open(ruta_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    p = next((x for x in data.get("paginas", []) if x.get("numero_pagina") == num_pagina), None)
    if not p:
        log.error("Página %d no encontrada en %s", num_pagina, ruta_json)
        return

    lineas = p.get("lineas_texto", [])
    print(f"\n{'='*70}")
    print(f" PÁGINA {num_pagina} · {len(lineas)} líneas de texto en catálogo")
    print(f"{'='*70}")
    for idx, l in enumerate(lineas):
        print(f"{idx:3d}: {l}")
    print(f"{'='*70}\n")


def extraer_figuras_pagina_gestor(num_pagina: int, origen: Path, insumo_dir: Path) -> None:
    """Extrae quirúrgicamente las figuras de una página puntual y actualiza el catálogo."""
    try:
        from extractor_figuras import extraer_figuras_pagina
        out_dir = Path("output/goanywhere_mft_user_guide_7_7_0")
        log.info("Iniciando extracción quirúrgica de figuras para la página %d...", num_pagina)
        figs = extraer_figuras_pagina(
            p_num=num_pagina,
            origen=out_dir,
            insumo_arg=insumo_dir,
            mirror_reporte=False
        )
        print(f"\n{'='*75}")
        print(f" FIGURAS EXTRAÍDAS · PÁGINA {num_pagina} ({len(figs)} figuras detectadas)")
        print(f"{'='*75}")
        if figs:
            for f in figs:
                print(f" [OK] {f['id']}: {f['ancho']}x{f['alto']} px en top={f['posicion_top_px']}px, left={f['posicion_left_px']}px")
                print(f"      Archivo: {f['archivo']}")
                print(f"      Ruta:    {f['archivo_absoluto']}")
        else:
            print(" [INFO] No se detectaron figuras o tarjetas UI cerradas en esta página.")
        print(f"{'='*75}\n")
    except Exception as e:
        log.error("Error al extraer figuras de la página %d: %s", num_pagina, e)


def limpiar_previews(origen: Path) -> int:
    """Elimina los archivos temporales preview_pagina_XXXX.html generados para pruebas individuales."""
    eliminados = 0
    for p in origen.glob("preview_pagina_*.html"):
        try:
            p.unlink()
            eliminados += 1
            log.info("Eliminado preview temporal: %s", p.name)
        except Exception as e:
            log.warning("No se pudo eliminar %s: %s", p.name, e)
    log.info("Limpieza completada: %d archivo(s) preview temporal(es) eliminado(s).", eliminados)
    return eliminados


def main():
    parser = argparse.ArgumentParser(
        description="Gestor y auditor de páginas individuales del Bot Scribd"
    )
    parser.add_argument("--pagina", type=int, default=None,
                        help="Número de página a procesar (ej: --pagina 43)")
    parser.add_argument("--origen", type=str, default="reporte/goanywhere_mft_user_guide_7_7_0",
                        help="Directorio del reporte técnico (defecto: reporte/goanywhere_mft_user_guide_7_7_0)")
    parser.add_argument("--insumo", type=str, default="insumo",
                        help="Directorio o archivo HTML de insumo local (defecto: insumo/)")
    parser.add_argument("--extraer", action="store_true",
                        help="Re-extrae la página puntual desde el JSONP oficial y actualiza paginas.json")
    parser.add_argument("--figuras", "--extraer-figuras", dest="extraer_figuras", action="store_true",
                        help="Extrae quirúrgicamente las figuras y diagramas de la página puntual y actualiza figuras_paginas.json")
    parser.add_argument("--preview", action="store_true",
                        help="Genera preview HTML aislado de la página puntual (preview_pagina_XXXX.html)")
    parser.add_argument("--ver-texto", action="store_true",
                        help="Muestra en consola las líneas de texto extraídas de la página")
    parser.add_argument("--integrar", action="store_true",
                        help="Recompila el documento maestro preview.html")
    parser.add_argument("--auto", action="store_true",
                        help="Flujo completo: previsualizar página puntual y sincronizar maestro")
    parser.add_argument("--limpiar-previews", action="store_true",
                        help="Elimina todos los archivos preview_pagina_*.html temporales de la carpeta de reporte")

    args = parser.parse_args()
    origen = Path(args.origen).resolve()
    insumo = Path(args.insumo).resolve()

    if args.limpiar_previews:
        limpiar_previews(origen)
        if not args.pagina:
            return

    pagina = args.pagina
    if not pagina and not args.integrar:
        parser.error("Debe indicar --pagina <N> o utilizar --limpiar-previews / --integrar.")

    # Si no se pasó ninguna acción específica, activar --preview por defecto
    if not any([args.extraer, args.extraer_figuras, args.preview, args.ver_texto, args.integrar, args.auto]):
        args.preview = True

    if (args.extraer or args.auto) and pagina:
        extraer_pagina_puntual(pagina, origen, insumo)

    if args.extraer_figuras and pagina:
        extraer_figuras_pagina_gestor(pagina, origen, insumo)

    if args.ver_texto and pagina:
        ver_texto_pagina(pagina, origen)

    if (args.preview or args.auto) and pagina:
        preview_p = compilar_preview_puntual(pagina, origen)
        print(f"\n[OK] Vista previa individual lista: file:///{preview_p.as_posix()}\n")

    if args.integrar or args.auto:
        maestro_p = integrar_documento_maestro(origen)
        ref_pagina = f"#page-{pagina}" if pagina else ""
        print(f"\n[OK] Documento maestro actualizado: file:///{maestro_p.as_posix()}{ref_pagina}\n")


if __name__ == "__main__":
    main()
