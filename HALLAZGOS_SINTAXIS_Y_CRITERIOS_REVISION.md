# Hallazgos de Sintaxis y Criterios de Revisión para Generación HTML (Páginas 100+)

> **Documento:** *GoAnywhere MFT User Guide 7.7.0*  
> **Propósito:** Guía de control de calidad, puntos de observación y criterios de revisión automatizada y visual para la compilación de reportes técnicos a partir de extracciones de Scribd, con foco en el escalado a partir de la página 101 en adelante.  
> **Estado:** Activo / Normativo para el compilador.

---

## 1. Contexto Técnico y Causa Raíz de las Anomalías

Durante el análisis y compilación de las páginas 1 a 100 se identificaron discrepancias sintácticas y estructurales entre el texto original y el extraído. Su origen radica en la arquitectura de renderizado web de Scribd:

1. **Descomposición Vectorial por Glifos (`pdf2htmlEX`):**
   Scribd no almacena el texto como párrafos continuos, sino como una capa `.text_layer` con cientos de etiquetas `<span>` posicionadas con coordenadas absolutas y márgenes microscópicos para preservar el *kerning* (interletrado tipográfico) del PDF original.
2. **Extracción Desacoplada (`paginas.json`):**
   Al extraer el texto con `.get_text().strip()`, cada `<span>` se convirtió en un renglón independiente dentro del arreglo `lineas_texto`.
3. **Concatenación con Espacio Intercalado (`compilador.py`):**
   Al reconstruir bloques con `" ".join(buffer)`, se generaron separaciones artificiales de palabras, roturas numéricas y solapamientos.

---

## 2. Catálogo de Hallazgos y Puntos de Observación

### Criterio 1: Palabras Fragmentadas en 3 Partes (Glifo Inicial + Raíz + Sufijo)
* **Descripción:** Palabras divididas en tres fragmentos debido a glifos con posiciones independientes (primera letra con coordenada especial, cuerpo central y letra final).
* **Ejemplos Reales Encontrados:**
  * `A ctio n` $\rightarrow$ **Action**
  * `E lem ent` $\rightarrow$ **Element**
  * `E xa mple` $\rightarrow$ **Example**
  * `Fe atur es` $\rightarrow$ **Features**
  * `Com plet ed` $\rightarrow$ **Completed**
  * `Data bas e` $\rightarrow$ **Database**
  * `Exec utio n` $\rightarrow$ **Execution**
* **Punto de Revisión para Páginas 100+:**
  Monitorear secuencias con el patrón léxico `\b([A-Z])\s+([a-z]{2,})\s+([a-z]{1,2})\b` para asegurar que ningún término técnico o verbo termine partido por espacios.

---

### Criterio 2: Prefijos y Raíces de 2 Letras Separadas
* **Descripción:** La primera sílaba o prefijo de dos letras queda aislada por el motor tipográfico de la capa de texto.
* **Ejemplos Reales Encontrados:**
  * `Co nnectors` $\rightarrow$ **Connectors**
  * `Ac tive` $\rightarrow$ **Active**
  * `Co nfiguring` $\rightarrow$ **Configuring**
  * `Co nfigure` $\rightarrow$ **Configure**
  * `Co ntact` $\rightarrow$ **Contact**
  * `Ad min` $\rightarrow$ **Admin**
  * `Ag ents` $\rightarrow$ **Agents**
  * `Cl uster` $\rightarrow$ **Cluster**
  * `Do main` $\rightarrow$ **Domain**
  * `Pro ject` $\rightarrow$ **Project**
* **Punto de Revisión para Páginas 100+:**
  Verificar que prefijos comunes del dominio GoAnywhere (`Co-`, `Ac-`, `Ad-`, `Ag-`, `Pro-`, `Re-`, `Se-`, `Tr-`) no queden separados del resto de la palabra.

---

### Criterio 3: Mayúsculas Aisladas al Inicio de Palabra
* **Descripción:** Letra capital en un `<span>` aislado seguido de las minúsculas restantes en la línea subsiguiente.
* **Ejemplos Reales Encontrados:**
  * `F iles` $\rightarrow$ **Files**
  * `F olders` $\rightarrow$ **Folders**
  * `E lse` $\rightarrow$ **Else**
  * `E rror` $\rightarrow$ **Error**
  * `P rojects` $\rightarrow$ **Projects**
  * `L ogin` $\rightarrow$ **Login**
  * `M anager` $\rightarrow$ **Manager**
  * `U ser` $\rightarrow$ **User**
* **Punto de Revisión para Páginas 100+:**
  Toda letra mayúscula de la `B` a la `Z` seguida de espacio y una palabra minúscula inglesa válida debe recomponerse. *(Nota: La letra `A` debe discriminarse contextualmente para no fusionar el artículo legítimo como `"A guide"` o `"A host"`).*

---

### Criterio 4: Letra Final Partida por Margen Derecho
* **Descripción:** El último glifo de una palabra salta a un `<span>` independiente al tocar el margen o separador visual del visor.
* **Ejemplos Reales Encontrados:**
  * `Interne t` $\rightarrow$ **Internet**
  * `Cod e` $\rightarrow$ **Code**
  * `Microsof t` $\rightarrow$ **Microsoft**
  * `Crea te` $\rightarrow$ **Create**
  * `Upda te` $\rightarrow$ **Update**
  * `Dele te` $\rightarrow$ **Delete**
  * `Star t` $\rightarrow$ **Start**
  * `Director y` $\rightarrow$ **Directory**
  * `Variabl e` $\rightarrow$ **Variable**
