# AUDITORÍA DE CALIDAD Y HALLAZGOS: PREVIEW.HTML (PÁGINAS 1 A 3,712)
## Diagnóstico Preciso de Sintaxis, Semántica, Viñetas y Posición de Figuras

> **Documento Evaluado:** [`reporte/goanywhere_mft_user_guide_7_7_0/preview.html`](file:///c:/IA_Proyectos/botScribd/reporte/goanywhere_mft_user_guide_7_7_0/preview.html) (8.7 MB)  
> **Alcance:** 3,712 páginas compiladas (Manual Completo *GoAnywhere MFT User Guide 7.7.0*)  
> **Criterios de Referencia:** [`HALLAZGOS_SINTAXIS_Y_CRITERIOS_REVISION.md`](file:///c:/IA_Proyectos/botScribd/HALLAZGOS_SINTAXIS_Y_CRITERIOS_REVISION.md) y [`REPORTE_GENERACION_PAGINAS_1_A_700.md`](file:///c:/IA_Proyectos/botScribd/REPORTE_GENERACION_PAGINAS_1_A_700.md)  
> **Propósito:** Catálogo consolidado de páginas y componentes que requieren corrección y calibración en el compilador.

---

## 1. Resumen Ejecutivo del Diagnóstico

Tras la auditoría exhaustiva mediante análisis sintáctico y semántico sobre las 3,712 páginas del archivo `preview.html`, se identificaron **154 páginas** con anomalías que requieren ajustes estructurados antes de la entrega final.

| Categoría de Hallazgo | Páginas Afectadas | Incidencias Totales | Impacto Visual / Estructural | Prioridad |
| :--- | :---: | :---: | :--- | :---: |
| **Posición de Figuras (Inversión H1)** | 4 | 4 | Captura colocada por encima del título principal `<h1>` | **Alta** |
| **Posición de Figuras (Amontonamiento Final)** | 13 | 47 | 3 a 7 figuras apiladas al pie de la página sin intercalar con su texto | **Alta** |
| **Viñetas y Pasos Mutilados** | 2 | 2 | Bloques `<div class="content-step">` con cuerpo vacío o truncado | **Media** |
| **Semántica: Párrafos Huérfanos de Puntuación** | 63 | 63 | Párrafos espurios `<p class="content-p">.</p>` o `:` tras títulos o figuras | **Media** |
| **Semántica: Código XML promovido a H2** | 2 | 3 | Etiquetas técnicas XML convertidas erróneamente en subtítulos `<h2>` | **Media** |
| **Sintaxis: Glifos y Palabras Fragmentadas** | 72 | 74 | Vocablos técnicos descompuestos por glifos sueltos (`PDFFile`, `Row Set`, etc.) | **Media** |

---

## 2. Detalle de Hallazgos por Categoría

### 2.1. Posición de Figuras e Imágenes

#### A. Inversión Jerárquica: Figura Posicionada Antes del Título H1 (4 páginas)
De acuerdo con el **Criterio 14 y Criterio 18**, una figura ilustrativa nunca debe preceder al título principal `<h1>` de un capítulo o tema principal que abre la página.

| Página | Título H1 Afectado | Figura Invertida | Causa y Acción Correctiva Requerida |
| :---: | :--- | :--- | :--- |
| **Pág. 75** | `Example SFTP Client Setup` | `fig_p0075_1.png` | La figura tiene `top_px` bajo y se inserta antes de `<h1>`. Forzar que `<h1>` tenga precedencia absoluta en top de página. |
| **Pág. 87** | `Main Menu Bar` | `fig_p0087_1.png` | La barra de menú aparece antes del título temático. Mover `fig_p0087_1` debajo de `<h1>Main Menu Bar</h1>`. |
| **Pág. 2348** | `Admin Users` | `fig_p2348_1.png` | La captura de la tabla de usuarios administradores precede a su cabecera. Mover después del encabezado. |
| **Pág. 2480** | `Review Import Web User Results` | `fig_p2480_1.png` | Captura de resultados del asistente previa al título. Intercalar después del título y su descripción. |

#### B. Amontonamiento de Múltiples Figuras al Pie de Página (13 páginas)
En páginas con alta densidad de capturas (Criterio 13), el acumulador vertical del tracking omite sumar la altura física de las figuras emitidas previamente (`y_actual`), provocando que las figuras 2, 3 o subsecuentes no alcancen su umbral y caigan acumuladas al final de la página.

| Página | Total Figs | Módulo / Tema | Figuras Afectadas | Acción Requerida |
| :---: | :---: | :--- | :--- | :--- |
| **Pág. 806** | 4 | Project Designer | `fig_p0806_2`, `3`, `4` | Intercalar entre las definiciones de parámetros de diseño. |
| **Pág. 865** | 3 | Password Protect Excel | `fig_p0865_1`, `2`, `3` | Intercalar tras sus subpasos respectivos de configuración. |
| **Pág. 866** | 3 | Excel Task Options | `fig_p0866_1`, `2`, `3` | Ubicar cada figura junto a su bloque de opciones. |
| **Pág. 888** | 3 | File System Tasks | `fig_p0888_1`, `2`, `3` | Distribuir tras los títulos de subsección correspondientes. |
| **Pág. 1035** | 4 | EDI / Data Mapping | `fig_p1035_2`, `3`, `4` | Separar entre las cuadrículas de mapeo EDI. |
| **Pág. 1202** | 3 | Cloud Connectors | `fig_p1202_1`, `2`, `3` | Asociar a cada conector de servicio en la lista. |
| **Pág. 1237** | 4 | FTP Tasks Execution | `fig_p1237_2`, `3`, `4` | Distribuir entre los pasos de configuración FTP. |
| **Pág. 1461** | 4 | Email Tasks | `fig_p1461_2`, `3`, `4` | Intercalar con los paneles de servidor de correo y adjuntos. |
| **Pág. 1602** | 3 | Triggers & Automations | `fig_p1602_1`, `2`, `3` | Asociar a cada tipo de condición de disparo. |
| **Pág. 1772** | 3 | Security & Certificates | `fig_p1772_1`, `2`, `3` | Separar entre los paneles de almacén de certificados. |
| **Pág. 2331** | 5 | Projects Overview | `fig_p2331_3`, `4`, `5` | Intercalar con las descripciones de los botones de acción. |
| **Pág. 2332** | 10 | Action Buttons & Icons | `fig_p2332_5` a `fig_p2332_10` | Tablas de iconos pequeños: consolidar en cuadrícula o distribuir. |
| **Pág. 2333** | 10 | GoFast Accelerators | `fig_p2333_4` a `fig_p2333_10` | Distribuir tras cada explicación técnica del protocolo de aceleración. |

---

### 2.2. Viñetas, Pasos Numerados y Listas

#### Pasos con Cuerpo Vacío / Truncado (2 páginas)
Conforme al **Criterio 17**, los pasos numerados (`content-step`) se componen de `.step-marker` y `.step-body`. Se detectaron pasos donde el cuerpo quedó en blanco por rotura de corte o glifos absorbidos erróneamente:

1. **Página 65:**  
   * **Incidencia:** `<div class="content-step"><span class="step-marker">21.</span><span class="step-body"></span></div>`.  
   * **Causa:** El número `21.` provenía de un número de puerto o de página en el margen que fue clasificado por error como paso de procedimiento.  
   * **Corrección:** Purgar el marcador espurio o reintegrar el texto de la instrucción.

2. **Página 3137:**  
   * **Incidencia:** `<div class="content-step"><span class="step-marker">2.</span><span class="step-body"></span></div>`.  
   * **Causa:** El texto del paso 2 (*"From the main menu bar, select System, and then click Security Settings"*) fue fragmentado en un párrafo previo y el subtítulo `<h2>Security Settings</h2>`, dejando el paso huérfano.  
   * **Corrección:** Unificar el paso 2 con su texto instruccional completo.

---

### 2.3. Integridad Semántica y Falsos Encabezados

#### A. Fragmentos de Código XML Promovidos a H2 (Páginas 3177 y 3705)
* **Página 3177:**
  * **Incidencia:**
    ```html
    <h2 class="content-h2"><Server port="8005" shutdown="SHUTDOWN"></h2>
    ```
  * **Causa:** Línea de código del archivo `server.xml` que por iniciar con mayúscula y no terminar en punto fue promovida a subtítulo H2.
  * **Corrección:** Encapsular en bloque de código estilizado `<pre class="content-code"><code>...</code></pre>`.
* **Página 3705:**
  * **Incidencia:** Presencia de etiquetas `<h2 class="content-h2"></h2>` vacías tras la lista de pasos de migración de cluster.
  * **Corrección:** Eliminar nodos H2 vacíos durante el post-procesado.

#### B. Párrafos Huérfanos con Solo Signos de Puntuación (63 páginas)
En Scribd, al aislar encabezados o enlaces en `<span>` independientes, los puntos finales `.` o dos puntos `:` quedan en la capa de texto como renglones sueltos de un solo carácter. El compilador los emite como `<p class="content-p">.</p>` o `<p class="content-p">:</p>`.

* **Páginas Afectadas (63 páginas):**
  `388`, `426`, `502`, `840`, `957`, `1083`, `1104`, `1534`, `1540`, `1662`, `1734`, `1737`, `1741`, `1754`, `1757`, `1761`, `1764`, `1768`, `1791`, `1799`, `1803`, `1807`, `1861`, `1919`, `1921`, `1946`, `1970`, `2087`, `2090`, `2179`, `2213`, `2249`, `2259`, `2296`, `2305`, `2314`, `2414`, `2453`, `2485`, `2642`, `2843`, `2851`, `2924`, `2939`, `2943`, `2945`, `2951`, `2962`, `2967`, `2973`, `2975`, `2978`, `2982`, `3002`, `3003`, `3007`, `3073`, `3137`, `3148`, `3188`, `3189`, `3410`, `3661`.
* **Acción Correctiva:**
  Aplicar regla de anexado al elemento inmediatamente anterior (si es texto) o supresión de párrafos con longitud `<= 1` que contengan únicamente signos de puntuación `[\.,;:x29]`.

---

### 2.4. Sintaxis y Desfragmentación Léxica

#### Palabras Técnicas Fragmentadas en el Rango 701-3712 (72 páginas)
Conforme a los **Criterios 1, 2, 3 y 4**, se detectaron los siguientes vocablos técnicos recurrentes partidos por espacios artificiales o fusionados incorrectamente:

| Término Roto / Encontrado | Forma Corregida Esperada | Páginas Afectadas (Muestreo) | Total Páginas |
| :--- | :--- | :--- | :---: |
| `PDFFile` | **PDF File** | 1800, 1803, 1804, 1808, 1812, 1816, etc. | 27 págs |
| `Row Set Variable` | **RowSet Variable** | 701, 779, 787, 795, 796, 807, 821, 835, etc. | 22 págs |
| `EDIFACTTransaction` | **EDIFACT Transaction** | 1000, 1006, 1020, 1026 | 4 págs |
| `FTPServer` | **FTP Server** | 1207, 1208, 1243, 2329 | 4 págs |
| `Forexample` | **For example** | 437, 701, 702 | 3 págs |
| `S ervers` | **Servers** | 120, 122, 946 | 3 págs |
| `JVMMemory` | **JVM Memory** | 3500, 3501 | 2 págs |
| `Cop y Task` | **Copy Task** | 1100 | 1 pág |
| `Bloc ked` | **Blocked** | 1701 | 1 pág |
| `Re gular` | **Regular** | 694 | 1 pág |
| `Un resolved` | **Unresolved** | 1803 | 1 pág |
| `Se cure` | **Secure** | 2208 | 1 pág |
| `Softwa re` | **Software** | 3401 | 1 pág |
| `Co ntrol` | **Control** | 3437 | 1 pág |
| `Ex pressions` | **Expressions** | 3629 | 1 pág |
| `S connections` | **SSL connections** | 337 | 1 pág |

* **Páginas con Términos Sintácticos Afectadas (72 páginas):**  
  `120`, `122`, `337`, `437`, `694`, `701`, `702`, `779`, `787`, `795`, `796`, `807`, `821`, `835`, `868`, `878`, `889`, `901`, `946`, `949`, `950`, `968`, `999`, `1000`, `1006`, `1020`, `1026`, `1033`, `1045`, `1054`, `1100`, `1207`, `1208`, `1243`, `1539`, `1560`, `1698`, `1701`, `1702`, `1706`, `1710`, `1714`, `1725`, `1735`, `1738`, `1742`, `1746`, `1750`, `1755`, `1758`, `1765`, `1769`, `1773`, `1776`, `1780`, `1784`, `1788`, `1792`, `1796`, `1800`, `1803`, `1804`, `1808`, `1812`, `1816`, `2208`, `2329`, `3342`, `3401`, `3437`, `3500`, `3629`.

---

## 3. Plan de Acción y Correcciones Sistemáticas Sugeridas

Para resolver la totalidad de los hallazgos identificados en este informe sobre [`compilador.py`](file:///c:/IA_Proyectos/botScribd/compilador.py):

1. **Ajuste de Precedencia H1 vs. Figuras:**
   * Garantizar que si una página tiene un tema mayor `<h1>`, ninguna figura con `top_px` bajo pueda anteponerse al título de apertura.
2. **Corrección del Acumulador Vertical de Figuras (`y_actual`):**
   * Incorporar la suma de la altura física de las figuras emitidas en `_intercalar_figuras` para evitar la postergación masiva de figuras al pie de página (Págs 806, 865, 1035, 2331-2333).
3. **Filtro de Párrafos Huérfanos de Puntuación:**
   * Descartar párrafos residuales que únicamente contengan `.` o `:` tras subtítulos o figuras.
4. **Protección de Bloques de Código XML:**
   * Detectar cadenas con sintaxis de etiquetas `<Server...>` o `<.../>` e inhibir su promoción a encabezados `<h2>`.
5. **Ampliación del Diccionario de Desfragmentación Léxica:**
   * Incorporar los 16 patrones léxicos detectados a `RE_PATRONES_DESFRAGMENTACION` en `compilador.py`.
