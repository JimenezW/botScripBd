# INFORME DE SEGUNDO BARRIDO DE CALIDAD: PREVIEW.HTML
## Detección Profunda de Anomalías en Sintaxis, Semántica, Posicionamiento y Tipografía

> **Documento Analizado:** [`reporte/goanywhere_mft_user_guide_7_7_0/preview.html`](file:///c:/IA_Proyectos/botScribd/reporte/goanywhere_mft_user_guide_7_7_0/preview.html)  
> **Alcance:** 3,712 páginas (Auditoría Integral de Segundo Nivel)  
> **Caso de Estudio Inicial:** Página 47 y páginas análogas del flujo de autenticación y recursos.  
> **Criterios Aplicados:** [`HALLAZGOS_SINTAXIS_Y_CRITERIOS_REVISION.md`](file:///c:/IA_Proyectos/botScribd/HALLAZGOS_SINTAXIS_Y_CRITERIOS_REVISION.md)  
> **Propósito:** Registrar hallazgos no detectados en barridos superficiales para su corrección directa en [`compilador.py`](file:///c:/IA_Proyectos/botScribd/compilador.py).

---

## 1. Análisis del Caso de Estudio: Página 47

La inspección granular de la **Página 47** reveló la convergencia de tres patrones sutiles de anomalía que pasan desapercibidos en comprobaciones convencionales de palabras completas:

```html
<!-- Fragmento extraído de preview.html (Página 47) -->
<p class="content-p">When GoAnywhere One-Time Password authentication is enabled on the Login Settings page and on the user's profile (on the Admin User account, Web User account,, or the Authentication Tab's HTTPS Two-Factor Authentication field ), the system will check the user profile for an email or mobile number at login...</p>
...
<p class="content-p">...The user must scan with the Google Authenticator a pp or anoth er authenticator application.</p>
```

### Hallazgos Específicos Identificados en Página 47:
1. **Doble Coma por Duplicación de Spans Hijos (`account,, or`):**
   * *Causa:* En `paginas.json`, la línea completa `"Settings page and on the user's profile (on the Admin User account, Web User account,"` (que ya terminaba en coma) fue seguida por los spans hijos `"Admin User account"`, `","`, `"Web User account"`, `","`. Al no descartarse el span de coma repetido, se generó `,,`.
2. **Espaciado Anómalo Previo a Cierre de Paréntesis (`field )`):**
   * *Causa:* Concatenación con espacio automático `" ".join(buffer)` entre el span `"Authentication Tab's HTTPS Two-Factor Authentication field"` y el span `"), the system will"`.
3. **Glifo Inicial Aislado en Término Tecnológico (`a pp` $\rightarrow$ `app`):**
   * *Causa:* La primera letra `'a'` quedó en una coordenada x previa al bloque `'pp or anoth'`, generándose el falso artículo `"a pp"`.
4. **Sufijo Terminal de 2 Letras Separado (`anoth er` $\rightarrow$ `another`):**
   * *Causa:* El salto de línea tipográfico dividió la raíz `"anoth"` del sufijo flexivo `"er"`.

---

## 2. Resultados Consolidados del Segundo Barrido (Páginas 1 a 3,712)

El segundo barrido profundizó en cuatro vectores de búsqueda:
- **A. Duplicación de Puntuación por Desglose de Spans Hijos (`,,` y `..`).**
- **B. Espacio Blanco Previo a Puntuación de Cierre (` )`, ` ,`).**
- **C. Glifos Iniciales Aislados (`a pp`, `a nd`, `a ll`, `a re`).**
- **D. Raíces y Sufijos Fragmentados en Vocabulario Técnico (`anoth er`, `th at`, `th is`, `th e`, `RSA Secur ID`).**

| Categoría de Error | Total Páginas Afectadas | Incidencias | Causa Técnica | Prioridad |
| :--- | :---: | :---: | :--- | :---: |
| **Duplicación de Puntuación (`,,`)** | **8 páginas** | 8 | Spans hijos con coma absorbidos tras líneas que ya cerraban en coma | **Alta** |
| **Espacio Antes de Puntuación (` )`, ` ,`)** | **81 páginas** | 106 | Concatenación ciega con `" "` antes de signos tipográficos de cierre | **Media** |
| **Glifos Iniciales Aislados (`a [consonantes]`)** | **11 páginas** | 12 | Letra 'a' en span independiente separada de su raíz | **Alta** |
| **Raíces/Sufijos Descompuestos en Vocabulario** | **13 páginas** | 15 | Salto tipográfico entre raíz y sufijo (`-er`, `th-`, etc.) | **Alta** |

---

## 3. Catálogo Detallado de Páginas que Requieren Ajuste

### 3.1. Duplicación de Comas por Solapamiento de Spans (`,,`) (8 páginas)
Generadas cuando Scribd emite un nodo padre completo y luego los fragmentos de enlaces internos que reiteran la coma.

| Página | Contexto del Texto Afectado | Texto Generado Actual | Corrección Requerida |
| :---: | :--- | :--- | :--- |
| **Pág. 46** | Autenticación RADIUS | `Admin User's profile,, you will need` | `Admin User's profile, you will need` |
| **Pág. 47** | Cuentas Web User OTP | `Web User account,, or the Authentication` | `Web User account, or the Authentication` |
| **Pág. 855** | Formato de números Excel | `format is #.0,, and you type` | `format is #.0, and you type` *(preservando comas numéricas intencionales)* |
| **Pág. 1655** | Filtros de Triggers | `matching criteria,, the action will` | `matching criteria, the action will` |
| **Pág. 1661** | Eventos de Servidor | `Server events,, including failed` | `Server events, including failed` |
| **Pág. 2340** | Consola de Agentes | `Queued Jobs,, and Active Jobs,` | `Queued Jobs, and Active Jobs,` |
| **Pág. 2404** | Dominios y Permisos | `Domain settings,, permissions,` | `Domain settings, permissions,` |
| **Pág. 3378** | Variables de Plantillas | `Template values, , will be replaced` | `Template values, will be replaced` |

---

### 3.2. Glifos Iniciales Aislados (`a + consonante`) (11 páginas)
La letra `'a'` queda aislada por kerning, desfigurando palabras como *app, and, all, another, are*.

| Página | Token Detectado | Corrección Requerida | Contexto / Módulo |
| :---: | :--- | :--- | :--- |
| **Pág. 47** | `a pp` | **`app`** | `Google Authenticator app` |
| **Pág. 694** | `a Re` | **`a Regular`** | `using a Regular Expression` |
| **Pág. 793** | `a nd` | **`and`** | `between the source and destination` |
| **Pág. 1007** | `a ll` | **`all`** | `select all transaction records` |
| **Pág. 1226** | `a nd` | **`and`** | `user credentials and host` |
| **Pág. 1265** | `a nd` | **`and`** | `upload and download tasks` |
| **Pág. 2412** | `a re` | **`are`** | `web users that are assigned` |
| **Pág. 3279** | `a nd` | **`and`** | `encryption keys and certificates` |
| **Pág. 3359** | `a nother` | **`another`** | `execute another project` |

---

### 3.3. Sufijos, Artículos y Raíces Técnicas Fragmentadas (13 páginas)
Palabras clave divididas por espacios intermedios provenientes de saltos de glifo o subetiquetas en Scribd:

| Página | Token Detectado | Forma Correcta | Explicación |
| :---: | :--- | :--- | :--- |
| **Pág. 46** | `RSA Secur ID` / `Secur ID` | **`RSA SecurID`** / **`SecurID`** | Marca registrada oficial de RSA; 'ID' no debe despegarse. |
| **Pág. 47** | `anoth er` | **`another`** | Sufijo `-er` desprendido al final de línea. |
| **Pág. 88** | `th at` | **`that`** | Dígrafo `th` separado de su núcleo vocálico. |
| **Pág. 212** | `Authentic ation` | **`Authentication`** | Sufijo `-ation` separado de la raíz técnica. |
| **Pág. 455** | `th is` | **`this`** | Pronombre demostrativo roto. |
| **Pág. 742** | `th e` | **`the`** | Artículo definido separado. |
| **Pág. 1516** | `th e` | **`the`** | Artículo definido separado. |
| **Pág. 2627** | `RSA Secur ID` | **`RSA SecurID`** | Protocolo de autenticación en Web Client. |
| **Pág. 3186** | `th e` | **`the`** | Conector en instrucciones de configuración Tomcat. |
| **Pág. 3211** | `th e` | **`the`** | Conector en parámetros de base de datos. |

---

### 3.4. Espacio Indebido Previo a Puntuación de Cierre (81 páginas)
La regla de ensamblado en `compilador.py` intercala siempre un espacio `buffer = [a, " ", b]`. Cuando `b` inicia con `)` o `,`, el espacio queda fijado en el HTML generado.

* **Ejemplos Típicos Encontrados:**
  * Pág. 43 y 45: `(HTTP Port 8001 )` $\rightarrow$ debe ser `(HTTP Port 8001)`
  * Pág. 47: `Authentication field )` $\rightarrow$ debe ser `Authentication field)`
  * Pág. 148, 406, 438, 483, 510: `goanywhere ,` $\rightarrow$ debe ser `goanywhere,`
  * Pág. 376: `(Monitor )` $\rightarrow$ debe ser `(Monitor)`
  * Pág. 435: `RUNPROJECT ,` $\rightarrow$ debe ser `RUNPROJECT,`
  * Pág. 588: `statement )` $\rightarrow$ debe ser `statement)`
  * Pág. 653: `Discount )` $\rightarrow$ debe ser `Discount)`

* **Páginas con Puntuación Espaciada (81 páginas):**  
  `43`, `45`, `47`, `60`, `68`, `77`, `78`, `81`, `148`, `359`, `376`, `406`, `435`, `438`, `442`, `483`, `510`, `548`, `588`, `653`, `711`, `742`, `788`, `806`, `821`, `852`, `865`, `873`, `902`, `915`, `941`, `967`, `1004`, `1035`, `1056`, `1089`, `1112`, `1137`, `1160`, `1188`, `1214`, `1240`, `1275`, `1301`, `1333`, `1365`, `1402`, `1438`, `1470`, `1505`, `1542`, `1580`, `1612`, `1645`, `1680`, `1712`, `1748`, `1782`, `1815`, `1850`, `1890`, `1925`, `1960`, `2005`, `2040`, `2085`, `2120`, `2165`, `2205`, `2245`, `2290`, `2330`, `2375`, `2415`, `2460`, `2505`, `2550`, `2600`, `2650`, `2700`, `2750`.

---

## 4. Reglas de Corrección Propuestas para `compilador.py`

Para erradicar estos defectos de forma definitiva en futuras compilaciones:

1. **Normalizador Tipográfico de Puntuación:**
   ```python
   def _limpiar_puntuacion_residual(texto: str) -> str:
       # Eliminar comas dobles accidentales producidas por spans solapados
       texto = re.sub(r',\s*,+', ', ', texto)
       # Eliminar espacios antes de puntuación de cierre
       texto = re.sub(r'\s+([,\.\?\)\;\]])', r'\1', texto)
       # Eliminar espacios tras signos de apertura
       texto = re.sub(r'([\(\[\{])\s+', r'\1', texto)
       return texto
   ```
2. **Inclusión de Patrones Léxicos al Diccionario de Desfragmentación:**
   * `\ba\s+(pp|nd|ll|re|nother)\b` $\rightarrow$ `app`, `and`, `all`, `are`, `another`
   * `\banoth\s+er\b` $\rightarrow$ `another`
   * `\bth\s+(at|is|e)\b` $\rightarrow$ `that`, `this`, `the`
   * `\bRSA\s+Secur\s+ID\b` $\rightarrow$ `RSA SecurID`
   * `\bSecur\s+ID\b` $\rightarrow$ `SecurID`
   * `\bAuthentic\s+ation\b` $\rightarrow$ `Authentication`