* **Punto de Revisión para Páginas 100+:**
  Comprobar terminaciones que dejen letras sueltas (`t`, `e`, `y`, `d`, `s`, `r`, `g`, `m`, `k`) tras sustantivos o verbos técnicos.

---

### Criterio 5: Números de Página Desplazados o Fragmentados
* **Descripción:** En la Tabla de Contenidos o listas tabulares, dígitos del número de página quedan divididos en múltiples líneas (por ejemplo `40` en una línea y `3` en otra, o el primer dígito adjunto al título).
* **Ejemplos Reales Encontrados:**
  * `Move Projects 40` + línea siguiente `3` $\rightarrow$ Debe consolidarse en **Move Projects 403**.
  * `Export Project 40` + línea siguiente `8` $\rightarrow$ **Export Project 408**.
  * `Export Folder 41` + línea siguiente `1` $\rightarrow$ **Export Folder 411**.
  * `Google Chrome 29` + número `51` $\rightarrow$ **Google Chrome** con destino **2951**.
* **Punto de Revisión para Páginas 100+:**
  Si aparecen apéndices, índices analíticos o tablas de referencia en páginas 100+, validar que el número de página tenga la longitud esperada (3 a 4 dígitos para este documento) y no quede como sufijo de texto ni se trunque.

---

### Criterio 6: Protección de Falsos Positivos con Números Técnicos Legítimos
* **Descripción:** No todos los números al final de una frase o en un título son números de página; existen versiones de producto, estándares y códigos técnicos.
* **Ejemplos Reales Protegidos:**
  * `Microsoft Internet Explorer 11` (El `11` es versión de navegador, no página).
  * `EDI 997 Error Codes` (El `997` es tipo de transacción X12).
  * `Section 508 Compliance` (Estándar de accesibilidad US).
  * `AWS S3 Bucket Connection Fails 403 Forbidden` (El `403` es código HTTP).
  * `Status Code: 590 - importMonitor Failed` (Código de estado de error interno).
  * `Truncated Server Reply 220` (Código de bienvenida FTP).
  * `IPv6`, `SHA1`, `SHA256`, `Base64`.
* **Punto de Revisión para Páginas 100+:**
  Mantener y ampliar la lista blanca de números técnicos para que el parser no los confunda con referencias de página.

---

### Criterio 7: Elementos Estructurales en Páginas de Contenido
* **Descripción:** Representación correcta de elementos ricos extraídos del cuerpo del documento.
* **Puntos de Verificación:**
  1. **Viñetas (`bullet`):** Scribd representa viñetas con la letra `l` de fuentes Dingbats. El parser debe mapear `l` $\rightarrow$ `•` y no incluirla como texto de párrafo.
  2. **Pasos Numerados (`numero`):** Detectar expresiones `^\d+\.\s` y no fusionar dos pasos en el mismo párrafo.
  3. **Bloques de Aviso / Tips (`tip`):** Detectar bloques que inician con `TIP:`, `Note:`, `Warning:` o `Important:` y encapsularlos en contenedores destacados (`callout` / `tip-box`).
  4. **Running Headers:** Títulos de sección superior como `GettingStarted/` o `Resources/` deben normalizarse con separación de mayúsculas (`Getting Started /`) y no duplicarse como títulos `h1`.
  5. **Artefactos Residuales:** Purgar líneas fijas de pie de página (`page: XX`, `www.goanywhere.com`, `GoAnywhere MFT User Guide`).

---

### Criterio 8: Extracción, Desacople e Inyección de Figuras y Diagramas UI
* **Descripción:** Scribd rasteriza pantallas de interfaz, cuadros de diálogo y diagramas dentro de hojas de atlas compuestas (`.image_layer`), a menudo combinando múltiples elementos visuales o fragmentos de texto en una misma rebanada gráfica (`clip: rect`).
* **Hallazgos Reales Encontrados:**
  * **Rebanadas Compuestas con Texto Intermedio (Pág. 57):** Scribd agrupó dos tarjetas UI en un solo bloque. Al extraer la segunda tarjeta, se arrastraba el texto intermedio del PDF si el corte no comenzaba estrictamente en su borde superior exacto (`y = 238` en vez de `120`).
  * **Falsos Positivos de Texto Formateado (Págs. 84, 94, 98):** Títulos con líneas decorativas arriba/abajo o bloques de enlaces sin bordes laterales eran capturados por error como imágenes.
  * **Duplicidad de Callouts Tintados (Pág. 43, 45, 78):** Cajas de `WARNING:` o `TIP:` con barras laterales azules no deben extraerse como imagen, sino formatearse como cajas CSS en el HTML para mantener fidelidad tipográfica y accesibilidad.
