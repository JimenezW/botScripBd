#!/usr/bin/env python3
"""
compilador.py - Compilador de reportes técnicos estructurados (HTML + Jinja2 + WeasyPrint).

Flujo en DOS FASES desacopladas:

    Fase 1 (HTML)  Lee los insumos de la carpeta de extracción (--origen), normaliza
                   los datos, resuelve rutas relativas de imágenes/fuentes y renderiza
                   la plantilla Jinja2 en un 'preview.html' listo para el navegador
                   o Live Server.

    Fase 2 (PDF)   Toma el HTML generado (en esta corrida o en una anterior) y lo
                   compila a PDF con WeasyPrint, usando el directorio del HTML como
                   base_url para que las rutas relativas se resuelvan sin rutas rotas.

Esquemas de datos soportados (autodetectados por contenido):

    * datos.json    -> Esquema de reporte: {"meta", "resumen", "secciones": [{"titulo", "bloques"}]}
                       Bloques: parrafo | subtitulo | lista | tabla | codigo | figura | nota
    * paginas.json  -> Esquema de extracción botScribd: {"documento", "paginas": [...]}
                       Se adapta automáticamente al esquema de reporte.

Códigos de salida:
    0  OK
    1  Precondición no satisfecha (carpeta/archivo inexistente, JSON inválido, etc.)
    2  Argumentos de línea de comandos inválidos (argparse)
    3  Error de ejecución (plantilla, WeasyPrint, escritura de archivos)
  130  Interrumpido por el usuario
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
import textwrap
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote

# ════════════════════════════════════════════════════════════════════════════
# Configuración por defecto (editable aquí o vía variables de entorno)
# ════════════════════════════════════════════════════════════════════════════

DIR_SCRIPT = Path(__file__).resolve().parent

#: Carpeta de extracción por defecto. Se puede sobrescribir con COMPILADOR_ORIGEN.
_DEFECTO_REPORTE = "reporte/ejemplo_reporte" if (DIR_SCRIPT / "reporte" / "ejemplo_reporte").is_dir() else "ejemplo_reporte"
ORIGEN_POR_DEFECTO = os.environ.get("COMPILADOR_ORIGEN", _DEFECTO_REPORTE)
#: Plantilla Jinja2 por defecto. Se puede sobrescribir con COMPILADOR_PLANTILLA.
PLANTILLA_POR_DEFECTO = os.environ.get("COMPILADOR_PLANTILLA", str(DIR_SCRIPT / "plantilla.html"))

NOMBRE_HTML_PREVIEW = "preview.html"
NOMBRE_PDF_POR_DEFECTO = "reporte.pdf"
ARCHIVOS_DATOS = ("datos.json", "paginas.json")  # Orden de autodetección
CARPETA_FUENTES = "fuentes"
UMBRAL_PAGINAS_AVISO = 300

EXIT_OK, EXIT_PRECONDICION, EXIT_ERROR, EXIT_INTERRUMPIDO = 0, 1, 3, 130

EXTENSIONES_FUENTE = {".ttf": "truetype", ".otf": "opentype", ".woff": "woff", ".woff2": "woff2"}
PESOS_FUENTE = {
    "thin": 100, "hairline": 100, "extralight": 200, "ultralight": 200, "light": 300,
    "regular": 400, "normal": 400, "book": 400, "medium": 500, "semibold": 600,
    "demibold": 600, "bold": 700, "extrabold": 800, "ultrabold": 800, "black": 900, "heavy": 900,
}
ALINEACIONES = {
    "izquierda": "left", "izq": "left", "left": "left",
    "centro": "center", "centrado": "center", "center": "center",
    "derecha": "right", "der": "right", "right": "right",
}
NIVELES_NOTA = {
    "info": "Nota",
    "exito": "Recomendación",
    "advertencia": "Advertencia",
    "critico": "Crítico",
}
RE_LONGITUD_CSS = re.compile(r"^\d+(?:\.\d+)?(?:%|mm|cm|in|pt|px|em|rem)$")
RE_URL_ABSOLUTA = re.compile(r"^(?:[a-z][a-z0-9+.-]*:)?//|^(?:data|file|https?):", re.IGNORECASE)
RE_VERSION = re.compile(r"\b\d+(?:\.\d+){1,3}\b")

log = logging.getLogger("compilador")


# ════════════════════════════════════════════════════════════════════════════
# Excepciones de dominio
# ════════════════════════════════════════════════════════════════════════════

class CompiladorError(Exception):
    """Error controlado del compilador (se reporta sin traceback)."""
    exit_code = EXIT_ERROR


class PrecondicionError(CompiladorError):
    """Una precondición de entrada no se cumple (rutas, archivos, formato de datos)."""
    exit_code = EXIT_PRECONDICION


# ════════════════════════════════════════════════════════════════════════════
# Logging y trazabilidad
# ════════════════════════════════════════════════════════════════════════════

class _FiltroPrefijo(logging.Filter):
    """Antepone el nombre del logger cuando el mensaje no proviene del compilador."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.prefijo = "" if record.name.startswith("compilador") else f"[{record.name}] "
        return True


def configurar_logging(verbose: bool) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_FiltroPrefijo())
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(prefijo)s%(message)s", datefmt="%H:%M:%S"
    ))
    raiz = logging.getLogger()
    raiz.handlers[:] = [handler]
    raiz.setLevel(logging.DEBUG if verbose else logging.INFO)
    # Silenciar librerías ruidosas
    for ruidoso in ("fontTools", "PIL"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)


@contextmanager
def etapa(titulo: str) -> Iterator[None]:
    """Delimita una fase en consola con marcas de inicio/fin y tiempo transcurrido."""
    log.info("=" * 72)
    log.info("INICIO  >> %s", titulo)
    log.info("-" * 72)
    t0 = time.perf_counter()
    try:
        yield
    except BaseException:
        log.error("FALLO   >> %s (%.2f s)", titulo, time.perf_counter() - t0)
        raise
    log.info("FIN     >> %s (%.2f s)", titulo, time.perf_counter() - t0)


def _tamano_legible(n_bytes: int) -> str:
    valor = float(n_bytes)
    for unidad in ("B", "KB", "MB", "GB"):
        if valor < 1024 or unidad == "GB":
            return f"{valor:.1f} {unidad}" if unidad != "B" else f"{int(valor)} B"
        valor /= 1024
    return f"{valor:.1f} GB"


# ════════════════════════════════════════════════════════════════════════════
# Resolución de rutas
# ════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Rutas:
    origen: Path
    html: Path
    pdf: Path
    plantilla: Path


def _resolver_salida(salida: str | None, origen: Path) -> Path:
    """
    --salida acepta un *nombre* (se ubica dentro de --origen) o una *ruta*
    (relativa al directorio actual o absoluta). Se garantiza la extensión .pdf.
    """
    if not salida:
        return origen / NOMBRE_PDF_POR_DEFECTO
    es_ruta = any(sep in salida for sep in ("/", "\\")) or Path(salida).is_absolute()
    destino = Path(salida).expanduser()
    if destino.suffix.lower() != ".pdf":
        destino = destino.with_name(destino.name + ".pdf")
    return (destino if es_ruta else origen / destino).resolve()


def resolver_rutas(args: argparse.Namespace) -> Rutas:
    origen = Path(args.origen).expanduser().resolve()
    if args.html:
        html = Path(args.html).expanduser().resolve()
    elif getattr(args, "pagina", None):
        html = origen / f"preview_pagina_{args.pagina:04d}.html"
    else:
        html = origen / NOMBRE_HTML_PREVIEW
    return Rutas(
        origen=origen,
        html=html,
        pdf=_resolver_salida(args.salida, origen),
        plantilla=Path(args.plantilla).expanduser().resolve(),
    )


class ResolutorRecursos:
    """
    Traduce rutas declaradas *relativas a la carpeta de origen* en rutas
    *relativas al HTML generado*. Así el mismo HTML funciona en:
      - el navegador / Live Server (rutas relativas, sin 'C:\\...'),
      - WeasyPrint (base_url = carpeta del HTML).
    """

    def __init__(self, origen: Path, dir_html: Path):
        self.origen = origen
        self.dir_html = dir_html
        self.faltantes: list[str] = []
        self.resueltos = 0

    def ruta_absoluta(self, ruta: str) -> Path:
        candidato = Path(ruta.replace("\\", "/")) if not Path(ruta).is_absolute() else Path(ruta)
        return (candidato if candidato.is_absolute() else self.origen / candidato).resolve()

    def resolver(self, ruta: str) -> tuple[str, bool]:
        """Retorna (url_relativa_al_html, existe)."""
        if RE_URL_ABSOLUTA.match(ruta):
            return ruta, True  # URL remota o data URI: se respeta tal cual
        absoluta = self.ruta_absoluta(ruta)
        existe = absoluta.is_file()
        if existe:
            self.resueltos += 1
        else:
            self.faltantes.append(ruta)
            log.warning("Recurso no encontrado: '%s' (buscado en %s)", ruta, absoluta)
        try:
            relativa = Path(os.path.relpath(absoluta, self.dir_html)).as_posix()
        except ValueError:
            # Windows: HTML y recurso en unidades distintas -> no existe ruta relativa posible
            log.debug("Unidades distintas, se usa URI absoluta para '%s'", ruta)
            return absoluta.as_uri(), existe
        return quote(relativa, safe="/._-~"), existe


# ════════════════════════════════════════════════════════════════════════════
# Utilidades de texto / filtros Jinja2
# ════════════════════════════════════════════════════════════════════════════

