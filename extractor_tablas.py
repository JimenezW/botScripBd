#!/usr/bin/env python3
"""
extractor_tablas.py - Extractor y estructurador canónico de tablas técnicas para botScribd.

Identifica, analiza y estructura las tablas técnicas presentes en el catálogo
paginas.json y genera un archivo consolidado tablas_documento.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
log = logging.getLogger("extractor_tablas")

DIR_SCRIPT = Path(__file__).resolve().parent
ORIGEN_DEFECTO = DIR_SCRIPT / "reporte" / "goanywhere_mft_user_guide_7_7_0"

def generar_catalogo_tablas(dir_salida: Path = ORIGEN_DEFECTO) -> Path:
    """Construye el catálogo completo de tablas técnicas de las páginas identificadas."""
    tablas: dict[str, list[dict]] = {}

    # ═══════════════════════════════════════════════════════════════════════
    # 1. BLOQUE DE EXPRESIONES (Páginas 591 a 598)
    # Encabezados: Item | Usage | Example
    # ═══════════════════════════════════════════════════════════════════════
    
    # PÁGINA 591: Strings
    tablas["591"] = [{
        "tipo": "tabla",
        "encabezados": ["Item", "Usage", "Example"],
        "clases_columnas": ["col-item", "col-usage", "col-example"],
        "filas": [[
            "Strings",
            "Any text that is enclosed in single or double quotes is treated as a string value.<br><br>"
            "If a string is enclosed with double quotes and a double quote is needed in the string value, "
            "it must be escaped by another double quote. If the string is enclosed in single quotes and a single "
            "quote is needed in the string value, it must be escaped by another single quote.<br><br>"
            "The $ character is a special character used in projects to evaluate GoAnywhere's expression syntax. "
            "When used in a string, it must be escaped by another $, or the string will be treated as an expression. "
            "For example, printing the string 'Dollar $ign' will fail and would need to be entered as 'Dollar $$ign'.",
            "<div style='margin-bottom:8px;'><span class='code-expr'>${x == 'enabled'}</span><br>"
            "<small style='color:#4b5563;'>Returns true if the variable \"x\" equals the string value 'enabled'</small></div>"
            "<div style='margin-bottom:8px;'><span class='code-expr'>${x == \"enabled\"}</span><br>"
            "<small style='color:#4b5563;'>Returns true if the variable \"x\" equals the string value \"enabled\"</small></div>"
            "<div style='margin-bottom:8px;'><span class='code-expr'>${length(\"x\"\"x\")}</span><br>"
            "<small style='color:#4b5563;'>Returns the value 3 since the double quote in the middle is escaped and resolves to one double quote.</small></div>"
            "<div style='margin-bottom:8px;'><span class='code-expr'>${length('x''x')}</span><br>"
            "<small style='color:#4b5563;'>Returns the value 3 since the single quote in the middle is escaped and resolves to one single quote.</small></div>"
            "<div style='margin-bottom:8px;'><span class='code-expr'>${length('x\"\"x')}</span><br>"
            "<small style='color:#4b5563;'>Returns the value 4 as the double quotes in the middle are not escaped since the string is enclosed with single quotes.</small></div>"
            "<div><span class='code-expr'>${length(\"x''x\")}</span><br>"
            "<small style='color:#4b5563;'>Returns the value 4 as the single quotes in the middle are not escaped since the string is enclosed with double quotes.</small></div>"
        ]]
    }]

    # PÁGINA 592: Variables
    tablas["592"] = [{
        "tipo": "tabla",
        "encabezados": ["Item", "Usage", "Example"],
        "clases_columnas": ["col-item", "col-usage", "col-example"],
        "filas": [[
            "Variables",
            "A variable refers to a value which may be a number, string or object. "
            "Multiple variables can be contained within one expression or function.",
            "<div style='margin-bottom:10px;'><span class='code-expr'>${x}</span><br>"
            "<small style='color:#4b5563;'>Returns the value of variable \"x\"</small></div>"
            "<div style='margin-bottom:10px;'><span class='code-expr'>${x + y}</span><br>"
            "<small style='color:#4b5563;'>Returns the result of variable \"x\" added to variable \"y\". Both variables must contain a numeric value.</small></div>"
            "<div style='margin-bottom:10px;'><span class='code-expr'>${x + 2}</span><br>"
            "<small style='color:#4b5563;'>Returns the result of variable \"x\" added to 2</small></div>"
            "<div><span class='code-expr'>${concat(x,y)}</span><br>"
            "<small style='color:#4b5563;'>Returns the combined string values from variables x and y</small></div>"
        ]]
    }]

    # PÁGINA 593: RowSet Values
    tablas["593"] = [{
        "tipo": "tabla",
        "encabezados": ["Item", "Usage", "Example"],
        "clases_columnas": ["col-item", "col-usage", "col-example"],
        "filas": [[
            "RowSet Values",
            "RowSet values can be accessed by placing the column name or column number inside of [ ] (square brackets). "
            "Column names must be placed inside double or single quotes. Additional functions, equations and other "
            "expressions can be placed in the square brackets.",
            "<div style='margin-bottom:10px;'><span class='code-expr'>${data[1]}</span><br>"
            "<small style='color:#4b5563;'>Returns the value of the first column</small></div>"
            "<div style='margin-bottom:10px;'><span class='code-expr'>${data[x]}</span><br>"
            "<small style='color:#4b5563;'>Returns the value of the column with a name contained in the variable \"x\"</small></div>"
            "<div style='margin-bottom:10px;'><span class='code-expr'>${data['columnName']}</span><br>"
            "<small style='color:#4b5563;'>Returns the value of the column with a name of \"columnName\"</small></div>"
            "<div><span class='code-expr'>${data[length(x)]}</span><br>"
            "<small style='color:#4b5563;'>Returns the value of the column with an index that is the length of variable \"x\"</small></div>"
        ]]
    }]

    # PÁGINA 594: Keywords & Method Calls
    keywords_grid = (
        "The following keywords are reserved for use by expressions and cannot be used as variable names in GoAnywhere:<br><br>"
        "<div style='display:grid; grid-template-columns: repeat(3, 1fr); gap: 4px; font-family: Consolas, monospace; font-size: 8.8pt; color: #1e293b; padding-left: 6px;'>"
        "<div>&bull; true</div><div>&bull; le</div><div>&bull; continue</div>"
        "<div>&bull; false</div><div>&bull; ge</div><div>&bull; do</div>"
        "<div>&bull; and</div><div>&bull; not</div><div>&bull; while</div>"
        "<div>&bull; or</div><div>&bull; null</div><div>&bull; dowhile</div>"
        "<div>&bull; ne</div><div>&bull; if</div><div>&bull; for</div>"
        "<div>&bull; eq</div><div>&bull; else</div><div>&bull; foreach</div>"
        "<div>&bull; gt</div><div>&bull; elseif</div><div>&bull; try</div>"
        "<div>&bull; lt</div><div>&bull; break</div><div>&bull; catch</div>"
        "</div>"
    )
    tablas["594"] = [{
        "tipo": "tabla",
        "encabezados": ["Item", "Usage", "Example"],
        "clases_columnas": ["col-item", "col-usage", "col-example"],
        "filas": [
            [
                "Keywords",
                keywords_grid,
                "<div style='margin-bottom:12px;'><span class='code-expr'>${contains('x', 'x', false)}</span><br>"
                "<small style='color:#4b5563;'>False does not need quotes and will not be interpreted as a variable since it is a reserved keyword representing a boolean value.</small></div>"
                "<div style='margin-bottom:12px;'><span class='code-expr'>${x == true}</span><br>"
                "<small style='color:#4b5563;'>Returns if the variable \"x\" is equal to true. The keyword true does not need quotes and will not be interpreted as a variable.</small></div>"
                "<div><span class='code-expr'>${data[1] == null}</span><br>"
                "<small style='color:#4b5563;'>Returns true if the first column in the RowSet is null.</small></div>"
            ],
            [
                "Method Calls",
                "Method Calls are way to retrieve additional METADATA for a variable. "
                "To call a method, insert a colon and the method name immediately after the variable name. "
                "Each variable type (File List, Local File, Email List, etc) provides a different set of methods that are available. "
                "Refer to the <strong>Variables</strong> topic for a complete list of methods that are available for each variable type.",
                "<div><span class='code-expr'>${FileInfo(\"C:\\file.txt\"):size}</span><br>"
                "<small style='color:#4b5563;'>The FileInfo function returns the size of the specified file.</small></div>"
            ]
        ]
    }]

    # PÁGINA 595: Grouping & Functions
    tablas["595"] = [{
        "tipo": "tabla",
        "encabezados": ["Item", "Usage", "Example"],
        "clases_columnas": ["col-item", "col-usage", "col-example"],
        "filas": [
            [
                "Grouping",
                "Parentheses can be placed in expressions to determine the order of precedence.",
                "<div style='margin-bottom:10px;'><span class='code-expr'>${x+(2-1)}</span><br>"
                "<small style='color:#4b5563;'>Calculates the equation in parentheses first before adding it to the variable \"x\"</small></div>"
                "<div><span class='code-expr'>${(x >= 0 || y >= 0) && z == 'enabled'}</span><br>"
                "<small style='color:#4b5563;'>Returns true if \"x\" or \"y\" are greater than zero and \"z\" is equal to \"enabled\"</small></div>"
            ],
            [
                "Functions",
                "A <strong>function</strong> is declared by placing parentheses after the function name. "
                "If parameters are needed, they should be placed inside the parentheses and must be separated by commas. "
                "Each parameter can contain additional functions, equations, strings, variables and any other expression value.",
                "<div style='margin-bottom:8px;'><span class='code-expr'>${Substring('text', 3)}</span><br>"
                "<small style='color:#4b5563;'>Returns the value \"xt\" from the Substring function</small></div>"
                "<div style='margin-bottom:8px;'><span class='code-expr'>${Concat('x','y','z')}</span><br>"
                "<small style='color:#4b5563;'>Returns the value \"xyz\" from the Concat function</small></div>"
                "<div><span class='code-expr'>${Length(Concat('x', 'y', 'z'))}</span><br>"
                "<small style='color:#4b5563;'>Returns the value 3 as the Concat function passed in \"xyz\" to the Length function</small></div>"
            ]
        ]
    }]

    # PÁGINA 596: Numbers
    tablas["596"] = [
        {
            "tipo": "tabla",
            "encabezados": ["Item", "Usage", "Example"],
            "clases_columnas": ["col-item", "col-usage", "col-example"],
            "filas": [[
                "Numbers",
                "An expression may contain whole numbers, decimals or numbers written in scientific notation. "
                "Numbers can optionally be formatted with patterns by using the FormatNumber(number, pattern) function.",
                "<div style='margin-bottom:8px;'><span class='code-expr'>${10.00}</span><br>"
                "<small style='color:#4b5563;'>Represents the value 10.00</small></div>"
                "<div style='margin-bottom:8px;'><span class='code-expr'>${2e2}</span><br>"
                "<small style='color:#4b5563;'>Represents the value 200</small></div>"
                "<div style='margin-bottom:8px;'><span class='code-expr'>${3.820954E6}</span><br>"
                "<small style='color:#4b5563;'>Represents the value 3820954</small></div>"
                "<div><span class='code-expr'>${FormatNumber(3820, '#,###')}</span><br>"
                "<small style='color:#4b5563;'>Returns the value 3,820 as a string</small></div>"
            ]]
        }
    ]

    # PÁGINA 597: Math Operators
    math_ops_grid = (
        "Valid math operators are:<br><br>"
        "<div style='margin-left: 6px; font-size: 8.8pt; line-height: 1.5; color: #1e293b;'>"
        "<div><strong>+</strong> &nbsp; Addition</div>"
        "<div><strong>-</strong> &nbsp; Subtraction</div>"
        "<div><strong>*</strong> &nbsp; Multiplication</div>"
        "<div><strong>/</strong> &nbsp; Division - When dividing numbers that result in a decimal value, the maximum number of digits to the right of the decimal point is 16.</div>"
        "<div><strong>%</strong> &nbsp; Returns the remainder after the first operand is divided by the second operand.</div>"
        "<div><strong>^</strong> &nbsp; Raises the first operand to the power of the second operand.</div>"
        "</div><br>"
        "Expressions containing more than one mathematical step will calculate exponents, multiplication and division before addition and subtraction."
    )
    tablas["597"] = [{
        "tipo": "tabla",
        "encabezados": ["Item", "Usage", "Example"],
        "clases_columnas": ["col-item", "col-usage", "col-example"],
        "filas": [[
            "Math Operators",
            math_ops_grid,
            "<div style='margin-bottom:10px;'><span class='code-expr'>${1+5-3*4/2}</span><br>"
            "<small style='color:#4b5563;'>Returns the value 0</small></div>"
            "<div style='margin-bottom:10px;'><span class='code-expr'>${2^3}</span><br>"
            "<small style='color:#4b5563;'>Returns the value of 2 taken to the power of 3</small></div>"
            "<div><span class='code-expr'>${10%3}</span><br>"
            "<small style='color:#4b5563;'>Returns the value 1</small></div>"
        ]]
    }]

    # PÁGINA 598: Logical & Comparison Operators
    comp_ops_grid = (
        "Both string and symbolic operators are supported.<br><br>"
        "<div style='margin-left: 6px; font-size: 8.8pt; line-height: 1.5; color: #1e293b;'>"
        "<div><strong>==</strong> or <strong>eq</strong> &nbsp; Equals</div>"
        "<div><strong>&lt;&gt;</strong> or <strong>ne</strong> &nbsp; Not Equal</div>"
        "<div><strong>&lt;</strong> or <strong>lt</strong> &nbsp; Less Than</div>"
        "<div><strong>&gt;</strong> or <strong>gt</strong> &nbsp; Greater Than</div>"
        "<div><strong>&lt;=</strong> or <strong>le</strong> &nbsp; Less Than or Equal to</div>"
        "<div><strong>&gt;=</strong> or <strong>ge</strong> &nbsp; Greater Than or Equal to</div>"
        "</div>"
    )
    tablas["598"] = [{
        "tipo": "tabla",
        "encabezados": ["Item", "Usage", "Example"],
        "clases_columnas": ["col-item", "col-usage", "col-example"],
        "filas": [
            [
                "Logical Operators",
                "Multiple conditions can be separated with the logical operators AND (&&) and OR (||). "
                "The AND operator requires both sides to evaluate to true. If the first operand evaluates to false the second operand is not evaluated. "
                "The OR operator requires that either side evaluates to true. If the first operand evaluates to true the second operand is not evaluated.",
                "<div style='margin-bottom:8px;'><span class='code-expr'>${(x == y) || (1+1 eq 2)}</span><br>"
                "<small style='color:#4b5563;'>Returns true as the second parameter is true</small></div>"
                "<div style='margin-bottom:8px;'><span class='code-expr'>${true || EndsWith(x,'csv')}</span><br>"
                "<small style='color:#4b5563;'>The EndsWith function is not called because the first operand is evaluated to true and meets the condition.</small></div>"
                "<div><span class='code-expr'>${(x+y==y+x) && (1+1 eq 2)}</span><br>"
                "<small style='color:#4b5563;'>Returns true as both sides evaluate to true</small></div>"
            ],
            [
                "Comparison Operators",
                comp_ops_grid,
                "<div style='margin-bottom:10px;'><span class='code-expr'>${x == x}</span><br>"
                "<small style='color:#4b5563;'>Returns \"true\" as the left operand equals the operand on the right</small></div>"
                "<div><span class='code-expr'>${1+1 eq 2}</span><br>"
                "<small style='color:#4b5563;'>Returns \"true\" as the result of the left operand equals the value of the right operand</small></div>"
            ]
        ]
    }]

    # ═══════════════════════════════════════════════════════════════════════
    # 2. VARIABLES DE REEMPLAZO EN EXCEL (Página 846)
    # Encabezados: Replacement Variable | Definition
    # ═══════════════════════════════════════════════════════════════════════
    tablas["846"] = [
        {
            "tipo": "p",
            "texto": "The following table describes the Header and Footer replacement variables available in the Write Excel task:"
        },
        {
            "tipo": "tabla",
            "encabezados": ["Replacement Variable", "Definition"],
            "clases_columnas": ["col-item", "col-usage"],
            "filas": [
                ["&amp;P", "Page number."],
                ["&amp;N", "Number of pages."],
                ["&amp;D", "Prints the system date."],
                ["&amp;T", "Prints the system time."],
                ["&amp;F", "The file name of the Excel file."],
                ["&amp;Z", "The file path where the Excel file was created."],
                ["&amp;A", "Name of the sheet."],
                ["&amp;U", "Begins and ends underline text. For example, \"&amp;U This is &amp;U text\" will print \"<u>This is text</u>\"."],
                ["&amp;B", "Begins and ends bold text. For example, \"&amp;B This is &amp;B text\" will print \"<strong>This is text</strong>\"."],
                ["&amp;I", "Begins and ends italicized text. For example, \"&amp;I This is &amp;I text\" will print \"<em>This is text</em>\"."]
            ]
        }
    ]

    # ═══════════════════════════════════════════════════════════════════════
    # 3. AUDIT LOG SETTINGS / PROTOCOLS (Página 2858)
    # Encabezados: Protocol | SD-ID | Type
    # ═══════════════════════════════════════════════════════════════════════
    tablas["2858"] = [
        {
            "tipo": "tabla",
            "encabezados": ["Protocol", "SD-ID", "Type"],
            "clases_columnas": ["col-item", "col-item", "col-usage"],
            "filas": [
                ["AS2", "gamft-as2@46583", "AS2 Audit Log"],
                ["FTP", "gamft-ftp@46583", "FTP Audit Log"],
                ["FTPS", "gamft-ftps@46583", "FTPS Audit Log"],
                ["SFTP", "gamft-sftp@46583", "SFTP Audit Log"],
                ["GoDrive", "gamft-godrive@46583", "GoDrive Audit Log"],
                ["GoFast", "gamft-gofast@46583", "GoFast Audit Log"]
            ]
        },
        {
            "tipo": "p",
            "texto": "Structured data parameters are split in two columns. The column on the left displays the available parameters and the column on the right displays the parameters that are sent to the Syslog server. Click to select parameters and then use the direction buttons between the columns to move parameters to the appropriate side. Syslog messages will not be sent for a protocol when there are no parameters selected."
        },
        {
            "tipo": "p",
            "texto": "The following table lists the optional structured data parameters that can be selected for each SD-ID:"
        },
        {
            "tipo": "tabla",
            "encabezados": ["SD-ID", "Data Parameters"],
            "clases_columnas": ["col-item", "col-usage"],
            "filas": [
                [
                    "gamft-admin@46583",
                    "<div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; font-size: 8.5pt; font-family: Consolas, monospace;'>"
                    "<div>entry_id</div><div>admin_user_id</div><div>comp_name</div><div>domain</div>"
                    "<div>entry_type</div><div>admin_user_name</div><div>field_label</div><div>old_value</div>"
                    "<div>comp_type</div><div>created_on</div><div>new_value</div><div>override_message</div>"
                    "<div>comp_id</div><div></div><div></div><div></div>"
                    "</div>"
                ]
            ]
        }
    ]

    # ═══════════════════════════════════════════════════════════════════════
    # 4. CODIFICACIONES DE ARCHIVOS SOPORTADAS (Páginas 3611 a 3613)
    # Encabezados: Name | Alias or Aliases | Description
    # ═══════════════════════════════════════════════════════════════════════
    tablas["3611"] = [
        {
            "tipo": "h1",
            "texto": "Supported File Encodings"
        },
        {
            "tipo": "p",
            "texto": "The following table lists file encodings supported by GoAnywhere. Support for encodings may vary depending on the version of JVM installed and which region the host machine is marked as residing in."
        },
        {
            "tipo": "tabla",
            "encabezados": ["Name", "Alias or Aliases", "Description"],
            "clases_columnas": ["col-item", "col-usage", "col-example"],
            "filas": [
                ["CESU-8", "CESU8 csCESU-8", "Unicode CESU-8"],
                ["IBM00858", "cp858 858 PC-Multilingual-850+euro cp00858 ccsid00858", "Variant of Cp850 with Euro character"],
                ["IBM437", "ibm437 437 ibm-437 cspc8codepage437 cp437 windows-437", "MS-DOS United States, Australia, New Zealand, South Africa"],
                ["IBM775", "ibm-775 ibm775 775 cp775", "PC Baltic"],
                ["IBM850", "cp850 cspc850multilingual ibm850 850 ibm-850", "MS-DOS Latin-1"],
                ["IBM852", "csPCp852 ibm-852 ibm852 852 cp852", "MS-DOS Latin-2"],
                ["IBM855", "ibm855 855 ibm-855 cp855 cspcp855", "IBM Cyrillic"],
                ["IBM857", "ibm857 857 cp857 csIBM857 ibm-857", "IBM Turkish"],
                ["IBM862", "csIBM862 cp862 ibm862 862 cspc862latinhebrew ibm-862", "PC Hebrew"],
                ["IBM866", "ibm866 866 ibm-866 csIBM866 cp866", "MS-DOS Russian"]
            ]
        }
    ]

    tablas["3612"] = [{
        "tipo": "tabla",
        "encabezados": ["Name", "Alias or Aliases", "Description"],
        "clases_columnas": ["col-item", "col-usage", "col-example"],
        "filas": [
            ["ISO-8859-1", "819 ISO8859-1 l1 ISO_8859-1:1987 ISO_8859-1 8859_1 iso-ir-100 latin1 cp819 ISO8859_1 IBM819 ISO_8859_1 IBM-819 csISOLatin1", "ISO-8859-1, Latin Alphabet No. 1"],
            ["ISO-8859-2", "ISO8859-2 ibm912 l2 ISO_8859-2 8859_2 cp912 ISO_8859-2:1987 iso8859_2 iso-ir-101 latin2 912 csISOLatin2 ibm-912", "Latin Alphabet No. 2"],
            ["ISO-8859-4", "8859_4 latin4 l4 cp914 ISO_8859-4:1988 ibm914 ISO_8859-4 iso-ir-110 iso8859_4 csISOLatin4 iso8859-4 914 ibm-914", "Latin Alphabet No. 4"],
            ["ISO-8859-5", "ISO_8859-5:1988 csISOLatinCyrillic iso-ir-144 iso8859_5 cp915 8859_5 ibm-915 ISO_8859-5 ibm915 915 cyrillic ISO8859-5", "Latin/Cyrillic Alphabet"],
            ["ISO-8859-7", "greek 8859_7 greek8 ibm813 ISO_8859-7 iso8859_7 ELOT_928 cp813 ISO_8859-7:1987 sun_eu_greek csISOLatinGreek iso-ir-126 813 iso8859-7 ECMA-118 ibm-813", "Latin/Greek Alphabet (ISO-8859-7:2003)"],
            ["ISO-8859-9", "ibm-920 ISO_8859-9 8859_9 ISO_8859-9:1989 ibm920 latin5 l5 iso8859_9 cp920 920 iso-ir-148 ISO8859-9 csISOLatin5", "Latin Alphabet No. 5"],
            ["ISO-8859-13", "iso_8859-13 ISO8859-13 iso8859_13 8859_13", "Latin Alphabet No. 7"],
            ["ISO-8859-15", "ISO8859-15 LATIN0 ISO8859_15_FDIS ISO8859_15 cp923 8859_15 L9 ISO-8859-15 IBM923 csISOLatin9 ISO_8859-15 IBM-923 csISOLatin0 923 LATIN9", "Latin Alphabet No. 9"],
            ["KOI8-R", "koi8_r koi8 cskoi8r", "KOI8-R, Russian"],
            ["KOI8-U", "koi8_u", "KOI8-U, Ukrainian"]
        ]
    }]

    tablas["3613"] = [{
        "tipo": "tabla",
        "encabezados": ["Name", "Alias or Aliases", "Description"],
        "clases_columnas": ["col-item", "col-usage", "col-example"],
        "filas": [
            ["US-ASCII", "ANSI_X3.4-1968 cp367 csASCII iso-ir-6 ASCII iso_646.irv:1983 ANSI_X3.4-1986 ascii7 default ISO_646.irv:1991 ISO646-US IBM367 646 us", "American Standard Code for Information Interchange"],
            ["UTF-8", "unicode-1-1-utf-8 UTF8", "Eight-bit Unicode (or UCS) Transformation Format"],
            ["UTF-16", "UTF_16 unicode utf16 UnicodeBig", "Sixteen-bit Unicode (or UCS) Transformation Format, byte order identified by an optional byte-order mark"],
            ["UTF-16BE", "X-UTF-16BE UTF_16BE ISO-10646-UCS-2 UnicodeBigUnmarked", "Sixteen-bit Unicode (or UCS) Transformation Format, big-endian byte order"],
            ["UTF-16LE", "UnicodeLittleUnmarked UTF_16LE X-UTF-16LE", "Sixteen-bit Unicode (or UCS) Transformation Format, little-endian byte order"]
        ]
    }]

    # Guardar catálogo JSON
    ruta_salida = dir_salida / "tablas_documento.json"
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump({"total_paginas_con_tablas": len(tablas), "paginas": tablas}, f, indent=2, ensure_ascii=False)

    log.info("Catálogo de tablas guardado exitosamente en: %s (%d páginas con tablas)", ruta_salida, len(tablas))
    return ruta_salida


if __name__ == "__main__":
    generar_catalogo_tablas()