* **Criterios Normativos de Calidad:**
  1. **Regla de Cierre de 4 Bordes:** Toda tarjeta UI legítima debe poseer cuatro bordes continuos (`top >= 40%`, `bottom >= 40%`, `left >= 60%`, `right >= 60%`).
  2. **Desacople Quirúrgico:** Cuando existan múltiples tarjetas en una rebanada, cada una debe aislarse desde su propio borde superior a su borde inferior, descartando espacios en blanco o textos externos.
  3. **Diagramas Complejos:** Gráficos estructurales mayores (ej. arquitectura en pág. 39) se preservan íntegros por su alta crominancia y complejidad visual.
  4. **Separación de Ciclo de Vida:** Las figuras residen en `output/.../figuras/` y su catálogo en `figuras_paginas.json`. La carpeta `reporte/` solo debe recibir copias de aquellas figuras que efectivamente hayan sido inyectadas en el HTML compilado.

---

### Criterio 9: Desglose Redundante de Spans Hijos (Multi-Capa con Enlaces Internos)
* **Descripción:** En páginas con enlaces internos cruzados (ej. `<a class="ll">`), Scribd emite un nodo contenedor `<span class="g">` con la oración completa ensamblada, e inmediatamente después emite una serie de nodos hijos `<span class="a">` con los fragmentos desglosados del enlace. Al capturarse ambos niveles en `paginas.json`, se producían duplicaciones fantasma dentro del mismo párrafo o viñeta.
* **Hallazgos Reales Encontrados:**
  * **Página 51:** La línea `'basic authentication of Admin User passwords against a'` fue seguida por los fragmentos `'ba'`, `'sic authentication of A'`, `'dmi'`, `'n User p'`, `'asswords against a'`, produciendo la duplicación `"basic authentication... ba sic authentication..."`.
  * **Página 52:** La línea `'Agent service from the Service Manager page.'` fue seguida por sus fragmentos `'Agen'`, `'t service from the'`, `'Service Manager'`, `'page.'`.
* **Criterio de Resolución en Compilador:**
  * **Algoritmo de Deduplicación en 2 Pasadas:** Tras colapsar sufijos idénticos consecutivos, se evalúa si la concatenación alfanumérica sin espacios de las $k$ líneas siguientes coincide exactamente con la línea completa precedente (`actual_norm == buf_hijos_norm`). De ser así, los fragmentos hijos se descartan en bloque.

---

### Criterio 10: Delimitación Semántica de Viñetas Multioracionales y Supresión de Falsos H2
* **Descripción:** 
  1. Las viñetas en manuales técnicos frecuentemente contienen dos o más oraciones completas. El corte prematuro de viñeta al primer punto `.` causaba que las oraciones subsecuentes quedaran huérfanas como párrafos sueltos.
  2. Fragmentos huérfanos muy cortos (ej. `'Agen'` o `'FT'`) que no terminaban en punto eran clasificados erróneamente como subtítulos `<h2>`.
* **Criterios Normativos de Calidad:**
  1. **Cierre Semántico de Viñeta:** Una viñeta acumula todas sus oraciones y solo concluye cuando se detecta el inicio de otra viñeta (`'l'`), un paso numerado (`^\d+\.\s`), un bloque callout (`TIP:`, `WARNING:`) o un nuevo título de sección.
  2. **Umbral Mínimo de Subtítulos H2:** Ninguna línea con longitud menor a 6 caracteres (`len(l) < 6`) puede ser promovida a subtítulo `<h2>`.

---

### Criterio 11: Integridad de Callouts Multi-Capa (TIP, WARNING, NOTE) y Enlaces Web
* **Descripción:** En Scribd, los bloques destacados (`TIP:`, `WARNING:`, `NOTE:`) con fondos coloreados o decoraciones a menudo dividen la página en múltiples capas `.text_layer` con diferentes `z-index` (ej. `z-index: 2` para viñetas y rótulo del callout; `z-index: 4` para el cuerpo del callout y el pie de página). Si la extracción de la página no concatena secuencialmente todos los `text_layer`, el callout resulta mutilado o vacío en el HTML compilado.
* **Hallazgos Reales Encontrados:**
  * **Página 54:** El bloque `<div class="content-tip">` solo contenía el rótulo `"TIP:"` mientras que la explicación (*"Fortra offers a production go-live review of your GoAnywhere system..."*) y el enlace oficial residían en la segunda capa (`z-index: 4`).
  * **Fragmentación de Enlaces y Cierre:** La frase de cierre venía descompuesta en los spans `'fo'`, `'r more infor'`, `'mation.'`, y las viñetas precedentes duplicaban puntos `..` por glifos sueltos `'.'`.
* **Criterios Normativos de Calidad:**
  1. **Concatenación Obligatoria Multi-Capa:** La extracción en `paginas.json` debe procesar todos los `text_layer` de la página para que ningún bloque callout quede huérfano.
  2. **Desfragmentación de Vocablos de Asistencia:** Recomponer `"fo r more"` $\rightarrow$ `"for more"` e `"infor mation"` $\rightarrow$ `"information"`.
  3. **Enriquecimiento de URLs:** Las URLs en callouts (ej. `https://www.goanywhere.com/...`) deben convertirse en etiquetas `<a>` interactivas con clase `.doc-link` abriendo en nueva pestaña (`target="_blank"`).
  4. **Supresión de Doble Puntuación:** Eliminar dobles puntos accidentales `\.{2,}` producidos al anexar puntos aislados de Scribd a oraciones ya cerradas.

---