def _txt(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


def _formatear_fecha(valor: Any) -> str:
    texto = _txt(valor)
    if not texto:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return texto  # Formato libre (p. ej. "Octubre 2026")


def _parrafos(valor: Any) -> list[str]:
    if isinstance(valor, list):
        return [_txt(p) for p in valor if _txt(p)]
    return [p.strip() for p in re.split(r"\n\s*\n", _txt(valor)) if p.strip()]


def filtro_inline(texto: Any):
    """Marcado inline seguro: escapa HTML y soporta **negrita** y `código`."""
    from markupsafe import Markup, escape

    seguro = str(escape(_txt(texto)))
    fragmentos: list[str] = []

    def _proteger(m: re.Match) -> str:
        fragmentos.append(m.group(1))
        return f"\x00{len(fragmentos) - 1}\x00"

    seguro = re.sub(r"`([^`]+)`", _proteger, seguro)
    seguro = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", seguro)
    seguro = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{fragmentos[int(m.group(1))]}</code>", seguro)
    return Markup(seguro)


def filtro_css_string(valor: Any):
    """Convierte un valor en literal de cadena CSS seguro para usar dentro de <style>."""
    from markupsafe import Markup

    s = (_txt(valor).replace("\\", "\\\\").replace('"', '\\"')
         .replace("\n", " ").replace("<", "\\3C ").replace(">", "\\3E "))
    return Markup(f'"{s}"')


# ════════════════════════════════════════════════════════════════════════════
# Desfragmentación léxica de palabras (reparación de espaciado por kerning de Scribd)
# ════════════════════════════════════════════════════════════════════════════

RE_PATRONES_DESFRAGMENTACION: list[tuple[re.Pattern, str]] = [
    # 3 partes (letras iniciales + raíz + terminación)
    (re.compile(r'\bA\s+ctio\s*n\b', re.I), 'Action'),
    (re.compile(r'\bA\s+ctio\s*ns\b', re.I), 'Actions'),
    (re.compile(r'\bA\s+dmi\s*n\b', re.I), 'Admin'),
    (re.compile(r'\bA\s+nyw\s*here\b', re.I), 'Anywhere'),
    (re.compile(r'\bE\s+lem\s*ent\b', re.I), 'Element'),
    (re.compile(r'\bE\s+lem\s*ents\b', re.I), 'Elements'),
    (re.compile(r'\bE\s+xa\s*mple\b', re.I), 'Example'),
    (re.compile(r'\bEle\s+me\s*nt\b', re.I), 'Element'),
    (re.compile(r'\bEle\s+me\s*nts\b', re.I), 'Elements'),
    (re.compile(r'\bElem\s+e\s*nt\b', re.I), 'Element'),
    (re.compile(r'\bElem\s+e\s*nts\b', re.I), 'Elements'),
    (re.compile(r'\bExec\s+utio\s*n\b', re.I), 'Execution'),
    (re.compile(r'\bExem\s+ption\s*s\b', re.I), 'Exemptions'),
    (re.compile(r'\bF\s+aile\s*d\b', re.I), 'Failed'),
    (re.compile(r'\bFe\s+atur\s*es\b', re.I), 'Features'),
    (re.compile(r'\bCom\s+plet\s*ed\b', re.I), 'Completed'),
    (re.compile(r'\bConf\s+igur\s*e\b', re.I), 'Configure'),
    (re.compile(r'\bConf\s+igur\s*ing\b', re.I), 'Configuring'),
    (re.compile(r'\bData\s+bas\s*e\b', re.I), 'Database'),
    (re.compile(r'\bDa\s+taba\s*se\b', re.I), 'Database'),
    (re.compile(r'\bC\s+reatin\s*g\b', re.I), 'Creating'),
    (re.compile(r'\bCh\s+oosi\s*ng\b', re.I), 'Choosing'),
    (re.compile(r'\bCert\s+ifica\s*tes\b', re.I), 'Certificates'),

    # Prefijos de 2 letras partidos
    (re.compile(r'\bCo\s+nnector\b', re.I), 'Connector'),
    (re.compile(r'\bCo\s+nnectors\b', re.I), 'Connectors'),
    (re.compile(r'\bAc\s+tive\b', re.I), 'Active'),
    (re.compile(r'\bAd\s+min\b', re.I), 'Admin'),
    (re.compile(r'\bAg\s+ent\b', re.I), 'Agent'),
    (re.compile(r'\bAg\s+ents\b', re.I), 'Agents'),
    (re.compile(r'\bAg\s+reements\b', re.I), 'Agreements'),
    (re.compile(r'\bCe\s+rtificate\b', re.I), 'Certificate'),
    (re.compile(r'\bCe\s+rtificates\b', re.I), 'Certificates'),
    (re.compile(r'\bCh\s+annels\b', re.I), 'Channels'),
    (re.compile(r'\bCl\s+uster\b', re.I), 'Cluster'),
    (re.compile(r'\bCo\s+nfig\b', re.I), 'Config'),
    (re.compile(r'\bCo\s+nfigure\b', re.I), 'Configure'),
    (re.compile(r'\bCo\s+nfiguring\b', re.I), 'Configuring'),
    (re.compile(r'\bCo\s+ntact\b', re.I), 'Contact'),
    (re.compile(r'\bDa\s+ta\b', re.I), 'Data'),
    (re.compile(r'\bDe\s+fine\b', re.I), 'Define'),
    (re.compile(r'\bDe\s+tails\b', re.I), 'Details'),
    (re.compile(r'\bDo\s+main\b', re.I), 'Domain'),
    (re.compile(r'\bDo\s+mains\b', re.I), 'Domains'),
    (re.compile(r'\bEm\s+ail\b', re.I), 'Email'),
    (re.compile(r'\bEnc\s+rypt\b', re.I), 'Encrypt'),
    (re.compile(r'\bFe\s+ature\b', re.I), 'Feature'),
    (re.compile(r'\bFe\s+atures\b', re.I), 'Features'),
    (re.compile(r'\bFo\s+lders\b', re.I), 'Folders'),
    (re.compile(r'\bGr\s+oups\b', re.I), 'Groups'),
    (re.compile(r'\bHi\s+story\b', re.I), 'History'),
    (re.compile(r'\bLo\s+gin\b', re.I), 'Login'),
    (re.compile(r'\bLo\s+g\b', re.I), 'Log'),
    (re.compile(r'\bLo\s+gs\b', re.I), 'Logs'),
    (re.compile(r'\bMo\s+nitors\b', re.I), 'Monitors'),
    (re.compile(r'\bPa\s+ssword\b', re.I), 'Password'),
    (re.compile(r'\bPa\s+sswords\b', re.I), 'Passwords'),
    (re.compile(r'\bPr\s+oject\b', re.I), 'Project'),
    (re.compile(r'\bPr\s+ojects\b', re.I), 'Projects'),
    (re.compile(r'\bPro\s+ject\b', re.I), 'Project'),
    (re.compile(r'\bPro\s+jects\b', re.I), 'Projects'),
    (re.compile(r'\bRe\s+source\b', re.I), 'Resource'),
    (re.compile(r'\bRe\s+sources\b', re.I), 'Resources'),
    (re.compile(r'\bSe\s+rver\b', re.I), 'Server'),
    (re.compile(r'\bSe\s+rvers\b', re.I), 'Servers'),
    (re.compile(r'\bSe\s+rvice\b', re.I), 'Service'),
    (re.compile(r'\bSe\s+rvices\b', re.I), 'Services'),
    (re.compile(r'\bSy\s+stem\b', re.I), 'System'),
    (re.compile(r'\bTr\s+igger\b', re.I), 'Trigger'),
    (re.compile(r'\bTr\s+iggers\b', re.I), 'Triggers'),
    (re.compile(r'\bVa\s+riable\b', re.I), 'Variable'),
    (re.compile(r'\bVa\s+riables\b', re.I), 'Variables'),
    (re.compile(r'\bWo\s+rkflow\b', re.I), 'Workflow'),
    (re.compile(r'\bWo\s+rkflows\b', re.I), 'Workflows'),

    # Mayúscula inicial aislada antes de término técnico
    (re.compile(r'\bA\s+gent\b', re.I), 'Agent'),
    (re.compile(r'\bA\s+gents\b', re.I), 'Agents'),
    (re.compile(r'\bA\s+lgorithms\b', re.I), 'Algorithms'),
    (re.compile(r'\bA\s+ctivity\b', re.I), 'Activity'),
    (re.compile(r'\bB\s+ased\b', re.I), 'Based'),
    (re.compile(r'\bB\s+uffer\b', re.I), 'Buffer'),
    (re.compile(r'\bC\s+ertificate\b', re.I), 'Certificate'),
    (re.compile(r'\bC\s+ertificates\b', re.I), 'Certificates'),
    (re.compile(r'\bC\s+hange\b', re.I), 'Change'),
    (re.compile(r'\bC\s+hecksum\b', re.I), 'Checksum'),
    (re.compile(r'\bC\s+onfiguration\b', re.I), 'Configuration'),
    (re.compile(r'\bC\s+onfiguring\b', re.I), 'Configuring'),
    (re.compile(r'\bC\s+onsiderations\b', re.I), 'Considerations'),
    (re.compile(r'\bD\s+ashboard\b', re.I), 'Dashboard'),
    (re.compile(r'\bD\s+ecrypted\b', re.I), 'Decrypted'),
    (re.compile(r'\bE\s+dit\b', re.I), 'Edit'),
    (re.compile(r'\bE\s+lse\b', re.I), 'Else'),
    (re.compile(r'\bE\s+rror\b', re.I), 'Error'),
    (re.compile(r'\bE\s+rrors\b', re.I), 'Errors'),
    (re.compile(r'\bE\s+xample\b', re.I), 'Example'),
    (re.compile(r'\bE\s+xamples\b', re.I), 'Examples'),
    (re.compile(r'\bF\s+ile\b', re.I), 'File'),
    (re.compile(r'\bF\s+iles\b', re.I), 'Files'),
    (re.compile(r'\bF\s+older\b', re.I), 'Folder'),
    (re.compile(r'\bF\s+olders\b', re.I), 'Folders'),
    (re.compile(r'\bF\s+or\b', re.I), 'For'),
    (re.compile(r'\bF\s+or-\s*Each\b', re.I), 'For-Each'),
    (re.compile(r'\bG\s+roup\b', re.I), 'Group'),
    (re.compile(r'\bG\s+roups\b', re.I), 'Groups'),
    (re.compile(r'\bL\s+ogin\b', re.I), 'Login'),
    (re.compile(r'\bM\s+anage\b', re.I), 'Manage'),
    (re.compile(r'\bM\s+anagement\b', re.I), 'Management'),
    (re.compile(r'\bM\s+anager\b', re.I), 'Manager'),
    (re.compile(r'\bM\s+anually\b', re.I), 'Manually'),
    (re.compile(r'\bM\s+aster\b', re.I), 'Master'),
    (re.compile(r'\bM\s+odule\b', re.I), 'Module'),
    (re.compile(r'\bM\s+odules\b', re.I), 'Modules'),
    (re.compile(r'\bN\s+ode\b', re.I), 'Node'),
    (re.compile(r'\bN\s+odes\b', re.I), 'Nodes'),
    (re.compile(r'\bO\s+ptions\b', re.I), 'Options'),
    (re.compile(r'\bO\s+utline\b', re.I), 'Outline'),
    (re.compile(r'\bO\s+verview\b', re.I), 'Overview'),
    (re.compile(r'\bP\s+arty\b', re.I), 'Party'),
    (re.compile(r'\bP\s+ermissions\b', re.I), 'Permissions'),
    (re.compile(r'\bP\s+roject\b', re.I), 'Project'),
    (re.compile(r'\bP\s+rojects\b', re.I), 'Projects'),
    (re.compile(r'\bP\s+rovider\b', re.I), 'Provider'),
    (re.compile(r'\bP\s+roxy\b', re.I), 'Proxy'),
    (re.compile(r'\bP\s+ull\b', re.I), 'Pull'),
    (re.compile(r'\bQ\s+uick\b', re.I), 'Quick'),
    (re.compile(r'\bR\s+ead\b', re.I), 'Read'),
    (re.compile(r'\bR\s+eceipt\b', re.I), 'Receipt'),
    (re.compile(r'\bR\s+ecovery\b', re.I), 'Recovery'),
    (re.compile(r'\bR\s+esponse\b', re.I), 'Response'),
    (re.compile(r'\bS\s+chedule\b', re.I), 'Schedule'),
    (re.compile(r'\bS\s+chedules\b', re.I), 'Schedules'),
    (re.compile(r'\bS\s+cheduler\b', re.I), 'Scheduler'),
    (re.compile(r'\bS\s+ervice\b', re.I), 'Service'),
    (re.compile(r'\bS\s+ervices\b', re.I), 'Services'),
    (re.compile(r'\bS\s+ettings\b', re.I), 'Settings'),
    (re.compile(r'\bS\s+ize\b', re.I), 'Size'),
    (re.compile(r'\bT\s+ask\b', re.I), 'Task'),
    (re.compile(r'\bT\s+asks\b', re.I), 'Tasks'),
    (re.compile(r'\bT\s+emplate\b', re.I), 'Template'),
    (re.compile(r'\bT\s+emplates\b', re.I), 'Templates'),
    (re.compile(r'\bT\s+ool\b', re.I), 'Tool'),
    (re.compile(r'\bT\s+ools\b', re.I), 'Tools'),
    (re.compile(r'\bU\s+ser\b', re.I), 'User'),
    (re.compile(r'\bU\s+sers\b', re.I), 'Users'),
    (re.compile(r'\bUs\s+er\b', re.I), 'User'),
    (re.compile(r'\bUs\s+ers\b', re.I), 'Users'),
    (re.compile(r'\bW\s+izard\b', re.I), 'Wizard'),
    (re.compile(r'\bW\s+eb\b', re.I), 'Web'),
    (re.compile(r'\bL\s+og\b', re.I), 'Log'),

    # Desprendimiento de letra inicial / flotante entre palabras
    (re.compile(r'\bCreate\s+t\s+he\b', re.I), 'Create the'),
    (re.compile(r'\bUser\s+p\s+asswords\b', re.I), 'User passwords'),
    (re.compile(r'\bthe\s+y\s+have\b', re.I), 'they have'),
    (re.compile(r'\bthe\s+f\s+eatures\b', re.I), 'the features'),
    (re.compile(r'\bthe\s+f\s+eat\s*ures\b', re.I), 'the features'),
    (re.compile(r'\bthe\s+f\s+eat\s*ure\b', re.I), 'the feature'),
    (re.compile(r'\btrading\s+p\s+artners\b', re.I), 'trading partners'),
    (re.compile(r'\bHow\s+t\s+o\b', re.I), 'How to'),
    (re.compile(r'\bth\s+e\s+Cluster\b', re.I), 'the Cluster'),
    (re.compile(r'\bfo\s+r\s+GoAnywhere\b', re.I), 'for GoAnywhere'),
    (re.compile(r'\bKe\s+y\s+Preferences\b', re.I), 'Key Preferences'),
    (re.compile(r'\bGrou\s+ps\s+t\s+o\b', re.I), 'Groups to'),
    (re.compile(r'\bProm\s*te\s+W\s+eb\b', re.I), 'Promote Web'),

    # Palabras de 3 partes adicionales
    (re.compile(r'\bH\s+isto\s*ry\b', re.I), 'History'),
    (re.compile(r'\bM\s+ast\s*er\b', re.I), 'Master'),
    (re.compile(r'\bM\s+anag\s+em\s*ent\b', re.I), 'Management'),
    (re.compile(r'\bM\s+anag\s+em\b', re.I), 'Managem'),
    (re.compile(r'\bR\s+eso\s*urce\b', re.I), 'Resource'),
    (re.compile(r'\bRe\s+sou\s*rce\b', re.I), 'Resource'),
    (re.compile(r'\bReso\s+urc\s*e\b', re.I), 'Resource'),
    (re.compile(r'\bS\s+erve\s*r\b', re.I), 'Server'),
    (re.compile(r'\bS\s+ub\s+mitted\b', re.I), 'Submitted'),
    (re.compile(r'\bSy\s+ste\s*m\b', re.I), 'System'),
    (re.compile(r'\bT\s+rig\s*ger\b', re.I), 'Trigger'),
    (re.compile(r'\bTra\s+nsf\s*er\b', re.I), 'Transfer'),
    (re.compile(r'\bW\s+iza\s*rd\b', re.I), 'Wizard'),
    (re.compile(r'\bU\s+na\s+uthorized\b', re.I), 'Unauthorized'),
    (re.compile(r'\bOr\s+ganiz\s*e\b', re.I), 'Organize'),
    (re.compile(r'\bf\s+eat\s*ures\b', re.I), 'features'),
    (re.compile(r'\bf\s+eat\s*ure\b', re.I), 'feature'),

    # Palabras de 2 partes adicionales
    (re.compile(r'\bActio\s+ns\b', re.I), 'Actions'),
    (re.compile(r'\bAge\s+nt\b', re.I), 'Agent'),
    (re.compile(r'\bAge\s+nts\b', re.I), 'Agents'),
    (re.compile(r'\bAgen\s+t\b', re.I), 'Agent'),
    (re.compile(r'\bAlgorit\s+hms\b', re.I), 'Algorithms'),
    (re.compile(r'\bCon\s+siderations\b', re.I), 'Considerations'),
    (re.compile(r'\bDatab\s+ase\b', re.I), 'Database'),
    (re.compile(r'\bDet\s+ails\b', re.I), 'Details'),
    (re.compile(r'\bDis\s+aster\b', re.I), 'Disaster'),
    (re.compile(r'\bErr\s+ors\b', re.I), 'Errors'),
    (re.compile(r'\bEx\s+ecution\b', re.I), 'Execution'),
    (re.compile(r'\bEx\s+emptions\b', re.I), 'Exemptions'),
    (re.compile(r'\bExec\s+ute\b', re.I), 'Execute'),
    (re.compile(r'\bExecuti\s+ng\b', re.I), 'Executing'),
    (re.compile(r'\bGlo\s+bal\b', re.I), 'Global'),
    (re.compile(r'\bGrou\s+ps\b', re.I), 'Groups'),
    (re.compile(r'\bIm\s+port\b', re.I), 'Import'),
    (re.compile(r'\bImp\s+ort\b', re.I), 'Import'),
    (re.compile(r'\bLic\s+ense\b', re.I), 'License'),
    (re.compile(r'\bLo\s+gin\b', re.I), 'Login'),
    (re.compile(r'\bMan\s+age\b', re.I), 'Manage'),
    (re.compile(r'\bMana\s+ger\b', re.I), 'Manager'),
    (re.compile(r'\bPart\s+ners\b', re.I), 'Partners'),
    (re.compile(r'\bPa\s+rtners\b', re.I), 'Partners'),
    (re.compile(r'\bPass\s+word\b', re.I), 'Password'),
    (re.compile(r'\bPass\s+words\b', re.I), 'Passwords'),
    (re.compile(r'\bPermis\s+sions\b', re.I), 'Permissions'),
    (re.compile(r'\bPrefer\s+ences\b', re.I), 'Preferences'),
    (re.compile(r'\bServ\s+er\b', re.I), 'Server'),
    (re.compile(r'\bServi\s+ce\b', re.I), 'Service'),
    (re.compile(r'\bSyst\s+em\b', re.I), 'System'),
    (re.compile(r'\bTransf\s+er\b', re.I), 'Transfer'),
    (re.compile(r'\busin\s+g\b', re.I), 'using'),
    (re.compile(r'\bexecut\s+e\b', re.I), 'execute'),
    (re.compile(r'\bCertificate\s+\(s\)\b', re.I), 'Certificate(s)'),
    (re.compile(r'\bCertificate\s+s\b', re.I), 'Certificates'),
    (re.compile(r'\bConfig\s+uring\b', re.I), 'Configuring'),
    (re.compile(r'\bConfig\s+urin\s*g\b', re.I), 'Configuring'),
    (re.compile(r'\bFil\s+eCatalyst\b', re.I), 'FileCatalyst'),
    (re.compile(r'\bDeplo\s+yment\b', re.I), 'Deployment'),
    (re.compile(r'\bPe\s+rmis\s*sions\b', re.I), 'Permissions'),
    (re.compile(r'\bTe\s+mplate\b', re.I), 'Template'),
    (re.compile(r'\bLicensin\s+g\b', re.I), 'Licensing'),
    (re.compile(r'\bProj\s+ects\b', re.I), 'Projects'),
    (re.compile(r'\bGoAnywhe\s*re\b', re.I), 'GoAnywhere'),
    (re.compile(r'\bM\s+FT\b', re.I), 'MFT'),
    (re.compile(r'\bManagem\s+ent\b', re.I), 'Management'),
    (re.compile(r'\bPa\s+rtne\s*r\b', re.I), 'Partner'),
    (re.compile(r'\bSetti\s+ng\b', re.I), 'Setting'),
    (re.compile(r'\bMA\s+IL\b', re.I), 'MAIL'),
    (re.compile(r'\bcon\s+nections\b', re.I), 'connections'),
    (re.compile(r'\baPr\s+oject\b', re.I), 'a Project'),
    (re.compile(r'\bAuthentica\s+tion\b', re.I), 'Authentication'),
    (re.compile(r'\bComm\s+unication\b', re.I), 'Communication'),

    # Letra final partida por espaciado de margen/kerning
    (re.compile(r'\bCas\s+e\b', re.I), 'Case'),
    (re.compile(r'\bChrom\s+e\b', re.I), 'Chrome'),
    (re.compile(r'\bCluste\s+r\b', re.I), 'Cluster'),
    (re.compile(r'\bCod\s+e\b', re.I), 'Code'),
    (re.compile(r'\bCoul\s+d\b', re.I), 'Could'),
    (re.compile(r'\bCrea\s+te\b', re.I), 'Create'),
    (re.compile(r'\bDele\s+te\b', re.I), 'Delete'),
    (re.compile(r'\bDen\s+y\b', re.I), 'Deny'),
    (re.compile(r'\bDirector\s+y\b', re.I), 'Directory'),
    (re.compile(r'\bDomai\s+n\b', re.I), 'Domain'),
    (re.compile(r'\bDomain\s+s\b', re.I), 'Domains'),
    (re.compile(r'\bElemen\s+t\b', re.I), 'Element'),
    (re.compile(r'\bExecutin\s+g\b', re.I), 'Executing'),
    (re.compile(r'\bFile\s+s\b', re.I), 'Files'),
    (re.compile(r'\bFor\s+m\b', re.I), 'Form'),
    (re.compile(r'\bGoAnywher\s+e\b', re.I), 'GoAnywhere'),
    (re.compile(r'\bGoFas\s+t\b', re.I), 'GoFast'),
    (re.compile(r'\bGrou\s+p\b', re.I), 'Group'),
    (re.compile(r'\bHistor\s+y\b', re.I), 'History'),
    (re.compile(r'\bInterne\s+t\b', re.I), 'Internet'),
    (re.compile(r'\bMetho\s+d\b', re.I), 'Method'),
    (re.compile(r'\bMicrosof\s+t\b', re.I), 'Microsoft'),
    (re.compile(r'\bOption\s+s\b', re.I), 'Options'),
    (re.compile(r'\bPartne\s+r\b', re.I), 'Partner'),
    (re.compile(r'\bProjec\s+t\b', re.I), 'Project'),
    (re.compile(r'\bQuic\s+k\b', re.I), 'Quick'),
    (re.compile(r'\bSecur\s+e\b', re.I), 'Secure'),
    (re.compile(r'\bSen\s+d\b', re.I), 'Send'),
    (re.compile(r'\bStar\s+t\b', re.I), 'Start'),
    (re.compile(r'\bTas\s+k\b', re.I), 'Task'),
    (re.compile(r'\bTrigge\s+r\b', re.I), 'Trigger'),
    (re.compile(r'\bUpda\s+te\b', re.I), 'Update'),
    (re.compile(r'\bUse\s+r\b', re.I), 'User'),
    (re.compile(r'\bVariabl\s+e\b', re.I), 'Variable'),
    (re.compile(r'\bVariable\s+s\b', re.I), 'Variables'),
    (re.compile(r'\bVie\s+w\b', re.I), 'View'),
    (re.compile(r'\bWhil\s+e\b', re.I), 'While'),
    (re.compile(r'\btransfer\s+s\b', re.I), 'transfers'),
    (re.compile(r'\byou\s+r\b', re.I), 'your'),

    # Casos de marca y nombres compuestos
    (re.compile(r'GettingStarted>GoAnywhereFeatureTour', re.I), 'Getting Started > GoAnywhere Feature Tour'),
    (re.compile(r'\bW\s+ebDAV\b', re.I), 'WebDAV'),
    (re.compile(r'\bGoAn\s*ywhere\b', re.I), 'GoAnywhere'),
    (re.compile(r'\bGo\s+A\s+nywhere\b', re.I), 'GoAnywhere'),
    (re.compile(r'\bGo\s+Anywhere\b', re.I), 'GoAnywhere'),
    (re.compile(r'\bcom\s+municates\b', re.I), 'communicates'),
    (re.compile(r'\bFT\s+P,\s*FTP\s+S,', re.I), 'FTP, FTPS,'),
    (re.compile(r'\bExec\s+ute\b', re.I), 'Execute'),
    (re.compile(r'\bOA\s+uth\b', re.I), 'OAuth'),
    (re.compile(r'\bActivatea\s*License\b', re.I), 'Activate a License'),
    (re.compile(r'\bActivateaLicense\b', re.I), 'Activate a License'),
    (re.compile(r'\bServerID\b', re.I), 'Server ID'),
    (re.compile(r'\bGetLicense\b', re.I), 'Get License'),
    (re.compile(r'\bf\s+ormat\s+f\s+ormat\b', re.I), 'format'),
    (re.compile(r'\bf\s+ormat\b', re.I), 'format'),
]

# Palabras objetivo para la heurística de letras desprendidas
_PALABRAS_HEURISTICA = {
    'the', 'to', 'passwords', 'password', 'features', 'feature', 'partners', 'partner',
    'have', 'that', 'this', 'with', 'from', 'agent', 'agents', 'execute', 'executed',
    'executing', 'create', 'created', 'delete', 'update', 'start', 'history', 'system',
    'resource', 'server', 'service', 'submitted', 'unauthorized', 'organize', 'wizard'
}


def _desfragmentar_letras_sueltas(texto: str) -> str:
    """Heurística generalizada: reubica letras sueltas intermedias entre palabras para páginas 100+."""
    if not texto:
        return ""

    def _reubicar(m: re.Match) -> str:
        w1, l, w2 = m.group(1), m.group(2), m.group(3)
        cand_derecha = (l + w2).lower()
        if cand_derecha in _PALABRAS_HEURISTICA:
            nueva_w2 = (l + w2) if not w2[0].isupper() else (l.upper() + w2)
            return f"{w1} {nueva_w2}"
        cand_izquierda = (w1 + l).lower()
        if cand_izquierda in _PALABRAS_HEURISTICA:
            return f"{w1 + l} {w2}"
        return m.group(0)

    return re.sub(r'\b([A-Za-z]{2,})\s+([b-hj-z])\s+([a-z]{1,})\b', _reubicar, texto)


def _reparar_palabras_rotas(texto: str) -> str:
    """Normaliza y recompone palabras separadas por espacios indeseados debido a la fragmentación de glifos en Scribd."""
    if not texto:
        return ""
    res = texto
    # 1. Aplicar patrones compilados del dominio
    for pat, rep in RE_PATRONES_DESFRAGMENTACION:
        def _rep_func(m: re.Match) -> str:
            t = m.group(0)
            return rep.lower() if t.islower() else rep
        res = pat.sub(_rep_func, res)
    # 2. Aplicar heurística dinámica de desfragmentación
    res = _desfragmentar_letras_sueltas(res)
    # 3. Normalizar rutas de navegación de menús con '>'
    res = re.sub(r'([a-z])>([A-Z])', r'\1 > \2', res)
    # 4. Normalizar casos de protocolos y puntuación espaciada
    res = re.sub(r'\[protocol\]:\s*//', '[protocol]://', res)
    res = re.sub(r'\s+([.,;:!?])', r'\1', res)
    return res


def _enriquecer_links(texto: str) -> str:
    """Convierte URLs y enlaces textuales conocidos en etiquetas <a> con clase estilizada 'doc-link'."""
    if not texto:
        return ""
    # URLs directas (http o https), excluyendo puntuación final
    def _rep_url(m: re.Match) -> str:
        raw = m.group(1)
        url = raw.rstrip('.,;:!?')
        punct = raw[len(url):]
        return f'<a href="{url}" class="doc-link" target="_blank" rel="noopener">{url}</a>{punct}'

    res = re.sub(r'\b(https?://[^\s<>"\'\)]+)', _rep_url, texto)
    # Enlaces oficiales del portal GoAnywhere
    res = re.sub(
        r'\bCustomer\s+Operations\b',
        r'<a href="https://my.goanywhere.com/" class="doc-link" target="_blank" rel="noopener">Customer Operations</a>',
        res
    )
    res = re.sub(
        r'\bCustomer\s+Support\b',
        r'<a href="https://my.goanywhere.com/" class="doc-link" target="_blank" rel="noopener">Customer Support</a>',
        res
    )
    return res


# ════════════════════════════════════════════════════════════════════════════
# Carga de datos
# ════════════════════════════════════════════════════════════════════════════

def validar_origen(origen: Path) -> None:
    if not origen.exists():
        raise PrecondicionError(
            f"La carpeta de origen no existe: {origen}\n"
            f"           Verifique la ruta o indique otra con --origen <carpeta_extraccion>."
        )
    if not origen.is_dir():
        raise PrecondicionError(f"--origen debe ser una carpeta, no un archivo: {origen}")


def localizar_archivo_datos(origen: Path, nombre_explicito: str | None) -> Path:
    candidatos = (nombre_explicito,) if nombre_explicito else ARCHIVOS_DATOS
    for nombre in candidatos:
        ruta = origen / nombre
        if ruta.is_file():
            return ruta
    presentes = sorted(p.name for p in origen.glob("*.json"))
    raise PrecondicionError(
        f"No se encontró {' ni '.join(candidatos)} en {origen}\n"
        f"           JSON presentes: {', '.join(presentes) or '(ninguno)'}. Use --datos <archivo.json>."
    )


def leer_json(ruta: Path) -> Any:
    try:
        with ruta.open("r", encoding="utf-8-sig") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise PrecondicionError(
            f"JSON inválido en {ruta.name}: línea {exc.lineno}, columna {exc.colno}: {exc.msg}"
        ) from exc
    except UnicodeDecodeError as exc:
        raise PrecondicionError(f"{ruta.name} no está codificado en UTF-8: {exc}") from exc


def detectar_esquema(datos: Any) -> str:
    if not isinstance(datos, dict):
        raise PrecondicionError("El archivo de datos debe contener un objeto JSON en la raíz.")
    if "secciones" in datos or "meta" in datos:
        return "reporte"
    if "paginas" in datos:
        return "paginas"
    raise PrecondicionError(
        "Esquema de datos no reconocido: se esperaba 'meta'/'secciones' (datos.json) "
        "o 'documento'/'paginas' (paginas.json)."
    )


def _limpiar_lineas_scribd(lineas: list[str]) -> list[str]:
    """Elimina redundancias posicionales de Scribd (.text_layer), sufijos y fragmentos hijos duplicados."""
    # 1. Normalizar caracteres y filtrar líneas vacías
    raw: list[str] = []
    for l in lineas:
        s = re.sub(r"[\ue000-\uf8ff]", "", str(l)).replace("\u00a0", " ").replace("\u2019", "'").replace("\u2018", "'").strip()
        if s:
            raw.append(s)

    # 2. Colapsar sufijos idénticos consecutivos
    etapa1: list[str] = []
    i = 0
    n = len(raw)
    while i < n:
        actual = raw[i]
        etapa1.append(actual)
        j = i + 1
        while j < n:
            sig = raw[j]
            if actual == sig or (actual.endswith(sig) and len(sig) < len(actual)):
                j += 1
            else:
                break
        i = j

    # 3. Detectar y suprimir fragmentos hijos desglosados inmediatamente posteriores
    etapa2: list[str] = []
    i = 0
    n = len(etapa1)
    while i < n:
        actual = etapa1[i]
        etapa2.append(actual)
        if actual == 'l':
            i += 1
            continue

        actual_norm = re.sub(r'[^a-zA-Z0-9]', '', actual).lower()
        if len(actual_norm) >= 8:
            j = i + 1
            buf_str = ""
            while j < n and len(buf_str) < len(actual_norm):
                if etapa1[j] == 'l':
                    break
                s_norm = re.sub(r'[^a-zA-Z0-9]', '', etapa1[j]).lower()
                if not s_norm:
                    j += 1
                    continue
                if not actual_norm.startswith(buf_str + s_norm):
                    break
                buf_str += s_norm
                j += 1
                if buf_str == actual_norm:
                    i = j - 1
                    break
        i += 1

    return etapa2


def _parsear_items_toc(lineas_limpias: list[str]) -> list[dict]:
    """Extrae las entradas de Tabla de Contenidos agrupando títulos con sus páginas de destino de forma robusta."""
    raw_items: list[tuple[str, str]] = []
    buffer_text: list[str] = []
    ignored = {
        'Table of Contents', 'TableofContents', 'GoAnywhere MFT User Guide',
        'GoAnywhere MFTUser Guide', 'www.goanywhere.com'
    }

    n = len(lineas_limpias)
    k = 0
    while k < n:
        line = lineas_limpias[k].strip()
        k += 1
        if not line or line in ignored or re.match(r'^page:\s*\d+$', line, re.I):
            continue
        if 'www.goanywhere.com' in line or 'GoAnywhere MFT' in line:
            continue

        # Si la línea es puramente numérica y el buffer está vacío, puede ser sufijo del ítem previo
        if line.isdigit() and not buffer_text and raw_items:
            prev_t, prev_p = raw_items[-1]
            if len(prev_p) < 4:
                raw_items[-1] = (prev_t, prev_p + line)
            continue

        m_space = re.search(r'^(.*?)\s+(\d{1,4})$', line)
        m_attached = re.search(r'^(.*?[a-zA-Z\)])(\d{1,4})$', line)

        match_cand = None
        if m_space and (len(m_space.group(1).strip()) > 1 or buffer_text):
            match_cand = (m_space.group(1).strip(), m_space.group(2))
        elif m_attached and (len(m_attached.group(1).strip()) > 1 or buffer_text):
            raw_title = m_attached.group(1).strip()
            split_title = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw_title)
            match_cand = (split_title, m_attached.group(2))

        if match_cand:
            t_cand, p_cand = match_cand

            # Versiones de software en títulos (ej. Internet Explorer 11)
            if buffer_text and any(w in " ".join(buffer_text) for w in ("Explorer", "IPv", "SHA")) and (t_cand in ("11", "1", "6", "4") or p_cand in ("11", "1", "6", "4")):
                buffer_text.append(f"{t_cand}{p_cand}")
                continue

            # Mirar si la siguiente línea son dígitos que completan la página
            if k < n and lineas_limpias[k].strip().isdigit() and len(p_cand) <= 2:
                p_cand = p_cand + lineas_limpias[k].strip()
                k += 1

            # En este manual, las páginas del TOC comienzan en la página 39
            if int(p_cand) < 39:
                buffer_text.append(f"{t_cand}{p_cand}")
                continue

            full_title = _reparar_palabras_rotas(" ".join(buffer_text + [t_cand]).strip())

            # Corrección de OCR en "Monitoring Files on an Agent 227" -> 2277
            if p_cand == "227" and "Monitoring" in full_title:
                p_cand = "2277"

            raw_items.append((full_title, p_cand))
            buffer_text = []

        elif line.isdigit():
            if buffer_text and any(w in " ".join(buffer_text) for w in ("Explorer", "IPv", "SHA")) and line in ("11", "1", "6", "4"):
                buffer_text.append(line)
                continue

            pg = line
            if k < n and lineas_limpias[k].strip().isdigit():
                pg = pg + lineas_limpias[k].strip()
                k += 1

            if int(pg) < 39:
                buffer_text.append(pg)
                continue

            if buffer_text:
                raw_items.append((_reparar_palabras_rotas(" ".join(buffer_text).strip()), pg))
                buffer_text = []
            elif raw_items:
                prev_t, prev_p = raw_items[-1]
                if len(prev_p) < 4:
                    raw_items[-1] = (prev_t, prev_p + pg)
        else:
            if buffer_text and line in buffer_text[-1]:
                continue
            buffer_text.append(line)

    # Post-procesamiento: resolver fusiones y números desplazados al título
    items_procesados: list[tuple[str, str]] = []
    for title, pg in raw_items:
        clean_title = _reparar_palabras_rotas(re.sub(r'\s+', ' ', title).strip())
        clean_pg = str(pg).strip()

        # Prefijo de página atrapado al final del título (ej. "Google Chrome 29" -> 51 => "Google Chrome" -> 2951)
        m_sufijo_tit = re.search(r'^(.*?)(?<!IPv)(?<!SHA)(?<!EDI)(?<!Section)\s+(\d{1,3})$', clean_title)
        if m_sufijo_tit:
            posible_tit = m_sufijo_tit.group(1).strip()
            num_tit = m_sufijo_tit.group(2)
            candidato_pg = num_tit + clean_pg
            try:
                c_val = int(candidato_pg)
                if 39 <= c_val <= 3720 and len(candidato_pg) >= 3 and len(clean_pg) <= 3:
                    clean_title = posible_tit
                    clean_pg = candidato_pg
            except ValueError:
                pass

        # Títulos fusionados con un número en medio (ej. "Import XML 413 Import ZIP" -> 415)
        m_fusion = re.match(r'^(.*?[a-zA-Z\)])\s+(\d{2,4})\s+([A-Z].*)$', clean_title)
        if m_fusion:
            tit1 = m_fusion.group(1).strip()
            pg1_str = m_fusion.group(2)
            tit2 = m_fusion.group(3).strip()
            pg2_str = clean_pg
            try:
                p1 = int(pg1_str)
                p2 = int(pg2_str)
                if 0 <= (p2 - p1) <= 50 and 39 <= p1 <= 3720:
                    items_procesados.append((tit1, pg1_str))
                    clean_title = tit2
                    clean_pg = pg2_str
            except ValueError:
                pass

        items_procesados.append((clean_title, clean_pg))

    # Deduplicación y correcciones tipográficas
    deduped: list[dict] = []
    temas_principales = {
        'getting started', 'dashboard', 'resources', 'workflows',
        'project design', 'task reference', 'database tasks',
        'data translation tasks'
    }

    for title, pg in items_procesados:
        clean_title = re.sub(r'\s+', ' ', title).strip()
        words = clean_title.split()
        if len(words) >= 6:
            half = len(words) // 2
            if " ".join(words[:half]).lower() == " ".join(words[half:2*half]).lower():
                clean_title = " ".join(words[:half])

        for orig, corr in (
            ("Auth entication", "Authentication"),
            ("Authenti ca tion", "Authentication"),
            ("Authenticatio n", "Authentication"),
            ("Pro ject", "Project"),
            ("Fo lders", "Folders"),
            ("Fol der", "Folder"),
            ("Sched ule", "Schedule"),
            ("Ex ample", "Example"),
            ("Ch ange", "Change"),
            ("Queu Manager", "Queue Manager"),
            ("Des igning", "Designing"),
            ("Sy stem", "System"),
            ("Varia ble", "Variable"),
            ("Vari abl e", "Variable"),
            ("Ta sk", "Task"),
            ("T ask", "Task"),
            ("Makin g", "Making"),
            ("Yo ur", "Your"),
            ("F iles", "Files"),
            ("T roubles hoo ting", "Troubleshooting"),
            ("Workflow s", "Workflows"),
            ("Decisionswith", "Decisions with"),
            ("PasswordProtect", "Password Protect"),
            ("Fixed-w idth", "Fixed-width"),
            ("Nod e", "Node"),
            ("A ctions", "Actions"),
            ("Transact ion", "Transaction"),
            ("In for mation", "Information"),
            ("Base 64", "Base64"),
            ("IPv 6", "IPv6"),
            ("SHA 1", "SHA1"),
        ):
            if orig in clean_title:
                clean_title = clean_title.replace(orig, corr)

        # Descartar fragmento residual "Base" -> 64
        if clean_title == "Base" and pg == "64":
            continue

        norm = re.sub(r'[^a-zA-Z0-9]', '', clean_title).lower()
        if not norm:
            continue

        if deduped:
            prev = deduped[-1]
            prev_norm = re.sub(r'[^a-zA-Z0-9]', '', prev["titulo"]).lower()
            mismo_titulo = (norm == prev_norm or (len(norm) > 6 and (norm in prev_norm or prev_norm in norm)))
            misma_pagina = (prev["pagina"] == pg or prev["pagina"].startswith(pg) or pg.startswith(prev["pagina"]))

            if mismo_titulo and misma_pagina:
                if len(pg) > len(prev["pagina"]):
                    prev["pagina"] = pg
                if len(clean_title) < len(prev["titulo"]):
                    prev["titulo"] = clean_title
                continue

        es_principal = clean_title.lower() in temas_principales
        deduped.append({
            "titulo": clean_title,
            "pagina": pg,
            "es_principal": es_principal
        })

    return deduped


