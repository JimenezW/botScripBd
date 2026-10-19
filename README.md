# Bot de Extracción, Auditoría y Reconstrucción en Scribd (100% Sin Login)

Sistema integral en Python para extraer, auditar, depurar y reconstruir documentos técnicos de Scribd en alta fidelidad (tamaño carta / A4), preservando la totalidad de texto, diagramas, capturas Retina 2x y estructura corporativa (como el manual *GoAnywhere MFT User Guide*).

---

## 🚀 Arquitectura y Componentes del Sistema

1. **Extractor Offline de Insumos (`main.py`):**
   Procesa archivos HTML guardados en `insumo/`, descarga payloads JSONP oficiales, extrae todas las capas vectoriales y tipográficas (`text_layer`), y genera imágenes nítidas Retina 2x junto con el catálogo `paginas.json`.
2. **Compilador de Fidelidad Editorial (`compilador.py`):**
   Reconstruye páginas idénticas al original usando Jinja2 (`plantilla.html`) y CSS Paged Media. Soporta portadas completas, tabla de contenidos dual con puntos guía, encabezados móviles alternos, bloques `WARNING:`, `TIP:`, viñetas y pasos numerados con enlaces activos.
3. **Gestor y Auditor Unipágina (`gestor_pagina.py`):**
   Permite diagnosticar, re-extraer, previsualizar en 0.2 segundos y sincronizar páginas individuales sin requerir la re-ejecución masiva de todo el libro (esencial para la escala de páginas 100 a 3,720).

4. **Extractor de Figuras y Diagramas (`extractor_figuras.py`):**
   Inspecciona las capas `image_layer` de los JSONPs de Scribd y los archivos atlas locales. Aplica detección geométrica estricta de contornos de 4 bordes para aislar capturas UI, diagramas de arquitectura y formularios en resolución nativa, desacoplando rebanadas compuestas y almacenando las imágenes en `output/.../figuras/` junto con su índice independiente `figuras_paginas.json`.

---

## ⚙️ Instalación y Requisitos

1. **Python 3.10 o superior.**
2. Crear y activar el entorno virtual en Windows PowerShell:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Instalar dependencias del proyecto:
   ```powershell
   pip install -r requirements.txt
   playwright install chromium
   ```

---

## 📖 Guía de Ejecución para Futuros Usos

### 1. Extracción Masiva desde Insumos Locales (`main.py`)

Procesa los archivos HTML descargados en `insumo/` y genera las imágenes 2x y el catálogo `paginas.json`:

```powershell
# Extraer todas las páginas catalogadas en el insumo
.\.venv\Scripts\python.exe main.py

# Prueba controlada con límite de páginas (ej. primeras 100 páginas)
.\.venv\Scripts\python.exe main.py --max-pages 100

# Indicar ruta específica de insumo y salida
.\.venv\Scripts\python.exe main.py --insumo "insumo/documento.html" --output-dir "output"
```

---

### 2. Extracción de Figuras y Diagramas UI (`extractor_figuras.py`)

Extrae y recorta quirúrgicamente todas las capturas de pantalla, diagramas y formularios UI sin mezclar datos con el texto, almacenándolos en `output/goanywhere_mft_user_guide_7_7_0/figuras/` y catalogándolos en `figuras_paginas.json`:

```powershell
# A. Extraer figuras de un rango de páginas (ej. primeras 100 páginas de validación)
.\.venv\Scripts\python.exe extractor_figuras.py --desde 1 --hasta 100

# B. Extracción completa de todas las páginas del libro (1 a 3,712)
.\.venv\Scripts\python.exe extractor_figuras.py --desde 1 --hasta 3712

# C. Extraer o actualizar exclusivamente las figuras de una página puntual
.\.venv\Scripts\python.exe extractor_figuras.py --pagina 57
```

**Criterios de Calidad del Extractor de Figuras:**
- **Cierre Rectangular Estricto (4 Bordes):** Requiere `ratio_left >= 60%` y `ratio_right >= 60%`, eliminando automáticamente texto con formato, títulos decorativos o enlaces aislados.
- **Desacople de Rebanadas Múltiples:** Cuando Scribd agrupa dos o más cuadros UI en la misma rebanada (ej. pág. 57), el algoritmo las separa recortando estrictamente cada caja desde su borde superior a su borde inferior, sin arrastrar texto exterior.
- **Supresión de Callouts Tintados:** Descarta automáticamente cajas de `WARNING:`, `TIP:` o `NOTE:` con fondos de color homogéneo para que no se dupliquen con las cajas tipográficas del compilador HTML.
- **Diagramas de Arquitectura:** Reconoce diagramas grandes complejos (ej. pág. 39) por su contenido gráfico cromático y alta varianza.

---

### 3. Diagnóstico y Re-proceso Unipágina (`gestor_pagina.py`)

