import os
from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright
from rich.console import Console

console = Console()


class BrowserController:
    def __init__(self, user_data_dir: str = ".browser_session", headless: bool = False, slow_mo: int = 100):
        self.user_data_dir = str(Path(user_data_dir).resolve())
        self.headless = headless
        self.slow_mo = slow_mo
        self.playwright: Playwright = None
        self.context: BrowserContext = None
        self.page: Page = None

    def start(self) -> Page:
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            slow_mo=self.slow_mo,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"],
        )
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()
        return self.page

    def navigate_and_wait_for_auth(self, url: str, wait_selector: str = None) -> Page:
        if not self.page:
            self.start()

        console.print(f"[bold cyan]Navigating to:[/] {url}")
        self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(2500)  # Wait for possible SSO redirect

        cur_url = self.page.url.lower()
        is_login_page = ("login" in cur_url or "idaas" in cur_url or "w3id" in cur_url or "oidc" in cur_url or "auth" in cur_url)
        
        cas_ready = False
        if not is_login_page:
            if wait_selector:
                try:
                    self.page.wait_for_selector(wait_selector, timeout=3000)
                    cas_ready = True
                except Exception:
                    cas_ready = False
            else:
                # Check for CAS form markers
                if self.page.locator("select[name*='serviceType'], select[name*='formBean'], input[name*='actyNum'], input[value*='Search']").count() > 0:
                    cas_ready = True

        if not cas_ready or is_login_page:
            console.print("[bold yellow]================================================================[/]")
            console.print("[bold yellow]  LOGIN SSO / MFA DIPERLUKAN DI BROWSER                         [/]")
            console.print("[yellow]  1. Silakan login w3id / SSO & selesaikan verifikasi di browser[/]")
            console.print("[yellow]  2. Pastikan halaman CAS yang dituju sudah terbuka sempurna    [/]")
            console.print("[bold yellow]================================================================[/]")
            input("\n>>> SETELAH HALAMAN CAS TERBUKA, TEKAN [ENTER] DI TERMINAL INI UNTUK LANJUT... <<<\n")
            self.page.wait_for_load_state("domcontentloaded")
            self.page.wait_for_timeout(1500)
        else:
            console.print("[bold green]Halaman CAS siap dan terverifikasi![/]")

        return self.page

    def close(self):
        if self.context:
            self.context.close()
            self.context = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
