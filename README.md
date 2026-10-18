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

### 2. Compilación del Documento Completo (`compilador.py`)

Genera la vista previa HTML consolidada o el PDF imprimible:

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

### 3. Diagnóstico y Re-proceso de Páginas Puntuales (`gestor_pagina.py`)

Cuando se detecta un detalle en una página específica (ej. página 43, 105, 250), se utiliza esta herramienta para trabajar de forma aislada e instantánea sin compilar las 100+ páginas:

```powershell
# A. Inspeccionar el texto extraído de una página puntual
.\.venv\Scripts\python.exe gestor_pagina.py --pagina 43 --ver-texto

# B. Generar vista previa HTML aislada (preview_pagina_0043.html en ~0.2 segundos)
.\.venv\Scripts\python.exe gestor_pagina.py --pagina 43 --preview

# C. Re-extraer quirúrgicamente la página desde el JSONP oficial y actualizar paginas.json
.\.venv\Scripts\python.exe gestor_pagina.py --pagina 43 --extraer

# D. Sincronizar e integrar los cambios en el documento maestro preview.html
.\.venv\Scripts\python.exe gestor_pagina.py --pagina 43 --integrar

# E. Flujo completo automático para una página (extraer + preview individual + integrar)
.\.venv\Scripts\python.exe gestor_pagina.py --pagina 43 --auto
```

También se puede previsualizar cualquier página puntual directamente con `compilador.py`:
```powershell
.\.venv\Scripts\python.exe compilador.py --fase 1 --pagina 43 --origen reporte/goanywhere_mft_user_guide_7_7_0
```

---

## 🔍 Criterios de Calidad y Puntos de Revisión

Al generar o validar páginas técnicas en el rango **100+**, verifique siempre:

1. **Multi-Capa en Scribd:** Cajas flotantes (`WARNING:`, `TIP:`, `NOTE:`) generan contenedores `<div class="text_layer">` adicionales. El extractor procesa todas las capas automáticamente.
2. **Desfragmentación de Glifos:** Palabras con microespacios (ej. `f ormat`, `Actio n`, `GetLicense`) son corregidas automáticamente por el motor léxico en `compilador.py`.
3. **Hipervínculos (`doc-link`):** Toda URL o referencia de soporte se renderiza con el color corporativo `#006a56`, subrayado e interactivo.
4. **Continuidad de Párrafos:** Frases que contienen saltos de línea internos no deben dividirse en subtítulos `<h2>` espurios.

---

## 📁 Estructura del Repositorio

```
c:\IA_Proyectos\botScribd\
├── compilador.py               # Motor Jinja2/WeasyPrint con soporte para páginas completas y aisladas
├── gestor_pagina.py            # CLI unipágina: extracción puntual, preview aislado e integración
├── main.py                     # Orquestador de extracción masiva desde insumos locales
├── plantilla.html              # Plantilla editorial A4/Carta con diseño corporativo GoAnywhere
├── config.py                   # Modelos de configuración y argumentos CLI
├── core/
│   ├── extractor.py            # Extractor con soporte multi-capa text_layer
│   ├── insumo_parser.py        # Parser de insumos HTML y descarga de chunks JSONP
│   └── insumo_renderer.py      # Renderizador Playwright a escala Retina 2x
├── insumo/                     # Archivos HTML y carpetas _files/ descargadas de Scribd
└── reporte/
    └── goanywhere_mft_user_guide_7_7_0/
        ├── paginas.json        # Índice estructurado con texto e imágenes por página
        ├── preview.html        # Documento maestro consolidado
        └── preview_pagina_*.html # Vistas previas aisladas por página para auditoría rápida
```