### Criterio 12: Subpasos Alfabéticos, Cierre de Pasos en Dos Puntos y Jerarquía H1/H2 por TOC
* **Descripción:** En páginas de tutoriales o procedimientos guiados (ej. página 55):
  1. **Jerarquía H1/H2 en Páginas Multi-Tema:** Cuando una página inicia una sección mayor (`Creating Your First Project`) y contiene múltiples temas del TOC subsecuentes (`Creating a Project`, `Building the Project`, `The Timestamp Task`), el compilador no debe generar múltiples etiquetas `<h1>`. Solo el tema principal que abre la página es `<h1>`; todos los demás temas secundarios del TOC en esa misma página deben clasificarse semánticamente como `<h2>`.
  2. **Delimitación de Pasos con Dos Puntos (`:`):** Pasos numerados introductorios que terminan en dos puntos `:` (ej. `"3. In the Create Project window, specify the following fields:"`) deben cerrar su bloque de inmediato y no absorber la letra del subpaso siguiente (`'a.'`).
  3. **Identificación de Subpasos Alfabéticos:** Líneas con formato `^[a-z]\.\s*` (ej. `a. Project Name - Give the Project a name.`) deben tipificarse como `subpaso` y renderizarse con sangría específica (`.content-step--sub`).
  4. **Regla de Posposición de Figuras ante Subpasos:** Si una figura tiene una coordenada vertical que cae en medio o antes de una lista de subpasos alfabéticos que ilustran sus campos, la figura debe posponerse automáticamente para ubicarse justo después del último subpaso consecutivo (`subpaso b.`) y antes del siguiente paso numerado (`paso 4.`).

---

### Criterio 13: Acumulación de Altura de Figuras en el Tracking Vertical (`_intercalar_figuras`)
* **Descripción:** Cuando una página contiene múltiples figuras intercaladas con bloques de texto breves (ej. página 57 con 4 figuras entre pasos 3, 4 y párrafo de cierre), si el cursor vertical `y_actual` únicamente acumula la altura estimada del texto (`h_e`) y omite sumar la altura física de las figuras que ya fueron insertadas, el valor de `y_actual` queda artificialmente bajo. Como consecuencia, las figuras subsiguientes (`fig_2`, `fig_3`, `fig_4`) nunca alcanzan su condición `top_px <= corte` durante el recorrido y terminan amontonadas al final de la página.
* **Hallazgos Reales Encontrados (Página 57):**
  * La página 57 cuenta con 4 figuras intercaladas:
    1. `fig_0057_1` (`top_px: 103`): cabecera de variables (al inicio).
    2. Paso 3 (`3. From the Variables...`).
    3. `fig_0057_2` (`top_px: 341`): variable asignada al panel Print task.
    4. Paso 4 (`4. Expand the Advanced...`).
    5. `fig_0057_3` (`top_px: 579`): panel Advanced y campo Output File.
    6. Párrafo (*"The Project outline should look like..."*).
    7. `fig_0057_4` (`top_px: 778`): esquema del proyecto completo.
  * Antes del ajuste, las figuras 2, 3 y 4 se renderizaban todas juntas al pie de la página después del último párrafo.
* **Criterios Normativos de Calidad:**
  1. **Acumulación de Altura de Figuras:** Al emitir una figura en el flujo, debe incrementarse obligatoriamente el acumulador vertical: `y_actual += float(f.get("alto") or 100) + 20.0`.
  2. **Calibración de Corte Proporcional:** El umbral de inserción debe evaluarse con `corte = y_actual + (h_e * 0.85)` para evitar postergaciones indebidas por variaciones de margen o fuentes.

---

### Criterio 14: Supresión de Falsos H1/H2 por Frases Verbales de Acción y Continuación de Temas
* **Descripción:** Cuando una página continúa el procedimiento de la página anterior y no corresponde al inicio formal de un tema mayor en el TOC (ej. página 58), la primera línea suele ser una instrucción procesal de acción (ej. `"Click the Execute button..."`). Si el parser aplica una regla ciega de primer elemento (`if not elementos: elemento = H1`), fragmenta la oración convirtiendo `"Click the"` en un falso título `<h1>` y arrojando el resto a un párrafo subordinado, además de empujar indebidamente la figura asociada a la parte superior absoluta de la página por la regla de protección de H1.
* **Hallazgos Reales Encontrados (Página 58):**
  * La línea de Scribd `'Click the'` se promovía a `<h1 class="content-h1">Click the</h1>`, fragmentando el texto `"Execute button in the toolbar. A notification will appear when the Project is finished."`.
  * La notificación de ejecución (`fig_0058_1`) se movía erróneamente arriba de `"Click the"`.
  * Las palabras compuestas `'OutputFile'` y `'ViewJobLog'` aparecían sin espacio.
