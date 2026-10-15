"""
Módulo de Detección y Evasión de Intersticiales Publicitarios (Ad-Gate).
Monitorea temporizadores de anuncios y gestiona el botón 'Omitir anuncio' para desbloquear lotes.
"""

import time
import random
from typing import Optional
from playwright.sync_api import Page


class AdGateHandler:
    """Gestiona la detección, temporizadores y omisión de anuncios entre páginas en Scribd."""

    def __init__(self, page: Page, timeout_seconds: int = 15):
        self.page = page
        self.timeout_seconds = timeout_seconds

    def is_ad_gate_present(self) -> bool:
        """Determina si el widget de anuncio o intersticial está bloqueando la lectura."""
        indicators = [
            "text=Desbloquea las próximas",
            "text=después de un anuncio",
            "button:has-text('Omitir anuncio')",
            "button:has-text('Skip ad')",
            ".ad_interstitial",
            "[data-testid*='ad-gate']"
        ]
        for sel in indicators:
            try:
                if self.page.locator(sel).first.is_visible(timeout=500):
                    return True
            except Exception:
                continue
        return False

    def handle_ad_gate(self) -> bool:
        """
        Si un Ad-Gate está activo, intenta omitirlo inmediatamente o espera a que
        el temporizador concluya para desbloquear el siguiente lote de páginas.
        """
        if not self.is_ad_gate_present():
            return False

        # 1. Intentar hacer clic en 'Omitir anuncio' si ya está habilitado
        skip_selectors = [
            "button:has-text('Omitir anuncio')",
            "button:has-text('Omitir')",
            "button:has-text('Skip ad')",
            "button:has-text('Skip')",
            "[aria-label*='Omitir']"
        ]

        for sel in skip_selectors:
            try:
                btn = self.page.locator(sel).first
                if btn.is_visible(timeout=800):
                    time.sleep(random.uniform(0.6, 1.2))
                    btn.click()
                    time.sleep(random.uniform(1.0, 1.8))
                    return True
            except Exception:
                continue

        # 2. Si hay cuenta regresiva, esperar activamente hasta que desaparezca el anuncio
        start_time = time.time()
        while time.time() - start_time < self.timeout_seconds:
            # Verificar si ya apareció el botón de omitir durante la cuenta atrás
            for sel in skip_selectors:
                try:
                    btn = self.page.locator(sel).first
                    if btn.is_visible(timeout=400):
                        time.sleep(random.uniform(0.5, 1.0))
                        btn.click()
                        time.sleep(random.uniform(1.0, 1.8))
                        return True
                except Exception:
                    pass

            if not self.is_ad_gate_present():
                # El anuncio desapareció y las páginas se desbloquearon
                time.sleep(random.uniform(0.8, 1.5))
                return True

            time.sleep(0.5)

        return False
