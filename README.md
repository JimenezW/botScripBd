# Bot de Extracción y Reconstrucción en Scribd (100% Sin Login)

Bot automatizado en Python para extraer y reconstruir documentos técnicos completos alojados en Scribd, sin requerir credenciales ni inicio de sesión. Diseñado con evasión stealth de WAFs, gestión autónoma de anuncios publicitarios (*Ad-Gate*) y generación dual de salidas: **PDF 1:1 de Alta Resolución (con imágenes originales y texto buscable)** y **Markdown enriquecido**.

---

## Características Principales

* **100% Sin Login:** Recorre documentos completos aprovechando los controles de avance y omitiendo ventanas de publicidad intermedias.
* **Preservación Total de Imágenes:** Descarga del CDN las imágenes de alta resolución de cada página (diagramas, capturas de pantalla, tablas y esquemas).
* **Compilación Dual:**
  * **PDF 1:1 Searchable:** Reconstrucción idéntica al original con capa de texto invisible para selección y búsqueda.
  * **Markdown Enriquecido:** Texto estructurado con enlaces relativos a las imágenes locales de cada página.
* **Evasión WAF Antidetección:** Integración con `playwright-stealth`, eliminación de flags de automatización y retardos humanos con *jitter*.
* **Parametrizable:** Acepta cualquier URL de Scribd mediante CLI o archivos de procesamiento por lotes (*batch*).
* **Persistencia Incremental:** Guarda el progreso en caliente para evitar pérdida de datos ante desconexiones.

---

## Requisitos e Instalación

1. **Python 3.10 o superior.**
2. Crear y activar el entorno virtual:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Instalar dependencias y los binarios de Chromium:
   ```powershell
   pip install -r requirements.txt
   playwright install chromium
   ```

---

## Modos de Uso

### 1. Extracción de Documento Individual (URL Parametrizable)
```powershell
.\.venv\Scripts\python.exe main.py --url https://es.scribd.com/document/855660163/ga7-7-0-user-guide
```

### 2. Prueba Rápida con Límite de Páginas (ej. primeras 5 páginas)
```powershell
.\.venv\Scripts\python.exe main.py --url https://es.scribd.com/document/855660163/ga7-7-0-user-guide --max-pages 5
```

### 3. Modo Visible para Depuración (Navegador Gráfico en Pantalla)
```powershell
.\.venv\Scripts\python.exe main.py --url https://es.scribd.com/document/855660163/ga7-7-0-user-guide --no-headless
```

### 4. Procesamiento por Lotes (Múltiples Documentos)
Crea un archivo `urls.txt` con una URL por línea y ejecuta:
```powershell
.\.venv\Scripts\python.exe main.py --batch urls.txt
```

---

## Estructura de Salida

Cada documento extraído se almacena de forma aislada en la carpeta `output/`:

```
output/
└── 855660163_ga7-7-0-user-guide/
    ├── ga7-7-0-user-guide.pdf     <-- PDF idéntico con imágenes y texto buscable
    ├── contenido.md               <-- Markdown con texto y diagramas vinculados
    ├── paginas.json               <-- JSON con líneas y metadatos por página
    ├── metadata.json              <-- Estadísticas de extracción y tiempos
    └── imagenes/                  <-- Imágenes y diagramas descargados en alta resolución
        ├── pag_001_img_1.webp
        ├── pag_002_img_1.webp
        └── ...
```

---

## Estructura del Código

```
c:\IA_Proyectos\botScribd\
├── config.py                 # Parámetros, argumentos CLI y normalizador de URLs
├── core/
│   ├── browser.py            # Motor Playwright Stealth y gestión de cookies
│   ├── navigator.py          # Controlador de paginación e inputs de salto
│   ├── ad_gate.py            # Detector de temporizadores y botón 'Omitir anuncio'
│   ├── extractor.py          # Extractor de .text_layer e .image_layer del CDN
│   ├── pdf_builder.py        # Compilador de PDF 1:1 con texto invisible
│   └── exporter.py           # Generador de Markdown enriquecido y JSON
├── main.py                   # Orquestador con barra de progreso Rich
└── requirements.txt          # Dependencias del proyecto
```