CAPITULOS_CANONICOS = {
    "gettingstarted": "Getting Started",
    "dashboard": "Dashboard",
    "workflows": "Workflows",
    "projectdesign": "Project Design",
    "taskreference": "Task Reference",
    "databasetasks": "Database Tasks",
    "datatranslationtasks": "Data Translation Tasks",
    "resources": "Resources",
}


def _construir_indice_toc(paginas_completas: list[dict]) -> dict:
    """Extrae y normaliza el índice del TOC de las páginas 3 a 38 para guiar las cabeceras de contenido."""
    temas_norm: dict[str, str] = {}
    inicios_tema: dict[int, list[str]] = {}

    for pag in paginas_completas:
        p_num = pag.get("numero_pagina", 0)
        if 3 <= p_num <= 38:
            raw = pag.get("lineas_texto") or []
            limp = _limpiar_lineas_scribd(raw)
            items = _parsear_items_toc(limp)
            for it in items:
                t = it["titulo"]
                try:
                    p_dest = int(it["pagina"])
                    norm = re.sub(r'[^a-zA-Z0-9]', '', t).lower()
                    if norm and len(norm) > 4:
                        temas_norm[norm] = t
                    inicios_tema.setdefault(p_dest, []).append(t)
                except ValueError:
                    pass
    return {"temas_norm": temas_norm, "inicios": inicios_tema}