* **Criterios Normativos de Calidad:**
  1. **Filtro de Frases de Acción Verbal:** Líneas que inician con verbos o conectores procesales (`click`, `the`, `to`, `if`, `when`, `from`, `select`, `in`, `for`, `and`, `expand`, `navigate`, `run`, `set`, `build`) quedan terminantemente excluidas de la asignación automática de `H1` o `H2`.
  2. **Agrupamiento Natural de Párrafos:** La frase se agrupa en su totalidad como `<p class="content-p">`, permitiendo que la figura de notificación se ubique limpiamente debajo de la instrucción.
  3. **Jerarquía H2 para Secciones Secundarias:** Encabezados que inician en la mitad o final de una página con contenido previo (ej. `"What's Next?"`) deben tipificarse como `<h2 class="content-h2">` para respetar la jerarquía de la página.
  4. **Desfragmentación de Comandos UI:** `'OutputFile'` $\rightarrow$ `'Output File'`, `'ViewJobLog'` $\rightarrow$ `'View Job Log'`.

---

### Criterio 15: Discriminación de Cabeceras Repetitivas vs. Figuras UI de Gran Altura en Top
* **Descripción:** En `extractor_figuras.py`, una regla descartaba imágenes con `abs_top < 90 and cw > 650`, asumiendo que eran franjas decorativas o cabeceras repetitivas. Esto provocaba que figuras legítimas de formularios UI que inician en la parte superior de la página (ej. la ventana "Add Web User" de la página 63, con `cw = 758px` y `ch = 433px`) fueran omitidas por completo del catálogo `figuras_paginas.json`.
* **Hallazgos Reales Encontrados (Página 63):**
  * La página 63 tiene 2 figuras claramente visibles:
    1. `fig_0063_1` (`top_px: 103`, 693x368 px): formulario completo "Add Web User" con pestañas y campos.
    2. `fig_0063_2` (`top_px: 929`, 449x99 px): panel "Password Generation" bajo Authentication Credentials.
  * Por el filtro ciego de ancho y top, `fig_0063_1` se descartaba silenciosamente, dejando el reporte HTML con una sola figura.
* **Criterios Normativos de Calidad:**
  1. **Acotamiento por Altura de Cabecera:** La supresión de cabeceras superiores repetitivas debe restringirse únicamente a elementos con altura delgada: `if abs_top < 90 and cw > 650 and ch <= 55: continue`.
  2. **Sincronización Espejo:** Asegurar que `extraer_figuras_pagina_gestor` ejecute siempre con `mirror_reporte=True` para actualizar simultáneamente `output/` y `reporte/`.

---

### Criterio 16: Delimitación de Subtítulos H2 tras Listas Cerradas y Preservación de Figuras de Cierre
* **Descripción:** 
  1. Si un ítem de lista numerada no termina en punto ortográfico (ej. `"4. Permission to upload files"`), no debe absorber la línea siguiente si el paso actual ya es una cláusula completa y la siguiente línea corresponde a un subtítulo (`"UserName"`).
  2. `es_cierre_previo` en la detección de subtítulos `<h2>` debe considerar como cierre válido cuando el elemento precedente es una lista (`numero`, `subpaso`, `bullet`, `figura`), permitiendo que el subtítulo no se convierta en texto de párrafo ordinario.
  3. Figuras ubicadas en la parte inferior de la página (`top_px >= 850`) que ilustran a un subtítulo final (ej. `Password Generation` bajo `Authentication Credentials`) no deben invertirse hacia arriba del título.
* **Criterios Normativos de Calidad:**
  1. **Corte Seguro de Pasos:** `sig_es_sub` evalúa si el paso actual concluye sintácticamente y corta la acumulación ante nombres propios o títulos.
  2. **Cierre Semántico de Listas:** Un elemento `numero` o `bullet` habilita inmediatamente la evaluación de `<h2>` para la siguiente línea.
  3. **Preservación de Figuras de Cierre:** Figuras con `top_px >= 850` permanecen después del `H2` introductorio.

---

### Criterio 17: Control Estricto de Viñetas, Marcadores Tabulares y Subnivel de Anidación Flexbox
* **Descripción:** 
  1. Las listas numeradas (`.content-step`) no deben renderizarse como texto corrido donde la segunda línea se mete debajo del número. Deben utilizar una arquitectura flexbox con `.step-marker` (ancho tabular fijo con `font-variant-numeric: tabular-nums`) y `.step-body` (alineación en bloque colgante).
  2. Los subpasos alfabéticos (`.content-step--sub`) deben mantener sangría de segundo nivel (`margin-left: 30px`) con su marcador propio (`a.`, `b.`).
  3. Las viñetas (`•`) que cuelguen de un paso numerado previo o introducción terminada en dos puntos (`:`) deben recibir automáticamente la clase subordinada `.content-bullet--sub` con tabulador desplazado (`margin-left: 32px`).
  4. Los pasos numerados no deben cortarse prematuramente ante verbos imperativos (`Click on`, `Click`, `Select`, `Choose`, `Enter`, `Type`, `Check`) ni confundir objetos de interfaz (`New Site`, `Connect`, `Save`) con subtítulos espurios.
* **Criterios Normativos de Calidad:**
  1. **Sangría Colgante Tabular:** Todo paso numerado o subpaso se divide en marcador y cuerpo flexbox sin roturas visuales multilínea.
  2. **Jerarquía Visual de Viñetas:** Toda viñeta subordinada a un paso se indenta a 32px, manteniendo clara subordinación lógica.
  3. **Absorción de Frases Verbales:** Un paso con verbo o preposición terminal incompleta continúa absorbiendo hasta la conclusión sintáctica de la instrucción.

---