Cuando se detecta un detalle en una página específica (ej. página 43, 57, 84, 105), se utiliza esta herramienta para auditarla, re-extraerla o previsualizarla de forma instantánea:

```powershell
# A. Extraer quirúrgicamente las figuras de una página puntual manualmente
.\.venv\Scripts\python.exe gestor_pagina.py --pagina 57 --figuras

# B. Inspeccionar el texto extraído de una página puntual
.\.venv\Scripts\python.exe gestor_pagina.py --pagina 43 --ver-texto

# C. Generar vista previa HTML aislada (preview_pagina_0043.html en ~0.2 segundos)
.\.venv\Scripts\python.exe gestor_pagina.py --pagina 43 --preview

# D. Re-extraer quirúrgicamente la página desde el JSONP oficial y actualizar paginas.json
.\.venv\Scripts\python.exe gestor_pagina.py --pagina 43 --extraer

# E. Sincronizar e integrar los cambios en el documento maestro preview.html
.\.venv\Scripts\python.exe gestor_pagina.py --pagina 43 --integrar

# F. Flujo completo automático para una página (extraer + preview individual + integrar)
.\.venv\Scripts\python.exe gestor_pagina.py --pagina 43 --auto
```

---

### 4. Compilación del Documento Completo (`compilador.py`)

Genera la vista previa HTML consolidada o el PDF imprimible incorporando las figuras catalogadas:

```powershell
# Fase 1: Generar HTML consolidado (preview.html)
.\.venv\Scripts\python.exe compilador.py --fase 1 --origen reporte/goanywhere_mft_user_guide_7_7_0

# Fase 1 con límite de páginas para pruebas rápidas
.\.venv\Scripts\python.exe compilador.py --fase 1 --origen reporte/goanywhere_mft_user_guide_7_7_0 --limite-paginas 50

# Fase 2: Compilar PDF final con WeasyPrint
.\.venv\Scripts\python.exe compilador.py --fase 2 --origen reporte/goanywhere_mft_user_guide_7_7_0 --salida "manual_goanywhere.pdf"

# Compilar ambas fases (HTML + PDF)
.\.venv\Scripts\python.exe compilador.py --fase all --origen reporte/goanywhere_mft_user_guide_7_7_0
```

---

## 🔍 Criterios de Calidad y Puntos de Revisión

Al generar o validar páginas técnicas en el rango **100+**, verifique siempre:

1. **Multi-Capa en Scribd:** Cajas flotantes (`WARNING:`, `TIP:`, `NOTE:`) generan contenedores `<div class="text_layer">` adicionales. El extractor procesa todas las capas automáticamente.
2. **Figuras y Diagramas Desacoplados:** Las imágenes no se confunden con bloques de texto y cuentan con sus coordenadas exactas en `figuras_paginas.json`.
3. **Desfragmentación de Glifos:** Palabras con microespacios (ej. `f ormat`, `Actio n`, `GetLicense`) son corregidas automáticamente por el motor léxico en `compilador.py`.
4. **Hipervínculos (`doc-link`):** Toda URL o referencia de soporte se renderiza con el color corporativo `#006a56`, subrayado e interactivo.
5. **Continuidad de Párrafos:** Frases que contienen saltos de línea internos no deben dividirse en subtítulos `<h2>` espurios.

---

## 📁 Estructura del Repositorio

```
c:\IA_Proyectos\botScribd\
├── compilador.py               # Motor Jinja2/WeasyPrint con soporte para páginas completas y aisladas
├── extractor_figuras.py        # Extractor refinado de figuras, diagramas y tarjetas UI (4 bordes)
├── gestor_pagina.py            # CLI unipágina: extracción de texto, figuras (--figuras) y preview
├── main.py                     # Orquestador de extracción masiva desde insumos locales
├── plantilla.html              # Plantilla editorial A4/Carta con diseño corporativo GoAnywhere
├── config.py                   # Modelos de configuración y argumentos CLI
├── core/
│   ├── extractor.py            # Extractor con soporte multi-capa text_layer
│   ├── insumo_parser.py        # Parser de insumos HTML y descarga de chunks JSONP
│   └── insumo_renderer.py      # Renderizador Playwright a escala Retina 2x
├── insumo/                     # Archivos HTML y carpetas _files/ descargadas de Scribd
├── output/
│   └── goanywhere_mft_user_guide_7_7_0/
│       ├── figuras/            # PNGs de figuras y diagramas recortados en alta fidelidad
│       ├── figuras_paginas.json # Catálogo estructurado de figuras y posiciones por página
│       └── paginas.json        # Catálogo general de texto y capas de páginas
└── reporte/
    └── goanywhere_mft_user_guide_7_7_0/
        ├── figuras/            # Copia espejo sincronizada para visualización web
        ├── preview.html        # Documento maestro consolidado
        └── preview_pagina_*.html # Vistas previas aisladas por página para auditoría rápida
```