def _parsear_contenido_pagina(num: int, lineas_limpias: list[str], indice_toc: dict | None = None) -> dict:
    """Extrae elementos estructurados de páginas de contenido guiado por el índice canónico del TOC."""
    if not lineas_limpias:
        return {"running_header": "", "elementos": []}

    indice_toc = indice_toc or {}
    temas_norm = indice_toc.get("temas_norm", {})
    inicios_tema = indice_toc.get("inicios", {})

    lineas = list(lineas_limpias)
    running_header = ""

    # 1. Determinar running header canónico
    if lineas and '/' in lineas[0]:
        first = lineas.pop(0).strip()
        raw_cap = first.split('/')[0].strip()
        norm_cap = re.sub(r'[^a-zA-Z0-9]', '', raw_cap).lower()
        nom_cap = CAPITULOS_CANONICOS.get(
            norm_cap,
            _reparar_palabras_rotas(re.sub(r'([a-z])([A-Z])', r'\1 \2', raw_cap).strip())
        )
        running_header = nom_cap

        # Verificar si la siguiente línea es un tema mayor registrado en el TOC
        if lineas:
            sig = lineas[0].strip()
            norm_sig = re.sub(r'[^a-zA-Z0-9]', '', sig).lower()
            if norm_sig in temas_norm:
                titulo_oficial = temas_norm[norm_sig]
                running_header = f"{nom_cap} / {titulo_oficial}"
                lineas.pop(0)  # Consumida como sección del encabezado

    # Descartar pie de página Scribd
    while lineas and ('www.goanywhere.com' in lineas[-1] or 'GoAnywhere MFT' in lineas[-1] or re.match(r'^page:\s*\d+$', lineas[-1], re.I)):
        lineas.pop()

    elementos = []

    # Si esta página es el inicio oficial de un tema en el TOC, asegurar el título H1 correspondiente
    temas_que_inician = inicios_tema.get(num, [])
    temas_esta_pag = {re.sub(r'[^a-zA-Z0-9]', '', t).lower(): t for t in temas_que_inician}
    if temas_que_inician:
        primer_tema = temas_que_inician[0]
        primer_linea_norm = re.sub(r'[^a-zA-Z0-9]', '', lineas[0]).lower() if lineas else ""
        tema_norm = re.sub(r'[^a-zA-Z0-9]', '', primer_tema).lower()
        if primer_linea_norm == tema_norm:
            lineas.pop(0)
            elementos.append({"tipo": "h1", "texto": primer_tema})
            temas_esta_pag.pop(tema_norm, None)
        elif not any(re.sub(r'[^a-zA-Z0-9]', '', x).lower() == tema_norm for x in lineas):
            # Si el tema no aparece como línea completa en las líneas siguientes (porque fue consumido en el encabezado, ej. pág 50)
            elementos.append({"tipo": "h1", "texto": primer_tema})
            temas_esta_pag.pop(tema_norm, None)

    i = 0
    n = len(lineas)

    while i < n:
        l = lineas[i].strip()
        if not l:
            i += 1
            continue

        if elementos and elementos[-1].get("texto") == l:
            i += 1
            continue

        norm_l = re.sub(r'[^a-zA-Z0-9]', '', l).lower()
        if norm_l in temas_esta_pag:
            tit_h1 = temas_esta_pag.pop(norm_l)
            elementos.append({"tipo": "h1", "texto": tit_h1})
            i += 1
            continue

        # Detección de viñeta (bullet) 'l' (acumula oraciones completas hasta siguiente ítem o encabezado)
        if l == 'l':
            i += 1
            buf_bullet = []
            while i < n and lineas[i].strip() != 'l' and not re.match(r'^\d+\.\s', lineas[i].strip()) and not lineas[i].strip().startswith(('TIP:', 'WARNING:', 'NOTE:')):
                item = lineas[i].strip()
                norm_item = re.sub(r'[^a-zA-Z0-9]', '', item).lower()
                if norm_item in temas_esta_pag:
                    break
                if buf_bullet and buf_bullet[-1].endswith(('.', '!', '?')) and 6 <= len(item) < 55 and not item.endswith(('.', ',', ';', ':')) and not item.startswith(('http:', 'https:')) and not re.match(r'^(for|where|and|or|with|to|in|of|on|at|by|from|the|a|an)\b', item, re.I):
                    if i + 1 < n and lineas[i + 1].strip() not in ('l',) and not re.match(r'^\d+\.\s', lineas[i + 1].strip()):
                        break
                buf_bullet.append(item)
                i += 1
            if buf_bullet:
                txt = _enriquecer_links(_reparar_palabras_rotas(re.sub(r'\s+', ' ', " ".join(buf_bullet))))
                elementos.append({"tipo": "bullet", "texto": txt})
            continue

        # Pasos numerados (1. , 2. , etc.)
        if re.match(r'^\d+\.\s', l):
            buf_num = [l]
            i += 1
            if not l.endswith('.'):
                while i < n and not re.match(r'^\d+\.\s', lineas[i].strip()) and lineas[i].strip() != 'l' and not lineas[i].strip().startswith(('TIP:', 'WARNING:', 'NOTE:')):
                    item = lineas[i].strip()
                    norm_item = re.sub(r'[^a-zA-Z0-9]', '', item).lower()
                    if norm_item in temas_esta_pag:
                        break
                    buf_num.append(item)
                    if item.endswith('.'):
                        i += 1
                        break
                    i += 1
            txt = _enriquecer_links(_reparar_palabras_rotas(re.sub(r'\s+', ' ', " ".join(buf_num))))
            elementos.append({"tipo": "numero", "texto": txt})
            continue

        # Bloques WARNING / TIP / NOTE
        if l.startswith(('WARNING:', 'TIP:', 'NOTE:')) or l in ('WARNING:', 'TIP:', 'NOTE:'):
            es_warning = l.startswith('WARNING:') or l == 'WARNING:'
            buf_callout = [l]
            i += 1
            while i < n and not re.match(r'^\d+\.\s', lineas[i].strip()) and lineas[i].strip() != 'l' and not lineas[i].strip().startswith(('TIP:', 'WARNING:', 'NOTE:')):
                item = lineas[i].strip()
                norm_item = re.sub(r'[^a-zA-Z0-9]', '', item).lower()
                if norm_item in temas_esta_pag:
                    break
                buf_callout.append(item)
                i += 1
            txt = _reparar_palabras_rotas(re.sub(r'\s+', ' ', " ".join(buf_callout)))
            txt = _enriquecer_links(txt)
            tipo_bloque = "warning" if es_warning else "tip"
            elementos.append({"tipo": tipo_bloque, "texto": txt})
            continue

        # Título principal de página (primer elemento de contenido si no fue establecido por TOC)
        if not elementos:
            t = _reparar_palabras_rotas(re.sub(r'([a-z])([A-Z])', r'\1 \2', l).strip())
            elementos.append({"tipo": "h1", "texto": t})
            i += 1
            continue

        # Subtítulo (h2) real: debe venir precedido de fin de oración, longitud mínima de 6 caracteres
        prev_texto = elementos[-1].get("texto", "") if elementos else ""
        es_cierre_previo = not prev_texto or prev_texto.endswith(('.', '!', '?', ':', '</div>', '</p>'))
        es_url = l.startswith(('http://', 'https://')) or '//' in l
        es_prep = bool(re.match(r'^(for|where|and|or|with|to|in|of|on|at|by|from|the|a|an)\b', l, re.I))

        if es_cierre_previo and not es_url and not es_prep and 6 <= len(l) < 55 and not l.endswith(('.', ',', ';', ':')):
            t = _reparar_palabras_rotas(re.sub(r'([a-z])([A-Z])', r'\1 \2', l).strip())
            if elementos and elementos[-1].get("texto") == t:
                i += 1
                continue
            elementos.append({"tipo": "h2", "texto": t})
            i += 1
            continue

        # Párrafos de texto continuo
        buf_p = [l]
        i += 1
        while i < n and lineas[i].strip() != 'l' and not re.match(r'^\d+\.\s', lineas[i].strip()) and not lineas[i].strip().startswith(('TIP:', 'WARNING:', 'NOTE:')):
            sig = lineas[i].strip()
            norm_sig = re.sub(r'[^a-zA-Z0-9]', '', sig).lower()
            if norm_sig in temas_esta_pag:
                break
            buf_str = " ".join(buf_p).strip()
            if buf_str.endswith(('.', '!', '?')):
                sig_es_url = sig.startswith(('http://', 'https://')) or '//' in sig
                sig_es_prep = bool(re.match(r'^(for|where|and|or|with|to|in|of|on|at|by|from|the|a|an)\b', sig, re.I))
                if not sig_es_url and not sig_es_prep and len(sig) < 55 and not sig.endswith(('.', ',', ';', ':')):
                    break
            buf_p.append(sig)
            if sig.endswith('.'):
                i += 1
                break
            i += 1

        txt = _enriquecer_links(_reparar_palabras_rotas(re.sub(r'\s+', ' ', " ".join(buf_p))))
        if not elementos or elementos[-1].get("texto") != txt:
            elementos.append({"tipo": "p", "texto": txt})

    return {"running_header": running_header, "elementos": elementos}


