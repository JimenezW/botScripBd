"""
Módulo de Navegación y Paginación en Scribd.
Controla el avance secuencial mediante el botón de siguiente página, saltos directos
y sincronización de renderizado en el visor web.
"""

import time
import random
import re
from typing import Optional
from playwright.sync_api import Page
from config import BotConfig
from core.ad_gate import AdGateHandler


class DocumentNavigator:
    """Controla el avance secuencial y posicionamiento dentro del visor de Scribd."""

    def __init__(self, page: Page, config: BotConfig):
        self.page = page
        self.config = config
        self.ad_handler = AdGateHandler(page, timeout_seconds=config.ad_timeout)

    def get_current_page_number(self) -> int:
        """
        Lee el número de página actual desde el input de salto de la barra lateral
        o mediante inspección del elemento activo en el visor.
        """
        try:
            # Buscar el input de salto de página
            input_locator = self.page.locator("input[aria-label*='página'], input[aria-label*='page']").first
            if input_locator.is_visible(timeout=1000):
                val = input_locator.input_value()
                if val and val.isdigit():
                    return int(val)
        except Exception:
            pass

        # Alternativa: buscar en contenedores .outer_page con data-page-number o similar
        try:
            pages = self.page.locator(".outer_page").all()
            if pages:
                # Retornar el índice o aproximación según el scroll actual
                return len(pages)
        except Exception:
            pass

        return 1

    def get_total_pages(self) -> Optional[int]:
        """Obtiene el número total de páginas reportadas por el visor o metadatos."""
        # 1. Intentar leer del indicador en la barra lateral
        try:
            text_el = self.page.locator("span:has-text('/'), div:has-text('/')").all_inner_texts()
            for t in text_el:
                m = re.search(r"/\s*(\d+)", t)
                if m:
                    return int(m.group(1))
        except Exception:
            pass

        # 2. Intentar buscar en atributos del visor
        try:
            doc_container = self.page.locator("[data-total-pages], [data-page-count]").first
            if doc_container.is_visible(timeout=500):
                attr = doc_container.get_attribute("data-total-pages") or doc_container.get_attribute("data-page-count")
                if attr and attr.isdigit():
                    return int(attr)
        except Exception:
            pass

        return None

    def advance_next_page(self) -> bool:
        """
        Avanza una página haciendo clic en el control de página siguiente o emulando PageDown.
        Gestiona automáticamente anuncios publicitarios en caso de presentarse.
        """
        # 1. Comprobar y resolver Ad-Gates antes del avance
        if self.ad_handler.is_ad_gate_present():
            self.ad_handler.handle_ad_gate()

        page_before = self.get_current_page_number()

        # 2. Localizar y accionar el botón de 'Página siguiente'
        next_button_selectors = [
            "button[aria-label*='siguiente']",
            "button[aria-label*='next']",
            "button[aria-label*='Next']",
            ".IconButtonBase-module_large_hJBmho",
            "button.RGekOz"
        ]

        clicked = False
        for sel in next_button_selectors:
            try:
                # El botón de siguiente página suele estar situado justo debajo del input de página
                buttons = self.page.locator(sel).all()
                for btn in buttons:
                    if btn.is_visible():
                        btn.click()
                        clicked = True
                        break
                if clicked:
                    break
            except Exception:
                continue

        # 3. Si el botón no respondió o no se halló, usar la tecla PageDown
        if not clicked:
            try:
                self.page.keyboard.press("PageDown")
                clicked = True
            except Exception:
                pass

        # 4. Pausa de cortesía humana con Jitter
        delay = random.uniform(self.config.min_delay, self.config.max_delay)
        time.sleep(delay)

        # 5. Comprobar si tras avanzar apareció un Ad-Gate
        if self.ad_handler.is_ad_gate_present():
            self.ad_handler.handle_ad_gate()

        # 6. Desplazamiento sutil de ratón para disparar lazy loading
        try:
            self.page.mouse.wheel(0, random.randint(150, 300))
        except Exception:
            pass

        page_after = self.get_current_page_number()
        return clicked or (page_after > page_before)

    def jump_to_page(self, target_page: int) -> bool:
        """Salta directamente a una página específica mediante el input de paginación."""
        try:
            input_locator = self.page.locator("input[aria-label*='página'], input[aria-label*='page']").first
            if input_locator.is_visible(timeout=1500):
                input_locator.click()
                input_locator.fill(str(target_page))
                input_locator.press("Enter")
                time.sleep(random.uniform(self.config.min_delay, self.config.max_delay))
                if self.ad_handler.is_ad_gate_present():
                    self.ad_handler.handle_ad_gate()
                return True
        except Exception:
            pass
        return False
