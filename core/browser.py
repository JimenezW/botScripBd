"""
Módulo de Inicialización y Gestión del Navegador Stealth (Playwright).
Aplica directivas avanzadas de evasión para neutralizar detección de WebDriver y WAFs.
"""

import time
import random
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
from playwright_stealth import Stealth
from config import BotConfig


class BrowserManager:
    """Administrador del ciclo de vida del navegador Chromium con perfil Stealth."""

    def __init__(self, config: BotConfig):
        self.config = config
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def start(self) -> Page:
        """
        Inicia la instancia de Playwright, lanza Chromium con flags de evasión,
        configura el contexto y retorna la página principal protegida con stealth.
        """
        self.playwright = sync_playwright().start()

        chromium_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-infobars",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1920,1080",
            "--disable-gpu",
        ]

        self.browser = self.playwright.chromium.launch(
            headless=self.config.headless,
            args=chromium_args
        )

        headers = {
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

        self.context = self.browser.new_context(
            viewport={"width": self.config.viewport_width, "height": self.config.viewport_height},
            user_agent=self.config.user_agent,
            locale="es-ES",
            timezone_id="America/Mexico_City",
            extra_http_headers=headers
        )

        self.page = self.context.new_page()

        # Aplicar el plugin playwright-stealth para enmascarar navigator.webdriver, hardwareConcurrency, etc.
        Stealth().apply_stealth_sync(self.page)

        # Inyección de scripts adicionales para blindaje extra
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
        """)

        return self.page

    def dismiss_cookie_banners(self) -> bool:
        """
        Detecta y cierra los banners comunes de cookies (Osano CMP, OneTrust o Scribd)
        para despejar el viewport y evitar que intercepten clics en los botones de página.
        """
        if not self.page:
            return False

        consent_selectors = [
            ".osano-cm-accept-all",
            "#onetrust-accept-btn-handler",
            "button:has-text('Aceptar todas')",
            "button:has-text('Aceptar cookies')",
            "button:has-text('Accept all')",
            ".osano-cm-dialog__close",
            "button[aria-label='Cerrar']"
        ]

        for selector in consent_selectors:
            try:
                locator = self.page.locator(selector).first
                if locator.is_visible(timeout=1500):
                    time.sleep(random.uniform(0.3, 0.8))
                    locator.click()
                    time.sleep(random.uniform(0.5, 1.0))
                    return True
            except Exception:
                continue

        return False

    def close(self):
        """Cierra de forma limpia todas las instancias y recursos del navegador."""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass


if __name__ == "__main__":
    from config import BotConfig
    cfg = BotConfig(headless=False)
    bm = BrowserManager(cfg)
    try:
        p = bm.start()
        p.goto("https://es.scribd.com/document/855660163/ga7-7-0-user-guide")
        bm.dismiss_cookie_banners()
        print(f"[OK] Navegador cargado exitosamente. Título: {p.title()}")
        time.sleep(3)
    finally:
        bm.close()