def _cargar_figuras_paginas(origen: Path | None) -> dict[int, list[dict]]:
    """Carga el catálogo de figuras_paginas.json buscando en origen o en output/."""
    candidatos: list[Path] = []
    if origen:
        candidatos.append(origen / "figuras_paginas.json")
        candidatos.append(origen.parent.parent / "output" / origen.name / "figuras_paginas.json")
        candidatos.append(origen.parent / "output" / origen.name / "figuras_paginas.json")
        candidatos.append(DIR_SCRIPT / "output" / origen.name / "figuras_paginas.json")
    candidatos.append(DIR_SCRIPT / "output" / "goanywhere_mft_user_guide_7_7_0" / "figuras_paginas.json")

    for ruta in candidatos:
        if ruta.is_file():
            try:
                datos = leer_json(ruta)
                raw_pags = datos.get("paginas", {}) if isinstance(datos, dict) else {}
                cat: dict[int, list[dict]] = {}
                for k, v in raw_pags.items():
                    try:
                        cat[int(k)] = v
                    except ValueError:
                        pass
                log.info("Catálogo de figuras cargado desde %s (%d páginas con figuras)", ruta, len(cat))
                return cat
            except Exception as e:
                log.warning("No se pudo leer catálogo de figuras en %s: %s", ruta, e)
    return {}


