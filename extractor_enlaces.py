"""
extractor_enlaces.py - Extractor quirúrgico de enlaces internos y referencias cruzadas.

Extrae de forma desacoplada todos los enlaces internos (<a class="ll"> y texto teal #006a56)
desde los JSONP de Scribd, resolviendo sus páginas de destino reales y generando
el catálogo 'enlaces_internos.json' sin modificar paginas.json ni el avance actual.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

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
log = logging.getLogger("extractor_enlaces")


def cargar_doc_hashes(insumo_dir: Path) -> tuple[str, dict[int, str]]:
    """Descubre el doc_hash y mapa de hashes de páginas desde el archivo de insumo."""
    html_files = list(insumo_dir.glob("*.html")) if insumo_dir.is_dir() else ([insumo_dir] if insumo_dir.is_file() else [])
    if not html_files:
        return "2v8yixh6bkejepzg", {}

    target = html_files[0]
    raw = target.read_text(encoding="utf-8", errors="ignore")
    doc_hash = ""
    page_hashes: dict[int, str] = {}
    matches = re.findall(r'scribdassets\.com/([^/]+)/pages/(\d+)-([a-f0-9]+)\.jsonp', raw)
    for m_hash, m_num, m_phash in matches:
        if not doc_hash:
            doc_hash = m_hash
        page_hashes[int(m_num)] = m_phash

    return doc_hash or "2v8yixh6bkejepzg", page_hashes


def _extraer_enlaces_de_html(html_page_str: str, num_pagina: int) -> list[dict[str, Any]]:
    """Parsea el HTML de la página en Scribd e identifica los enlaces cruzados con su destino."""
    soup = BeautifulSoup(html_page_str, "html.parser")
    
    # 1. Recolectar anchors <a> de Scribd
    anchors_info = []
    for a in soup.find_all("a"):
        orig = a.get("orig", "")
        dest_str = ""
        dest_num = None
        if orig:
            try:
                dest_str = base64.b64decode(orig).decode(errors="ignore")
                m = re.search(r'(\d+)', dest_str)
                if m:
                    dest_num = int(m.group(1))
            except Exception:
                pass

        st = a.get("style", "")
        top_px = None
        m_top = re.search(r'top:\s*(\d+)px', st)
        if m_top:
            top_px = int(m_top.group(1))

        txt = a.get_text().strip()
        anchors_info.append({
            "dest_str": dest_str,
            "dest_pagina": dest_num,
            "top_px": top_px,
            "texto_a": txt
        })

    # 2. Recolectar textos con color teal (#006a56)
    # En Scribd el texto estilizado está escalado aproximadamente a 5x en coordenadas
    teals_info = []
    for s in soup.find_all(True):
        st = s.get("style", "")
        if "006a56" in st.lower():
            txt = s.get_text().replace("\ue000", " ").strip()
            # Unir glifos separados
            txt = re.sub(r'\s+', ' ', txt)
            if not txt:
                continue
            m_top = re.search(r'top:\s*(\d+)px', st)
            top_px = int(m_top.group(1)) if m_top else 0
            teals_info.append({
                "texto": txt,
                "top_px": top_px,
                "approx_a_top": round(top_px / 5.0)
            })

    # Unificar fragmentos adyacentes de texto teal en la misma línea
    teals_agrupados = []
    for t in teals_info:
        if teals_agrupados and abs(teals_agrupados[-1]["top_px"] - t["top_px"]) < 10:
            teals_agrupados[-1]["texto"] += t["texto"]
        else:
            teals_agrupados.append(dict(t))

    enlaces_resueltos: list[dict[str, Any]] = []

    # 3. Casar anchors con teals por proximidad vertical o texto
    for teal in teals_agrupados:
        txt_teal = teal["texto"].strip()
        candidatos = [
            a for a in anchors_info
            if a["dest_pagina"] and a["dest_pagina"] != num_pagina
        ]
        
        mejor_anchor = None
        menor_diff = 999999
        for a in candidatos:
            if a["top_px"] is not None:
                diff = abs(a["top_px"] - teal["approx_a_top"])
                if diff < menor_diff and diff < 30:  # Umbral de tolerancia geométrica
                    menor_diff = diff
                    mejor_anchor = a
            elif a["texto_a"] and a["texto_a"] in txt_teal:
                mejor_anchor = a
                break

        if mejor_anchor and mejor_anchor["dest_pagina"]:
            enlaces_resueltos.append({
                "texto": txt_teal,
                "pagina_destino": mejor_anchor["dest_pagina"],
                "tipo": "interno",
                "destino_ref": f"#page-{mejor_anchor['dest_pagina']}"
            })

    # 4. Incluir también anchors directos que tengan texto propio si no fueron casados
    for a in anchors_info:
        if a["dest_pagina"] and a["texto_a"] and len(a["texto_a"]) > 2:
            if not any(e["pagina_destino"] == a["dest_pagina"] for e in enlaces_resueltos):
                enlaces_resueltos.append({
                    "texto": a["texto_a"],
                    "pagina_destino": a["dest_pagina"],
                    "tipo": "interno",
                    "destino_ref": f"#page-{a['dest_pagina']}"
                })

    return enlaces_resueltos


def extraer_enlaces_documento(
    origen_reporte: Path,
    insumo_dir: Path,
    max_workers: int = 10,
    limite: int | None = None
) -> Path:
    """Ejecuta la extracción paralela y genera enlaces_internos.json."""
    doc_hash, page_hashes = cargar_doc_hashes(insumo_dir)
    log.info("Iniciando extracción de enlaces internos... (doc_hash: %s, %d páginas)", doc_hash, len(page_hashes))
    
    paginas_a_procesar = sorted(page_hashes.keys())
    if limite:
        paginas_a_procesar = paginas_a_procesar[:limite]

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.scribd.com/"
    })

    resultados: dict[str, list[dict[str, Any]]] = {}
    total_enlaces = 0
    t0 = time.time()

    def _procesar_pagina(num: int) -> tuple[int, list[dict[str, Any]]]:
        phash = page_hashes[num]
        url = f"https://html.scribdassets.com/{doc_hash}/pages/{num}-{phash}.jsonp"
        try:
            r = session.get(url, timeout=12)
            if r.status_code == 200:
                m = re.search(r'callback\((.*)\)', r.text, re.DOTALL)
                if m:
                    data = json.loads(m.group(1))
                    html = data[0] if isinstance(data, list) else str(data)
                    links = _extraer_enlaces_de_html(html, num)
                    return num, links
        except Exception:
            pass
        return num, []

    completadas = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_procesar_pagina, num): num for num in paginas_a_procesar}
        for future in as_completed(futures):
            num, links = future.result()
            completadas += 1
            if links:
                resultados[str(num)] = links
                total_enlaces += len(links)
            if completadas % 250 == 0 or completadas == len(paginas_a_procesar):
                log.info("Progreso: %d/%d páginas auditadas (%d enlaces detectados)",
                         completadas, len(paginas_a_procesar), total_enlaces)

    dt = time.time() - t0
    salida_json = origen_reporte / "enlaces_internos.json"
    
    payload = {
        "documento": "GoAnywhere MFT User Guide 7.7.0",
        "total_paginas_con_enlaces": len(resultados),
        "total_enlaces": total_enlaces,
        "tiempo_extraccion_segundos": round(dt, 2),
        "paginas": resultados
    }

    with open(salida_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    log.info("Catálogo generado en %.2f s: %s (%d páginas con enlaces, %d enlaces en total)",
             dt, salida_json, len(resultados), total_enlaces)
    return salida_json


def main():
    parser = argparse.ArgumentParser(description="Extractor de enlaces internos cruzados del manual Scribd")
    parser.add_argument("--origen", default="reporte/goanywhere_mft_user_guide_7_7_0", help="Carpeta del reporte")
    parser.add_argument("--insumo", default="insumo", help="Carpeta del insumo HTML")
    parser.add_argument("--workers", type=int, default=15, help="Hilos paralelos de descarga")
    parser.add_argument("--limite", type=int, default=None, help="Límite de páginas a auditar (ej: para pruebas)")
    args = parser.parse_args()

    origen = Path(args.origen).resolve()
    insumo = Path(args.insumo).resolve()
    extraer_enlaces_documento(origen, insumo, max_workers=args.workers, limite=args.limite)


if __name__ == "__main__":
    main()
