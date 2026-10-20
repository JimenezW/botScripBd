# PLAN DE TRABAJO: CALIBRACIÓN Y REPARACIÓN QUIRÚRGICA DE PREVIEW.HTML (PÁGINAS 1 A 3,712)
## Resolución Sistemática de Hallazgos de Auditoría y Segundo Barrido de Calidad

> **Documento Objetivo:** [`reporte/goanywhere_mft_user_guide_7_7_0/preview.html`](file:///c:/IA_Proyectos/botScribd/reporte/goanywhere_mft_user_guide_7_7_0/preview.html) (3,712 páginas compiladas)  
> **Fuentes de Diagnóstico:** [`HALLAZGOS_PREVIEW_HTML_PAGINAS_1_A_3712.md`](file:///c:/IA_Proyectos/botScribd/HALLAZGOS_PREVIEW_HTML_PAGINAS_1_A_3712.md) y [`INFORME_SEGUNDO_BARRIDO_CALIDAD_PREVIEW.md`](file:///c:/IA_Proyectos/botScribd/INFORME_SEGUNDO_BARRIDO_CALIDAD_PREVIEW.md)  
> **Estado de Protección Inicial:** Commit `e3ba333` ("docs: registrar hallazgos de auditoria de preview.html...")  
> **Estrategia General:** Corregir en [`compilador.py`](file:///c:/IA_Proyectos/botScribd/compilador.py) para que la reconstrucción del HTML sea idempotente, limpia y sistemática, validando páginas puntuales antes de compilar la totalidad.

---

## 1. Matriz de Análisis Técnico y Estado de Solución

| ID | Hallazgo | Alcance Original | Causa Raíz | Solución Aplicada en Bot (`compilador.py`) | Estado |
| :---: | :--- | :---: | :--- | :--- | :---: |
| **H-01** | Inversión H1 vs. Figuras | 4 págs (75, 87, 2348, 2480) | En `_intercalar_figuras`, la condición de apertura (`i == 0`) insertaba la figura antes de evaluar la precedencia de `<h1>`. | Precedencia absoluta para `<h1>`: ninguna figura puede anteponerse al encabezado `<h1>` que abre la página. | **RESUELTO [x]** |
| **H-02** | Amontonamiento masivo de figuras al pie | 13 págs (806, 865, 866, 888, 1035, 1202, 1237, 1461, 1602, 1772, 2331-2333) | En páginas con densidad $\ge 3$ figuras y texto compacto, el umbral vertical `top_px` quedaba desfasado del tracking acumulado `y_actual`. | Incorporación de `scale_factor` vertical dinámico basado en la altura física de las figuras y corte anticipado tras oraciones ilustrativas (`The following image...`). | **RESUELTO [x]** |
| **H-03** | Viñetas y pasos mutilados (vacíos) | 2 págs (65, 3137) | Valores numéricos solos (`21.`) en lista se tomaban como pasos; rotura de sufijos (`FIPS 140-` y `2.`). | Validación obligatoria de cuerpo (`texto.strip() != ""`) al emitir `numero` y `subpaso`; purga final de pasos sin contenido textual. | **RESUELTO [x]** |
| **H-04** | Código XML promovido a H2 | 2 págs (3177, 3705) | Cadenas XML/DOCTYPE (`<Server...>`, `<?xml...>`, `<!DOCTYPE...`) cumplían longitud y ausencia de punto final siendo promovidas a `<h2>`. | Detección de sintaxis de etiquetas `^\s*<[/!a-zA-Z\?]` inhibiendo su promoción a encabezado `<h2>` y manteniéndolas en su bloque textual. | **RESUELTO [x]** |
| **H-05** | Párrafos huérfanos con solo puntuación | 63 págs (388, 426, 502, 840, 957, 1083...) | Desglose de hipervínculos aislaba el punto final en una línea independiente que se clasificaba como `<p class="content-p">.</p>`. | Supresión sistemática de párrafos con longitud $\le 2$ compuestos solo de puntuación (`^[.,;:!?\s]+$`), adhiriendo el signo al elemento anterior si procede. | **RESUELTO [x]** |
| **H-06** | Palabras fragmentadas (Rango 701-3712) | 72 págs (`PDFFile`, `Row Set Variable`, `FTPServer`, `S ervers`...) | Ausencia de patrones específicos en el catálogo léxico de Scribd. | Ampliación de `RE_PATRONES_DESFRAGMENTACION` con los 16 términos auditados + normalización en TOC. | **RESUELTO [x]** |
| **H-07** | Duplicación de comas (`,,`) | 8 págs (46, 47, 855, 1655, 1661, 2340, 2404, 3378) | Superposición de spans hijos donde el padre ya cerraba en coma. | Normalización regex `re.sub(r',\s*,+', ', ', res)` en `_reparar_palabras_rotas`. | **RESUELTO [x]** |
| **H-08** | Espacio previo a signos de puntuación | 81 págs (`(Port )`, `field )`, `goanywhere ,`) | Concatenación ciega `" ".join(...)` antes de signos de cierre y apertura. | Filtros tipográficos en `_reparar_palabras_rotas`: `\s+([.,;:!?\)\]])` $\rightarrow$ `\1` y `([(\[{])\s+` $\rightarrow$ `\1`. | **RESUELTO [x]** |
| **H-09** | Glifos iniciales y sufijos rotos | 24 págs (`a pp`, `a nd`, `anoth er`, `RSA Secur ID`) | Kerning de letra inicial `'a'` o división tipográfica de sufijo de 2 letras. | Reglas léxicas en `RE_PATRONES_DESFRAGMENTACION` (`\ba\s+(pp|nd|ll|re|nother)\b`, `\banoth\s+er\b`, etc.). | **RESUELTO [x]** |

---

## 2. Check-List de Ejecución y Validación

### Fase 1: Calibración del Compilador (`compilador.py`)
- [x] **1.1.** Ampliar `RE_PATRONES_DESFRAGMENTACION` con términos técnicos de auditoría (`PDFFile` $\rightarrow$ `PDF File`, `Row Set Variable` $\rightarrow$ `RowSet Variable`, `EDIFACTTransaction`, `FTPServer`, `Forexample`, `S ervers`, `JVMMemory`, `Cop y Task`, `Bloc ked`, `Re gular`, `Un resolved`, `Se cure`, `Softwa re`, `Co ntrol`, `Ex pressions`, `SSL connections`).
- [x] **1.2.** Añadir a `_reparar_palabras_rotas` la normalización tipográfica de comas dobles (`,\s*,+` $\rightarrow$ `, `) y espacios antes de puntuación de cierre (`\s+([,\.\?\)\;\]])` $\rightarrow$ `\1`) y apertura (`([(\[{])\s+` $\rightarrow$ `\1`).
- [x] **1.3.** Añadir reglas de desfragmentación de glifo inicial `'a'` y sufijos rotos (`a pp` $\rightarrow$ `app`, `a nd` $\rightarrow$ `and`, `anoth er` $\rightarrow$ `another`, `th at/is/e`, `RSA Secur ID` $\rightarrow$ `RSA SecurID`).
- [x] **1.4.** Proteger detección de H2 contra fragmentos de código XML (`<Server...>`, `<?xml...>`, `<!DOCTYPE...>`, etc.).
- [x] **1.5.** Eliminar párrafos huérfanos que contengan únicamente signos de puntuación (`.` o `:`).
- [x] **1.6.** Corregir pasos truncados o vacíos (purgar `<div class="content-step">` vacíos y evitar rotura de números como `FIPS 140-` + `2.`).
- [x] **1.7.** Ajustar precedencia en `_intercalar_figuras` para que `<h1>` siempre anteceda a cualquier figura en cabecera de página (págs 75, 87, 2348, 2480).
- [x] **1.8.** Calibrar acumulador vertical `y_actual` en `_intercalar_figuras` para intercalar correctamente figuras en páginas densas (págs 806, 865, 866, 888, 1035, 1202, 1237, 1461, 1602, 1772, 2331-2333).

### Fase 2: Validación Quirúrgica en Páginas Testigos
- [x] **2.1.** Compilar y validar Página 47 (comas dobles resueltas, `app`, `another`, paréntesis cerrados sin espacio).
- [x] **2.2.** Compilar y validar Página 65 y 3137 (pasos vacíos purgados; lista limpia sin marcador falso).
- [x] **2.3.** Compilar y validar Páginas 75 y 87 (precedencia de `<h1>` sobre figura confirmada).
- [x] **2.4.** Compilar y validar Páginas 3177 y 3705 (código XML no promovido a H2, conservado en bloque de contenido).
- [x] **2.5.** Compilar y validar Página 388 (eliminación total de `<p>.</p>`).
- [x] **2.6.** Compilar y validar Páginas 806, 865 y 2331 (distribución armónica de figuras intercaladas).

### Fase 3: Reconstrucción Idempotente del Documento Maestro (`preview.html`)
- [x] **3.1.** Ejecutar `gestor_pagina.py --integrar` sobre el documento completo (3,712 páginas compiladas sincronizadas en 33.02 s).
- [x] **3.2.** Ejecutar auditoría automatizada de verificación sobre las 3,712 páginas de `preview.html`:
  * `<p class="content-p">.</p>`: **0 incidencias** (de 63 originales).
  * Comas dobles `,,`: **0 incidencias** (de 8 originales).
  * Código XML promovido a H2: **0 incidencias** (de 3 originales).
  * Pasos con cuerpo vacío: **0 incidencias** (de 2 originales).
  * Inversión H1 vs Figuras: **0 incidencias** (de 4 originales).
  * Glifos y tokens fragmentados auditados: **0 incidencias** (de 74 originales).
- [x] **3.3.** Proteger el avance con Git commit.

---

## 3. Calibración Adicional: Páginas 3707 y 3708 ("How to Perform a Thread Dump")

| Página | Hallazgo Detectado | Causa Raíz | Solución Aplicada en `compilador.py` | Estado |
| :---: | :--- | :--- | :--- | :---: |
| **3707** | Espaciado roto en path JDK y comando CLI | Scribd colapsa u oscila espacios en `jdk1.8.0_ 191` y `jstack-l[PID]>threaddump.txt`. | Reglas de normalización en `RE_PATRONES_DESFRAGMENTACION` para `jdk1.8.0_191` y `jstack -l [PID] > threaddump.txt`. | **RESUELTO [x]** |
| **3708** | Subtítulo `IBM i` absorbido en párrafo | Umbral mínimo para `<h2>` era `len(l) >= 6`. `'IBM i'` tiene longitud 5, cayendo en el acumulador de párrafos. | Umbral ajustado a `4 <= len(l) < 55` y whitelist explícita para plataformas (`IBM i`, `AIX`, `Unix`, `Linux`, `macOS`). | **RESUELTO [x]** |
| **3708** | Comando CLI y opción sin espacios | `Kill-3[PIDoftomcat]>threaddump.txt` y `option9` sin espacios estándar. | Reglas de normalización en `RE_PATRONES_DESFRAGMENTACION` para `kill -3 [PID of tomcat] > threaddump.txt` y `option 9`. | **RESUELTO [x]** |

- [x] **3707-1.** Validado `preview_pagina_3707.html`: `<h1>How to Perform a Thread Dump</h1>`, `<h2>Windows</h2>`, paso 2 con `jdk1.8.0_191` y paso 3 con `jstack -l [PID] > threaddump.txt`.
- [x] **3708-1.** Validado `preview_pagina_3708.html`: `<h2>Linux and Unix</h2>` con comando `kill -3 [PID of tomcat] > threaddump.txt`, y `<h2 class="content-h2">IBM i</h2>` correctamente clasificado con pasos 1-6 normalizados (`option 9`).
- [x] **3708-2.** Sincronizado en maestro [`reporte/goanywhere_mft_user_guide_7_7_0/preview.html`](file:///c:/IA_Proyectos/botScribd/reporte/goanywhere_mft_user_guide_7_7_0/preview.html).

---

## 4. Tercer Barrido Sistemático Integral (Auditoría Semántica en Páginas 1 a 3,712)

| Caso | Alcance | Causa Raíz | Solución Aplicada en `compilador.py` | Estado |
| :---: | :--- | :--- | :--- | :---: |
| **Comando CLI `setspn`** | Págs 2698, 2699 | Sintaxis de comando pegada (`setspn-s[protocol]...` y `>setspn-sHTTPS`). | Reglas en `RE_PATRONES_DESFRAGMENTACION` para `setspn -s [protocol]` y `> setspn -s HTTPS`. | **RESUELTO [x]** |
| **Ruta/Variable `[AzureBlobStorage]`** | Pág 203 | Colapso léxico `[AzureBlobStorageresourcename]`. | Regla de desfragmentación `[AzureBlobStorage resourcename]`. | **RESUELTO [x]** |
| **Duplicación léxica de glosario y términos** | Págs 594, 2098, 2394, 3642, 3646, 3647 | Spans hijos en capas repetían el término inicial (`Method Calls Method Calls`, `JKS JKS`, `SSH SSH`, `SSL SSL`, `Add Add`). | Desduplicación sistemática en post-procesamiento de `<p>` en `_parsear_contenido_pagina`. | **RESUELTO [x]** |

- [x] **4.1.** Recompilado y sincronizado el documento maestro [`reporte/goanywhere_mft_user_guide_7_7_0/preview.html`](file:///c:/IA_Proyectos/botScribd/reporte/goanywhere_mft_user_guide_7_7_0/preview.html) en 36.25 s.
- [x] **4.2.** Verificación de cero comandos CLI o rutas mutiladas en todo el documento.
- [x] **4.3.** Cambios protegidos bajo control de versiones Git.

---

## 5. Calibración Visual: Páginas con Pestañas de Contactos (Página 331 y análogas)

| Caso | Alcance | Causa Raíz | Solución Aplicada en `compilador.py` | Estado |
| :---: | :--- | :--- | :--- | :---: |
| **Inversión de Figura en `Contacts Tab`** | Pág 331 (y 26 pestañas de recursos con formulario de contactos) | La regla 5 de H2 asignaba figuras inmediatas antes del párrafo descriptivo (*"The Contacts tab allows you..."*), cuando visualmente la figura ilustra el formulario y se ubica debajo de la oración. | Ajuste en Regla 4 y Regla 5 de `_intercalar_figuras` para que `Contacts Tab` postergue la figura y la ancle inmediatamente después de su párrafo descriptivo. | **RESUELTO [x]** |

- [x] **5.1.** Validado en [`preview_pagina_0331.html`](file:///c:/IA_Proyectos/botScribd/reporte/goanywhere_mft_user_guide_7_7_0/preview_pagina_0331.html): encabezado `<h2>Contacts Tab</h2>`, seguido de `<p>The Contacts tab allows you to store the contact information for the Resource.</p>`, seguido de la figura `<figure class="doc-figure"><img src="figuras/fig_p0331_1.png" ...></figure>`, seguido de los parámetros `Name`, `Phone Number` y `Email`.
- [x] **5.2.** Documento maestro [`preview.html`](file:///c:/IA_Proyectos/botScribd/reporte/goanywhere_mft_user_guide_7_7_0/preview.html) sincronizado y actualizado.
- [x] **5.3.** Control de versiones protegido con Git commit.