def _sincronizar_figura(f: dict, dir_html: Path | None) -> str:
    """Copia la figura a dir_html (subcarpeta figuras/) solo si no existe ya o su tamaño cambió."""
    rel_archivo = f.get("archivo", "")
    if not rel_archivo:
        return ""
    rel_normalizado = rel_archivo.replace("\\", "/")

    if dir_html is None:
        return rel_normalizado

    dest = dir_html / rel_archivo
    dest.parent.mkdir(parents=True, exist_ok=True)

    cands: list[Path] = []
    if f.get("archivo_absoluto"):
        cands.append(Path(f["archivo_absoluto"]))
    cands.append(DIR_SCRIPT / "output" / "goanywhere_mft_user_guide_7_7_0" / rel_archivo)
    cands.append(DIR_SCRIPT / rel_archivo)

    copiado = False
    for orig in cands:
        if orig.is_file():
            if not dest.is_file() or dest.stat().st_size != orig.stat().st_size:
                try:
                    shutil.copy2(orig, dest)
                    log.info("Figura sincronizada a reporte: %s -> %s", orig.name, dest)
                except Exception as exc:
                    log.warning("No se pudo copiar figura %s a %s: %s", orig, dest, exc)
            copiado = True
            break

    if not copiado and not dest.is_file():
        log.warning("Archivo de figura no localizado para %s", rel_archivo)

    return rel_normalizado


def _intercalar_figuras(elementos: list[dict], page_figs: list[dict], dir_html: Path | None) -> list[dict]:
    """Intercala las figuras de la página en la secuencia de elementos según su posición vertical estimada."""
    if not page_figs:
        return elementos

    figs_ordenadas = sorted(page_figs, key=lambda x: x.get("posicion_top_px", 0))

    alturas = []
    for e in elementos:
        t = e.get("tipo")
        txt = e.get("texto", "")
        n_lin = max(1, len(txt) / 80.0)
        if t == "h1":
            h = 60.0
        elif t == "h2":
            h = 45.0
        elif t in ("tip", "warning"):
            h = 50.0 + n_lin * 22.0
        elif t in ("bullet", "numero"):
            h = 10.0 + n_lin * 26.0
        else:
            h = 10.0 + n_lin * 25.0
        alturas.append(h + 15.0)

    res: list[dict] = []
    idx_fig = 0
    n_figs = len(figs_ordenadas)
    y_actual = 110.0

    for i, e in enumerate(elementos):
        h_e = alturas[i]
        y_medio = y_actual + (h_e * 0.5)

        while idx_fig < n_figs:
            f = figs_ordenadas[idx_fig]
            top_px = float(f.get("posicion_top_px", 0))
            if i == 0 and e.get("tipo") == "h1" and top_px >= 90:
                break
            if top_px <= y_medio:
                ruta_rel = _sincronizar_figura(f, dir_html)
                res.append({
                    "tipo": "figura",
                    "id": f.get("id"),
                    "archivo": ruta_rel,
                    "ancho": f.get("ancho"),
                    "alto": f.get("alto"),
                    "posicion_top_px": top_px,
                    "caption": f.get("caption", ""),
                })
                idx_fig += 1
            else:
                break

        res.append(e)
        y_actual += h_e

    while idx_fig < n_figs:
        f = figs_ordenadas[idx_fig]
        ruta_rel = _sincronizar_figura(f, dir_html)
        res.append({
            "tipo": "figura",
            "id": f.get("id"),
            "archivo": ruta_rel,
            "ancho": f.get("ancho"),
            "alto": f.get("alto"),
            "posicion_top_px": float(f.get("posicion_top_px", 0)),
            "caption": f.get("caption", ""),
        })
        idx_fig += 1

    # Regla tipográfica: una figura no debe intercalarse entre un encabezado H1/H2 y su primer contenido
    resultado_ordenado: list[dict] = []
    j = 0
    m = len(res)
    while j < m:
        if j < m - 1 and res[j]["tipo"] in ("h1", "h2") and res[j + 1]["tipo"] == "figura":
            resultado_ordenado.append(res[j + 1])
            resultado_ordenado.append(res[j])
            j += 2
        else:
            resultado_ordenado.append(res[j])
            j += 1

    return resultado_ordenado


def _reconstruir_paginas_documento(
    paginas: list[dict],
    doc_meta: dict,
    indice_toc: dict | None = None,
    figuras_dict: dict[int, list[dict]] | None = None,
    dir_html: Path | None = None
) -> list[dict]:
    """Genera la lista de páginas reconstruidas fielmente a partir de paginas.json guiado por el TOC."""
    paginas_doc = []

    for idx, pag in enumerate(paginas, start=1):
        num = pag.get("numero_pagina", idx)
        raw_lines = pag.get("lineas_texto") or []
        limpias = _limpiar_lineas_scribd(raw_lines)

        if num == 1:
            paginas_doc.append({
                "tipo": "portada",
                "numero": 1,
                "imagen": pag.get("imagen_relativa") or "imagenes/pagina_0001.png",
            })
        elif num == 2:
            parrafos = []
            build = "202412120113"
            for l in limpias:
                if "CopyrightTermsandConditions" in l or ("Copyright" in l and "Terms" in l):
                    continue
                if l.strip().isdigit() and len(l.strip()) >= 8:
                    build = l.strip()
                else:
                    parrafos.append(l)

            p_unidos = []
            buf = []
            for l in parrafos:
                buf.append(l)
                if l.endswith((".", ":")):
                    p_unidos.append(" ".join(buf))
                    buf = []
            if buf:
                p_unidos.append(" ".join(buf))

            paginas_doc.append({
                "tipo": "legal",
                "numero": 2,
                "titulo": "Copyright Terms and Conditions",
                "parrafos": p_unidos,
                "build": build,
            })
        elif num <= 38:
            items = _parsear_items_toc(limpias)
            mid = (len(items) + 1) // 2
            paginas_doc.append({
                "tipo": "toc",
                "numero": num,
                "columna_izq": items[:mid],
                "columna_der": items[mid:],
            })
        else:
            cnt = _parsear_contenido_pagina(num, limpias, indice_toc)
            elementos = cnt["elementos"]
            page_figs = figuras_dict.get(num, []) if figuras_dict else []
            if page_figs:
                elementos = _intercalar_figuras(elementos, page_figs, dir_html)

            paginas_doc.append({
                "tipo": "contenido",
                "numero": num,
                "running_header": cnt["running_header"],
                "elementos": elementos,
            })

    return paginas_doc


def adaptar_paginas_json(
    datos: dict,
    limite: int | None,
    pagina_objetivo: int | None = None,
    origen: Path | None = None,
    dir_html: Path | None = None
) -> dict:
    """
    Convierte el esquema de extracción botScribd (paginas.json) en una reconstrucción
    textual directa y fiel del documento original, consultando figuras_paginas.json
    para intercalar figuras existentes y sincronizarlas al reporte HTML.
    """
    doc = datos.get("documento") or {}
    paginas = datos.get("paginas")
    if not isinstance(paginas, list) or not paginas:
        raise PrecondicionError("paginas.json no contiene una lista 'paginas' con elementos.")

    total = len(paginas)
    # Construir el índice canónico del TOC a partir del catálogo completo
    indice_toc = _construir_indice_toc(paginas)
    # Cargar figuras asociadas a las páginas
    figuras_dict = _cargar_figuras_paginas(origen)

    if pagina_objetivo:
        seleccion = [p for p in paginas if p.get("numero_pagina") == pagina_objetivo]
        if not seleccion:
            raise PrecondicionError(f"La página {pagina_objetivo} no se encuentra en paginas.json (total registradas: {total}).")
        log.info("Adaptando paginas.json para página puntual %d (de %d páginas totales)", pagina_objetivo, total)
    else:
        seleccion = paginas[:limite] if limite else paginas
        if not limite and total > UMBRAL_PAGINAS_AVISO:
            log.warning(
                "El documento tiene %d páginas: la Fase 2 puede tardar y consumir mucha memoria. "
                "Considere --limite-paginas N para pruebas.", total
            )
        log.info("Adaptando paginas.json: %d de %d páginas seleccionadas (reconstrucción textual pura)", len(seleccion), total)

    titulo = _txt(doc.get("titulo")) or _txt(doc.get("slug")) or "Documento reconstruido"
    version = _txt(doc.get("version")) or (RE_VERSION.search(titulo).group(0) if RE_VERSION.search(titulo) else "7.7.0")

    paginas_doc = _reconstruir_paginas_documento(
        seleccion,
        doc,
        indice_toc=indice_toc,
        figuras_dict=figuras_dict,
        dir_html=dir_html
    )

    return {
        "modo_documento": True,
        "esquema": "reconstruccion",
        "meta": {
            "titulo": titulo,
            "subtitulo": "",
            "tipo_documento": "Documento reconstruido",
            "version": version,
            "fecha": doc.get("fecha_procesamiento"),
            "codigo_documento": _txt(doc.get("slug")),
            "estado": "Reconstrucción pura",
            "clasificacion": "Uso interno",
        },
        "paginas_documento": paginas_doc,
        "secciones": [],
        "resumen": [],
    }


# ════════════════════════════════════════════════════════════════════════════
# Normalización del esquema de reporte -> contexto de plantilla
# ════════════════════════════════════════════════════════════════════════════