### Criterio 18: Orden Canónico de Secciones H2 Ilustradas e Intercalación de Figuras Intermedias
* **Descripción:** 
  1. Un encabezado `<h2>` que abre una sección (ej. `Access to the GoAnywhere FTP Feature`, `Permission to Upload files`) introduce conceptualmente la temática y sus figuras asociadas. Una figura perteneciente a dicha subsección nunca debe colocarse antes de su encabezado de apertura.
  2. En diagramas UI donde la figura precede inmediatamente a la explicación de la interfaz, la figura debe posicionarse justo después del encabezado H2 y antes del párrafo descriptivo siguiente.
  3. Desfragmentación canónica de los títulos y opciones clave de la página 64 (`Access to the GoAnywhere FTP Feature`, `Permission to Upload files`, `Generate a password based on the password policy`, `Upload (Write)`, `List`).
* **Criterios Normativos de Calidad:**
  1. **Barrera de Encabezado:** Ninguna figura con `top_px >= 200` puede anteponerse a un H2 dentro de la misma subsección.
  2. **Intercalación Ilustrativa H2:** La figura ilustrativa de un H2 se emite inmediatamente tras el título si precede al párrafo descriptivo.
  3. **Excepción de Cierre:** Únicamente encabezados de cierre o transición externa (ej. `"What's Next?"`) permiten que las figuras explicativas de la sección previa se ubiquen antes del encabezado.

---

## 3. Matriz Comparativa: Antes vs. Después

| Caso | Entrada en `paginas.json` | Antes (Sin regla) | Después (Con Desfragmentación) |
| :--- | :--- | :--- | :--- |
| **Acción** | `['A', 'ctio', 'n 3283']` | `"A ctio n 3283"` | `"Action 3283"` |
| **Elemento** | `['E', 'lem', 'ent 3267']` | `"E lem ent 3267"` | `"Element 3267"` |
| **Conector** | `['Cloud Co', 'nnectors 3259']` | `"Cloud Co nnectors 3259"` | `"Cloud Connectors 3259"` |
| **Sesiones Activas**| `['Ac', 'tive Sessions 3367']` | `"Ac tive Sessions 3367"` | `"Active Sessions 3367"` |
| **Navegador** | `['Microsoft Interne', 't Explorer 11']` | `"Microsoft Interne t Explorer 11"` | `"Microsoft Internet Explorer 11"` |
| **Código de Error**| `['Status Cod', 'e: 590']` | `"Status Cod e: 590"` | `"Status Code: 590"` |
| **Archivos** | `['F', 'iles Folders 81']` | `"F iles Folders 81"` | `"Files Folders 81"` |
| **Configuración** | `['Co', 'nfiguring a Resource 139']` | `"Co nfiguring a Resource 139"` | `"Configuring a Resource 139"` |
| **Letra 't' suelta**| `['Create t', 'he CSV File']` | `"Create t he CSV File"` | `"Create the CSV File"` |
| **Letra 'p' suelta**| `['User p', 'asswords against']` | `"User p asswords against"` | `"User passwords against"` |
| **Pronombre roto**| `['the', 'y have access']` | `"the y have access"` | `"they have access"` |
| **Recurso en 3** | `['Export R', 'eso', 'urce 142']` | `"Export R eso urce 142"` | `"Export Resource 142"` |
| **Historia en 3** | `['Change H', 'isto', 'ry 2578']` | `"Change H isto ry 2578"` | `"Change History 2578"` |
| **Gatillo en 3** | `['Copy T', 'rig', 'ger 541']` | `"Copy T rig ger 541"` | `"Copy Trigger 541"` |
| **Sistema en 3** | `['File Sy', 'ste', 'm Tasks']` | `"File Sy ste m Tasks"` | `"File System Tasks"` |
| **Mago en 3** | `['SQL W', 'iza', 'rd 3375']` | `"SQL W iza rd 3375"` | `"SQL Wizard 3375"` |
| **Ruta de Menú** | `['navigate to', 'GettingStarted>GoAnywhereFeatureTour']` | `"GettingStarted>GoAnywhereFeatureTour"` | `"Getting Started > GoAnywhere Feature Tour"` |
| **Protocolo WebDAV** | `['W', 'ebDAV directories']` | `"W ebDAV directories"` | `"WebDAV directories"` |
| **Duplicación Spans** | `['basic auth against a', 'ba', 'sic auth against a']` | `"basic auth... ba sic auth..."` | `"basic auth against a"` (sin repetición) |
| **Fragmento Huérfano** | `['Agent service...', 'Agen', 't service...']` | `<h2>Agen</h2><p>t service...</p>` | Viñeta completa integrada |
| **Callout Mutilado (Pág 54)** | `['TIP:']` (sin capa 2) | `<div class="content-tip">TIP:</div>` | Callout completo con cuerpo y enlace activo |
| **Filtro IP pegado** | `['using the IPFilter and']` | `"using the IPFilter and"` | `"using the IP Filter and"` |
| **Frase de Cierre TIP** | `['fo', 'r more infor', 'mation.']` | `"fo r more infor mation."` | `"for more information."` |
| **Crear Proyecto Pegado** | `['click the', 'CreateaProject', 'link']` | `"click the CreateaProject link"` | `"click the Create a Project link"` |
| **Subpasos Mutilados (Pág 55)** | `['fields:', 'a.', 'ProjectName', '- Give...']` | Paso 3 absorbe `'a.'` y crea falso `<h2>` | `a. Project Name - Give the Project a name.` identado |
| **Multi-H1 en Página (Pág 55)** | 4 temas de TOC en página 55 | 4 títulos `<h1 class="content-h1">` | 1 `<h1>` (tema mayor) y 3 `<h2>` (secciones) |
| **Amontonamiento Figuras (Pág 57)** | 4 figuras con pasos breves | Figs 2, 3 y 4 al final de página | Cada figura tras su paso respectivo (Paso 3 $\rightarrow$ Fig 2, Paso 4 $\rightarrow$ Fig 3) |
| **Falso H1 por 'Click the' (Pág 58)** | `['Click the', 'Execute', 'button...']` | `<h1>Click the</h1>` y figura al inicio | Párrafo continuo `"Click the Execute button..."` con figura de notificación debajo |
| **Comando Ver Log (Pág 58)** | `['Click', 'ViewJobLog', 'to review...']` | `"Click ViewJobLog to review..."` | `"Click View Job Log to review..."` |
| **Figura Superior Omitida (Pág 63)** | Formulario "Add Web User" (top=103, h=433) | Descartada por `abs_top < 90` | Extraída limpiamente como `fig_0063_1` (693x368px) al inicio de página |
| **Subtítulo Tras Lista (Pág 63)** | `['4. Permission to upload files', 'UserName']` | Paso 4 absorbe `UserName` y párrafo | Paso 4 cerrado y `<h2>User Name</h2>` independiente |
| **Figura al Pie (Pág 63)** | `AuthenticationCredentials` y `fig_0063_2` | Figura invertida arriba del subtítulo | `<h2>Authentication Credentials</h2>` seguido de figura `Password Generation` |
| **Figuras Invertidas (Pág 64)** | Subtítulos H2 y figuras `fig_p0064_1` y `fig_p0064_2` | Figuras colocadas antes de sus H2 | H2 precede a su figura (`Access to...` $\rightarrow$ Protocols, `Permission to...` $\rightarrow$ Permissions) |
| **Texto Partido en Pág 64** | `['Accesstothe', 'Permissionto', 'Upload(Write)']` | Texto fusionado sin espacios | `"Access to the GoAnywhere FTP Feature"`, `"Permission to Upload files"`, `<strong>Upload (Write)</strong>` |
| **Estructura Tabular de Pasos** | `<p class="content-step">1. Texto multilínea</p>` | Texto debajo del número 1. | `.content-step` con `.step-marker` tabular y `.step-body` flex |
| **Viñetas Subordinadas** | Viñeta dentro de paso 4 (Pág 65) | Viñeta plana en 14px | `.content-bullet--sub` indentada a 32px |

