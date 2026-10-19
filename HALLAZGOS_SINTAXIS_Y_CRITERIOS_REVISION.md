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
- [ ] **8. Supresión de Duplicados Multi-Capa:**
  * 0 apariciones de duplicaciones por desglose de spans (`ba sic`, `dmi n`, etc.).
- [ ] **9. Integridad de Encabezados H2:**
  * Ningún elemento `<h2>` con menos de 6 caracteres (ej. no debe haber `<h2>Agen</h2>`, `<h2>FT</h2>`).

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