class ConstructorContexto:
    """Valida y normaliza el JSON de reporte; numera tablas/figuras; resuelve rutas."""

    def __init__(self, resolutor: ResolutorRecursos):
        self.resolutor = resolutor
        self.contadores: Counter[str] = Counter()

    # -- API pública ---------------------------------------------------------
    def construir(self, datos: dict, archivo_datos: Path, esquema: str) -> dict:
        meta = self._meta(datos.get("meta") or {})
        secciones_in = datos.get("secciones") or []
        if not isinstance(secciones_in, list):
            raise PrecondicionError("'secciones' debe ser una lista.")
        secciones = [self._seccion(s, i) for i, s in enumerate(secciones_in, start=1)]
        resumen = _parrafos(datos.get("resumen"))
        es_modo_doc = bool(datos.get("modo_documento") or datos.get("paginas_documento") or esquema == "reconstruccion")
        if not secciones and not resumen and not es_modo_doc:
            log.warning("El documento no contiene 'resumen' ni 'secciones': el reporte quedará vacío.")

        fuentes = self._descubrir_fuentes()
        ahora = datetime.now()
        try:
            from jinja2 import __version__ as v_jinja
        except ImportError:  # pragma: no cover
            v_jinja = "?"

        return {
            "modo_documento": es_modo_doc,
            "paginas_documento": datos.get("paginas_documento", []),
            "meta": meta,
            "resumen": resumen,
            "resumen_plano": re.sub(r"[`*]", "", " ".join(resumen)),
            "secciones": secciones,
            "fuentes": fuentes,
            "fuente_principal": _txt((datos.get("meta") or {}).get("fuente")) or (fuentes[0]["familia"] if fuentes else ""),
            "estadisticas": {
                "secciones": len(secciones),
                "tablas": self.contadores["tabla"],
                "figuras": self.contadores["figura"],
                "codigos": self.contadores["codigo"],
            },
            "generacion": {
                "fecha": ahora.strftime("%Y-%m-%d %H:%M"),
                "fecha_iso": ahora.isoformat(timespec="seconds"),
                "generador": f"compilador.py (Jinja2 {v_jinja} + WeasyPrint)",
                "archivo_datos": archivo_datos.name,
                "esquema": esquema,
            },
        }

    # -- Meta ----------------------------------------------------------------
    def _meta(self, m: dict) -> dict:
        if not isinstance(m, dict):
            raise PrecondicionError("'meta' debe ser un objeto JSON.")
        meta = {
            "titulo": _txt(m.get("titulo")) or "Reporte técnico",
            "subtitulo": _txt(m.get("subtitulo")),
            "tipo_documento": _txt(m.get("tipo_documento")) or "Reporte técnico",
            "version": _txt(m.get("version")) or "1.0",
            "fecha": _formatear_fecha(m.get("fecha")),
            "autor": _txt(m.get("autor")),
            "organizacion": _txt(m.get("organizacion")),
            "estado": _txt(m.get("estado")),
            "clasificacion": _txt(m.get("clasificacion")) or "Uso interno",
            "codigo": _txt(m.get("codigo_documento") or m.get("codigo")),
            "idioma": _txt(m.get("idioma")) or "es",
            "palabras_clave": [_txt(k) for k in (m.get("palabras_clave") or []) if _txt(k)],
        }
        meta["ficha"] = [(etiqueta, valor) for etiqueta, valor in (
            ("Versión", meta["version"]), ("Fecha", meta["fecha"]), ("Autor", meta["autor"]),
            ("Organización", meta["organizacion"]), ("Estado", meta["estado"]),
            ("Código", meta["codigo"]), ("Clasificación", meta["clasificacion"]),
        ) if valor]
        meta["pie_izquierdo"] = " · ".join(v for v in (meta["codigo"], meta["organizacion"]) if v)
        return meta

    # -- Secciones -----------------------------------------------------------
    def _seccion(self, s: Any, numero: int) -> dict:
        loc = f"secciones[{numero - 1}]"
        if not isinstance(s, dict):
            raise PrecondicionError(f"{loc}: cada sección debe ser un objeto con 'titulo' y 'bloques'.")
        bloques_in = s.get("bloques") or []
        if not isinstance(bloques_in, list):
            raise PrecondicionError(f"{loc}.bloques debe ser una lista.")

        sub = Counter()
        bloques = []
        for j, b in enumerate(bloques_in):
            normalizado = self._bloque(b, f"{loc}.bloques[{j}]", numero, sub)
            if normalizado:
                bloques.append(normalizado)
        return {
            "id": f"sec-{numero}",
            "numero": str(numero),
            "titulo": _txt(s.get("titulo")) or f"Sección {numero}",
            "nueva_pagina": bool(s.get("nueva_pagina")),
            "bloques": bloques,
        }

    def _bloque(self, b: Any, loc: str, num_seccion: int, sub: Counter) -> dict | None:
        if isinstance(b, str):
            b = {"tipo": "parrafo", "texto": b}
        if not isinstance(b, dict):
            raise PrecondicionError(f"{loc}: bloque inválido (se esperaba objeto o texto).")
        tipo = _txt(b.get("tipo")).lower()
        manejador = getattr(self, f"_b_{tipo}", None)
        if manejador is None:
            log.warning("%s: tipo de bloque desconocido '%s' (se omite).", loc, tipo or "<vacío>")
            return None
        if tipo == "subtitulo":
            sub["n"] += 1
            return manejador(b, loc, f"{num_seccion}.{sub['n']}")
        return manejador(b, loc)

    def _b_parrafo(self, b: dict, loc: str) -> dict:
        return {"tipo": "parrafo", "texto": _txt(b.get("texto"))}

    def _b_subtitulo(self, b: dict, loc: str, numero: str) -> dict:
        return {"tipo": "subtitulo", "numero": numero, "texto": _txt(b.get("texto") or b.get("titulo")),
                "id": f"sec-{numero.replace('.', '-')}"}

    def _b_lista(self, b: dict, loc: str) -> dict:
        elementos = self._items(b.get("items"), loc)
        if not elementos:
            log.warning("%s: lista sin elementos.", loc)
        # Clave 'elementos' (no 'items'): en Jinja2 `x.items` resolvería al método dict.items
        return {"tipo": "lista", "ordenada": bool(b.get("ordenada")), "elementos": elementos}

    def _items(self, items: Any, loc: str) -> list[dict]:
        salida = []
        for it in items or []:
            if isinstance(it, dict):
                salida.append({"texto": _txt(it.get("texto")), "elementos": self._items(it.get("items"), loc)})
            else:
                salida.append({"texto": _txt(it), "elementos": []})
        return salida

    def _b_tabla(self, b: dict, loc: str) -> dict:
        columnas_in = b.get("columnas") or []
        if not columnas_in:
            raise PrecondicionError(f"{loc}: la tabla requiere 'columnas'.")
        columnas = []
        for c in columnas_in:
            if isinstance(c, dict):
                columnas.append({
                    "titulo": _txt(c.get("titulo")),
                    "alineacion": ALINEACIONES.get(_txt(c.get("alineacion")).lower(), "left"),
                    "ancho": self._longitud_css(c.get("ancho"), "", loc),
                })
            else:
                columnas.append({"titulo": _txt(c), "alineacion": "left", "ancho": ""})

        n = len(columnas)
        filas = []
        for i, fila in enumerate(b.get("filas") or []):
            if isinstance(fila, dict):  # Fila como objeto {titulo_columna: valor}
                fila = [fila.get(c["titulo"], "") for c in columnas]
            if not isinstance(fila, list):
                raise PrecondicionError(f"{loc}.filas[{i}]: cada fila debe ser lista u objeto.")
            celdas = [_txt(x) for x in fila]
            if len(celdas) != n:
                log.warning("%s.filas[%d]: %d celdas para %d columnas (se ajusta).", loc, i, len(celdas), n)
                celdas = (celdas + [""] * n)[:n]
            filas.append(celdas)

        self.contadores["tabla"] += 1
        return {
            "tipo": "tabla", "numero": self.contadores["tabla"], "titulo": _txt(b.get("titulo")),
            "columnas": columnas, "filas": filas, "nota": _txt(b.get("nota")),
            "dividir": bool(b.get("dividir")),
        }

    def _b_codigo(self, b: dict, loc: str) -> dict:
        contenido = b.get("contenido", "")
        if b.get("archivo"):  # Código externo dentro de la carpeta de origen
            ruta = self.resolutor.ruta_absoluta(_txt(b["archivo"]))
            if not ruta.is_file():
                raise PrecondicionError(f"{loc}: archivo de código no encontrado: {ruta}")
            contenido = ruta.read_text(encoding="utf-8")
        if isinstance(contenido, list):
            contenido = "\n".join(str(linea) for linea in contenido)
        contenido = textwrap.dedent(str(contenido).expandtabs(4)).strip("\n")
        self.contadores["codigo"] += 1
        return {
            "tipo": "codigo", "lenguaje": _txt(b.get("lenguaje")) or "texto",
            "titulo": _txt(b.get("titulo")), "lineas": contenido.split("\n"),
            "numerar": b.get("numerar_lineas", True) is not False,
        }

    def _b_figura(self, b: dict, loc: str) -> dict:
        imagen = _txt(b.get("imagen") or b.get("src"))
        if not imagen:
            raise PrecondicionError(f"{loc}: la figura requiere 'imagen' (ruta relativa a --origen).")
        src, existe = self.resolutor.resolver(imagen)
        self.contadores["figura"] += 1
        return {
            "tipo": "figura", "numero": self.contadores["figura"], "src": src, "ruta_declarada": imagen,
            "existe": existe, "pie": _txt(b.get("pie")), "alt": _txt(b.get("alt")) or _txt(b.get("pie")) or imagen,
            "fuente": _txt(b.get("fuente")), "ancho": self._longitud_css(b.get("ancho"), "85%", loc),
            "pagina_completa": bool(b.get("pagina_completa")),
        }

    def _b_nota(self, b: dict, loc: str) -> dict:
        nivel = _txt(b.get("nivel")).lower() or "info"
        if nivel not in NIVELES_NOTA:
            log.warning("%s: nivel de nota '%s' no válido, se usa 'info'.", loc, nivel)
            nivel = "info"
        return {"tipo": "nota", "nivel": nivel, "titulo": _txt(b.get("titulo")) or NIVELES_NOTA[nivel],
                "texto": _txt(b.get("texto"))}

    # -- Utilidades ----------------------------------------------------------
    @staticmethod
    def _longitud_css(valor: Any, defecto: str, loc: str) -> str:
        texto = _txt(valor)
        if not texto:
            return defecto
        if RE_LONGITUD_CSS.match(texto):
            return texto
        log.warning("%s: longitud CSS inválida '%s', se usa '%s'.", loc, texto, defecto or "auto")
        return defecto

    def _descubrir_fuentes(self) -> list[dict]:
        """Registra fuentes de <origen>/fuentes/ como @font-face con rutas relativas al HTML."""
        carpeta = self.resolutor.origen / CARPETA_FUENTES
        if not carpeta.is_dir():
            return []
        fuentes = []
        for archivo in sorted(carpeta.iterdir()):
            formato = EXTENSIONES_FUENTE.get(archivo.suffix.lower())
            if not formato:
                continue
            familia, _, variante = archivo.stem.partition("-")
            variante = variante.lower().replace("_", "").replace(" ", "")
            estilo = "italic" if "italic" in variante else "normal"
            variante = variante.replace("italic", "") or "regular"
            src, _ = self.resolutor.resolver(f"{CARPETA_FUENTES}/{archivo.name}")
            fuentes.append({"familia": familia, "src": src, "formato": formato,
                            "peso": PESOS_FUENTE.get(variante, 400), "estilo": estilo})
        if fuentes:
            log.info("Fuentes locales registradas: %s", ", ".join(sorted({f["familia"] for f in fuentes})))
        return fuentes


# ════════════════════════════════════════════════════════════════════════════
# FASE 1 - Generación de HTML
# ════════════════════════════════════════════════════════════════════════════