---

## 4. Checklist Automatizado para la Fase de Páginas 100+

Antes de dar por aceptada una corrida masiva de páginas (ej. páginas 101 a 500 o manual completo):

- [ ] **1. Verificación de Fragmentos de 3 Partes:**
  * Ejecutar búsqueda regex: `\b([A-Za-z]{1,4})\s+([a-z]{1,6})\s+([a-z]{1,3})\b`.
  * Umbral: 0 ocurrencias de palabras comunes rotas.
- [ ] **2. Verificación de Mayúsculas Aisladas:**
  * Ejecutar búsqueda regex: `\b([B-Z])\s+([a-z]{3,})\b`.
  * Umbral: 0 ocurrencias excepto nombres de variables explícitas de programación.
- [ ] **3. Verificación de Prefijos Rotos:**
  * Ejecutar búsqueda de términos clave: `Co n\w+`, `Ac tive`, `Ad min`, `Ag ent`, `Pro ject`.
  * Umbral: 0 ocurrencias.
- [ ] **4. Verificación de Terminaciones con 1 Letra:**
  * Ejecutar búsqueda regex: `\b([a-zA-Z]{4,})\s+([b-hj-z])\b`.
  * Umbral: Solo abreviaturas o variables de código legítimas.
- [ ] **5. Auditoría Numérica de Paginación:**
  * Ningún título debe terminar con números colgados de 1 o 2 dígitos si el rango de páginas de la sección supera 100.
  * No deben existir números de página decrecientes dentro de la misma sección temática.
- [ ] **6. Limpieza de Artefactos de Visor:**
  * 0 apariciones de cadenas `\ue000` a `\uf8ff` (caracteres privados de Scribd).
  * 0 apariciones de cadenas `"page: "` dentro del cuerpo de texto compilado.
- [ ] **7. Auditoría de Figuras y Diagramas UI:**
  * Toda imagen insertada debe provenir del catálogo `figuras_paginas.json`.
  * Las figuras deben posicionarse en el flujo HTML según su coordenada `posicion_top_px` relativa al párrafo correspondiente.
  * Ninguna figura debe contener texto circundante mutilado o fondos tintados de callouts.
  * Los archivos en `reporte/.../figuras/` deben corresponder únicamente a imágenes activas referenciadas en el HTML.
  * Ninguna figura debe quedar insertada en medio de una secuencia de subpasos alfabéticos (`a.`, `b.`).
- [ ] **8. Supresión de Duplicados Multi-Capa:**
  * 0 apariciones de duplicaciones por desglose de spans (`ba sic`, `dmi n`, etc.).