def renderizar_plantilla(plantilla: Path, contexto: dict) -> str:
    try:
        from jinja2 import (Environment, FileSystemLoader, StrictUndefined, TemplateError,
                            TemplateSyntaxError, select_autoescape)
    except ImportError as exc:
        raise CompiladorError("Jinja2 no está instalado. Ejecute: pip install jinja2") from exc

    entorno = Environment(
        loader=FileSystemLoader(str(plantilla.parent)),
        autoescape=select_autoescape(["html", "htm", "xml"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    entorno.filters["inline"] = filtro_inline
    entorno.filters["css_string"] = filtro_css_string
    try:
        return entorno.get_template(plantilla.name).render(**contexto)
    except TemplateSyntaxError as exc:
        raise CompiladorError(f"Error de sintaxis en la plantilla {exc.filename}:{exc.lineno}: {exc.message}") from exc
    except TemplateError as exc:
        raise CompiladorError(f"Error al renderizar la plantilla {plantilla.name}: {exc}") from exc


def fase_1_html(rutas: Rutas, args: argparse.Namespace) -> None:
    with etapa("FASE 1 · Generación de HTML (Jinja2)"):
        # 1. Precondiciones
        validar_origen(rutas.origen)
        if not rutas.plantilla.is_file():
            raise PrecondicionError(f"No existe la plantilla Jinja2: {rutas.plantilla}")
        archivo = localizar_archivo_datos(rutas.origen, args.datos)
        log.info("[1/4] Origen   : %s", rutas.origen)
        log.info("      Datos    : %s (%s)", archivo.name, _tamano_legible(archivo.stat().st_size))
        log.info("      Plantilla: %s", rutas.plantilla)

        # 2. Carga y normalización
        datos = leer_json(archivo)
        esquema = detectar_esquema(datos)
        log.info("[2/4] Esquema detectado: '%s'", esquema)
        if esquema == "paginas":
            datos = adaptar_paginas_json(
                datos,
                args.limite_paginas,
                getattr(args, "pagina", None),
                origen=rutas.origen,
                dir_html=rutas.html.parent
            )
        elif args.limite_paginas:
            log.warning("--limite-paginas solo aplica al esquema paginas.json (se ignora).")

        resolutor = ResolutorRecursos(rutas.origen, rutas.html.parent)
        contexto = ConstructorContexto(resolutor).construir(datos, archivo, esquema)
        if contexto.get("modo_documento"):
            log.info("[3/4] Contenido: %d páginas reconstruidas fielmente a partir de la extracción",
                     len(contexto.get("paginas_documento", [])))
        else:
            est = contexto["estadisticas"]
            log.info("[3/4] Contenido: %d secciones · %d tablas · %d figuras · %d bloques de código",
                     est["secciones"], est["tablas"], est["figuras"], est["codigos"])
        log.info("      Recursos : %d resueltos · %d faltantes", resolutor.resueltos, len(resolutor.faltantes))
        if resolutor.faltantes and args.estricto:
            raise PrecondicionError(f"Modo estricto: {len(resolutor.faltantes)} recurso(s) no encontrado(s).")

        # 3. Render y escritura
        html = renderizar_plantilla(rutas.plantilla, contexto)
        try:
            rutas.html.parent.mkdir(parents=True, exist_ok=True)
            rutas.html.write_text(html, encoding="utf-8")
        except OSError as exc:
            raise CompiladorError(f"No se pudo escribir el HTML en {rutas.html}: {exc}") from exc
        log.info("[4/4] HTML generado: %s (%s)", rutas.html, _tamano_legible(rutas.html.stat().st_size))
        log.info("      Previsualizar: %s", rutas.html.as_uri())


# ════════════════════════════════════════════════════════════════════════════
# FASE 2 - Compilación a PDF
# ════════════════════════════════════════════════════════════════════════════

class _MonitorWeasyPrint(logging.Handler):
    """Cuenta avisos de WeasyPrint y aísla los relativos a recursos no cargados."""

    RE_RECURSO = re.compile(r"(?i)failed to (load|fetch)|unable to|not found|no such file|cannot")

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.avisos = 0
        self.recursos: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.avisos += 1
        if self.RE_RECURSO.search(record.getMessage()):
            self.recursos.append(record.getMessage())


def _preparar_dlls_windows() -> None:
    """En Windows, apunta WeasyPrint a instalaciones comunes de Pango/GTK si no se configuró."""
    if os.name != "nt" or os.environ.get("WEASYPRINT_DLL_DIRECTORIES"):
        return
    candidatos = [
        Path(r"C:\msys64\mingw64\bin"), Path(r"C:\msys64\ucrt64\bin"),
        Path(r"C:\Program Files\GTK3-Runtime Win64\bin"),
    ]
    encontrados = [str(p) for p in candidatos if (p / "libgobject-2.0-0.dll").is_file()]
    if encontrados:
        os.environ["WEASYPRINT_DLL_DIRECTORIES"] = os.pathsep.join(encontrados)
        log.debug("WEASYPRINT_DLL_DIRECTORIES=%s", os.environ["WEASYPRINT_DLL_DIRECTORIES"])


def importar_weasyprint():
    _preparar_dlls_windows()
    try:
        import weasyprint  # noqa: F401  (import diferido: la Fase 1 no lo requiere)
        from weasyprint import HTML
    except ImportError as exc:
        raise CompiladorError("WeasyPrint no está instalado. Ejecute: pip install weasyprint") from exc
    except OSError as exc:
        primera_linea = str(exc).strip().splitlines()[0]
        raise CompiladorError(
            "WeasyPrint no pudo cargar sus librerías nativas (Pango/GObject).\n"
            f"           Detalle: {primera_linea}\n"
            "           Windows: instale MSYS2 (https://www.msys2.org), ejecute\n"
            "             pacman -S mingw-w64-x86_64-pango\n"
            "           y defina WEASYPRINT_DLL_DIRECTORIES=C:\\msys64\\mingw64\\bin\n"
            "           Linux/macOS: instale 'pango' con el gestor de paquetes del sistema."
        ) from exc
    log.info("WeasyPrint %s cargado", weasyprint.__version__)
    logging.getLogger("weasyprint").setLevel(logging.WARNING)
    logging.getLogger("weasyprint.progress").setLevel(logging.INFO)
    return HTML


def _advertir_html_desactualizado(rutas: Rutas, nombre_datos: str | None) -> None:
    if not rutas.origen.is_dir():
        return
    for nombre in ((nombre_datos,) if nombre_datos else ARCHIVOS_DATOS):
        datos = rutas.origen / nombre
        if datos.is_file() and datos.stat().st_mtime > rutas.html.stat().st_mtime:
            log.warning("%s es más reciente que %s: el PDF podría quedar desactualizado "
                        "(ejecute --fase all para regenerar).", datos.name, rutas.html.name)
            return


def fase_2_pdf(rutas: Rutas, args: argparse.Namespace) -> None:
    with etapa("FASE 2 · Compilación a PDF (WeasyPrint)"):
        # 1. Precondiciones
        if not rutas.html.is_file():
            raise PrecondicionError(
                f"No existe el HTML de entrada: {rutas.html}\n"
                f"           Genérelo primero con: python compilador.py --fase 1 --origen \"{rutas.origen}\""
            )
        if rutas.html.stat().st_size == 0:
            raise PrecondicionError(f"El HTML de entrada está vacío: {rutas.html}")
        _advertir_html_desactualizado(rutas, args.datos)

        HTML = importar_weasyprint()
        base_url = rutas.html.parent.as_uri() + "/"
        log.info("[1/3] HTML de entrada: %s", rutas.html)
        log.info("      base_url       : %s", base_url)

        # 2. Maquetación
        monitor = _MonitorWeasyPrint()
        logger_wp = logging.getLogger("weasyprint")
        logger_wp.addHandler(monitor)
        try:
            t0 = time.perf_counter()
            documento = HTML(filename=str(rutas.html), base_url=base_url).render()
            log.info("[2/3] Maquetación completa: %d páginas (%.2f s)",
                     len(documento.pages), time.perf_counter() - t0)
        except Exception as exc:
            raise CompiladorError(f"WeasyPrint falló al maquetar el HTML: {exc}") from exc
        finally:
            logger_wp.removeHandler(monitor)

        if monitor.recursos:
            log.warning("WeasyPrint no pudo cargar %d recurso(s) referenciado(s).", len(monitor.recursos))
            if args.estricto:
                raise PrecondicionError("Modo estricto: existen recursos no resueltos en el HTML.")

        # 3. Escritura atómica (evita PDFs corruptos si falla a mitad de camino)
        temporal = rutas.pdf.with_name(rutas.pdf.name + ".tmp")
        try:
            rutas.pdf.parent.mkdir(parents=True, exist_ok=True)
            documento.write_pdf(str(temporal))
            os.replace(temporal, rutas.pdf)
        except PermissionError as exc:
            temporal.unlink(missing_ok=True)
            raise CompiladorError(
                f"Sin permiso para escribir {rutas.pdf}. ¿Está abierto en un visor de PDF? ({exc})"
            ) from exc
        except OSError as exc:
            temporal.unlink(missing_ok=True)
            raise CompiladorError(f"No se pudo escribir el PDF {rutas.pdf}: {exc}") from exc

        log.info("[3/3] PDF generado: %s (%s, %d páginas, %d aviso(s) de WeasyPrint)",
                 rutas.pdf, _tamano_legible(rutas.pdf.stat().st_size), len(documento.pages), monitor.avisos)


# ════════════════════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════════════════════

EJEMPLOS = """\
ejemplos:
  python compilador.py --fase 1   --origen ejemplo_reporte
  python compilador.py --fase 2   --origen ejemplo_reporte --salida informe_arquitectura.pdf
  python compilador.py --fase all --origen ejemplo_reporte --salida salidas/informe.pdf
  python compilador.py --origen output/goanywhere_mft_user_guide_7_7_0 --limite-paginas 25
"""


def _entero_positivo(valor: str) -> int:
    try:
        n = int(valor)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{valor}' no es un entero") from None
    if n <= 0:
        raise argparse.ArgumentTypeError("debe ser mayor que 0")
    return n


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compilador.py",
        description="Compila reportes técnicos en dos fases: (1) JSON -> HTML con Jinja2, (2) HTML -> PDF con WeasyPrint.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EJEMPLOS,
    )
    parser.add_argument("--fase", type=str.lower, choices=("1", "2", "all"), default="all",
                        help="1 = solo HTML · 2 = solo PDF desde el HTML existente · all = 1 y luego 2 (defecto: all)")
    parser.add_argument("--origen", default=ORIGEN_POR_DEFECTO,
                        help=f"Carpeta de extracción con datos.json/paginas.json e imágenes (defecto: '{ORIGEN_POR_DEFECTO}', "
                             "configurable con la variable COMPILADOR_ORIGEN)")
    parser.add_argument("--salida", default=None,
                        help=f"PDF final. Solo nombre -> se crea dentro de --origen; ruta -> se usa tal cual "
                             f"(defecto: <origen>/{NOMBRE_PDF_POR_DEFECTO})")
    parser.add_argument("--html", default=None,
                        help=f"HTML intermedio producido por la Fase 1 y consumido por la Fase 2 "
                             f"(defecto: <origen>/{NOMBRE_HTML_PREVIEW})")
    parser.add_argument("--plantilla", default=PLANTILLA_POR_DEFECTO,
                        help="Plantilla Jinja2 (defecto: plantilla.html junto al script)")
    parser.add_argument("--datos", default=None,
                        help=f"Archivo JSON dentro de --origen (defecto: autodetecta {' -> '.join(ARCHIVOS_DATOS)})")
    parser.add_argument("--limite-paginas", type=_entero_positivo, default=None,
                        help="Solo paginas.json: incluye únicamente las primeras N páginas")
    parser.add_argument("--pagina", type=_entero_positivo, default=None,
                        help="Compila únicamente la página especificada (ej: --pagina 43). Genera preview_pagina_XXXX.html")
    parser.add_argument("--estricto", action="store_true",
                        help="Aborta si hay imágenes/fuentes referenciadas que no existen")
    parser.add_argument("-v", "--verbose", action="store_true", help="Logs de depuración")
    return parser


def _forzar_utf8_consola() -> None:
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _forzar_utf8_consola()
    args = construir_parser().parse_args(argv)
    configurar_logging(args.verbose)
    rutas = resolver_rutas(args)

    log.info("Compilador de reportes técnicos · fase=%s", args.fase)
    log.info("  origen : %s", rutas.origen)
    log.info("  html   : %s", rutas.html)
    if args.fase in ("2", "all"):
        log.info("  salida : %s", rutas.pdf)

    t0 = time.perf_counter()
    try:
        if args.fase in ("1", "all"):
            fase_1_html(rutas, args)
        if args.fase in ("2", "all"):
            fase_2_pdf(rutas, args)
    except CompiladorError as exc:
        log.error("%s", exc)
        if args.fase == "all" and not rutas.pdf.exists():
            log.error("Proceso abortado: no se generó el PDF.")
        return exc.exit_code
    except KeyboardInterrupt:
        log.error("Proceso interrumpido por el usuario.")
        return EXIT_INTERRUMPIDO
    except Exception:  # noqa: BLE001 - último recurso con traceback completo
        log.exception("Error inesperado")
        return EXIT_ERROR

    log.info("=" * 72)
    log.info("Proceso completado en %.2f s", time.perf_counter() - t0)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