- [ ] **9. Integridad de Encabezados H2:**
  * Ningún elemento `<h2>` con menos de 6 caracteres (ej. no debe haber `<h2>Agen</h2>`, `<h2>FT</h2>`).
- [ ] **10. Integridad de Callouts (TIP / WARNING / NOTE):**
  * Ningún bloque callout vacío (`<div class="content-tip">` o similar que solo contenga el label sin contenido).
  * Enlaces URL dentro de callouts correctamente enriquecidos con clase `doc-link`.
  * 0 apariciones de dobles puntos `..` generados por glifos sueltos.
- [ ] **11. Jerarquía de Títulos por Página:**
  * Máximo un único `<h1 class="content-h1">` por página de contenido. Temas adicionales del TOC en la misma página deben ser `<h2 class="content-h2">`.
- [ ] **12. Integridad de Pasos y Subpasos:**
  * Ningún paso numerado terminado en `:` debe absorber la letra de un subpaso siguiente (`a.`).
  * Los subpasos alfabéticos deben mantener su formato `a. [Título] - [Descripción]` con sangría CSS `.content-step--sub`.
- [ ] **13. Tracking Vertical de Figuras Intercaladas:**
  * En páginas con múltiples figuras secuenciales (ej. tutoriales paso a paso), verificar que cada figura se posicione inmediatamente después de su paso instructivo asociado y no se agrupen todas al pie de la página.
- [ ] **14. Supresión de Falsos H1 por Frases de Acción:**
  * 0 apariciones de encabezados `<h1>` o `<h2>` con frases verbales procesales (`Click the`, `Select the`, `Navigate to`, `Expand the`, etc.) al inicio de páginas continuas.
  * Toda instrucción de acción debe renderizarse como párrafo `<p class="content-p">` con su figura correspondiente ubicada debajo.
- [ ] **15. Figuras UI Superiores vs. Cabeceras:**
  * Ninguna figura rectangular con `ch > 60px` debe descartarse por residir en la parte superior (`abs_top < 90`).
- [ ] **16. Subtítulos tras Listas y Figuras al Pie:**
  * Los subtítulos que siguen a listas no deben fusionarse con el paso anterior.
  * Figuras con `top_px >= 850` deben colocarse siempre debajo de su encabezado introductorio.
- [ ] **17. Estructura Tabular de Viñetas y Sangría Colgante:**
  * Todo ítem numerado o alfabético debe estructurarse con `.step-marker` y `.step-body` flexbox.
  * Toda viñeta subordinada a un paso debe tener sangría correspondiente de 32px (`.content-bullet--sub`).
- [ ] **18. Orden Canónico de Secciones H2 Ilustradas:**
  * Todo encabezado H2 debe preceder a la figura que lo ilustra en su subsección (`top_px >= 200`).

---

## 5. Análisis de Solución Arquitectónica para Escalar a Páginas 100+

Para procesar de forma masiva y confiable volúmenes grandes de páginas (101 a 3,700+) sin depender de agregar manualmente cada palabra en un diccionario regex, se concluye la siguiente **estrategia desacoplada en dos niveles**:

### Nivel A: En el Compilador (Solución Inmediata en Ejecución)
1. **Pipeline de Dos Etapas:**
   * **Etapa 1 (Reglas del Dominio):** Mantiene la lista compilada `RE_PATRONES_DESFRAGMENTACION` para términos técnicos de GoAnywhere (`OAuth`, `FileCatalyst`, `Active Directory`, `AS2`, `FTP`, etc.) ejecutándose en $O(N)$ tiempo lineal.
   * **Etapa 2 (Heurística Posicional Dinámica):** La función `_desfragmentar_letras_sueltas()` evalúa cualquier secuencia `Word1 + Letra + Word2`. Si `Letra + Word2` o `Word1 + Letra` forma un vocablo válido en inglés (ej. `t + he` $\rightarrow$ `the`, `p + asswords` $\rightarrow$ `passwords`, `Agen + t` $\rightarrow$ `Agent`), une automáticamente los glifos sin requerir reglas puntuales.
2. **Ventaja:**
   * Corrige insumos ya extraídos sin necesidad de volver a scrapear las páginas existentes de Scribd.

### Nivel B: En el Bot Scraper / Extractor (Solución de Raíz para Futuras Corridas)
1. **Fusión Geométrica de `<span>`:**
   * En Scribd, los `<span>` dentro de `.text_layer` poseen atributos de posición CSS (`left`, `top`, `width` o matrices transform).
   * **Criterio de Proximidad:** En lugar de hacer `.get_text().strip()` sobre cada `<span>`, el extractor debe calcular la distancia horizontal:
     $$\Delta x = \text{left}_{i+1} - (\text{left}_i + \text{width}_i)$$
   * Si $\Delta x < 3.5\text{ px}$ (distancia menor a un espacio en blanco tipográfico) y comparten la misma coordenada vertical $y$, **los textos de ambos spans deben concatenarse directamente sin espacio** (`span_i + span_{i+1}`).
2. **Ventaja:**
   * Elimina el 95% de las fragmentaciones de sintaxis directamente en la extracción de `paginas.json`, entregando texto limpio de origen a cualquier consumidor.
