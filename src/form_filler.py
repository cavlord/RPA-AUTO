import time
from typing import Any, Dict, List
from playwright.sync_api import Page
from rich.console import Console

console = Console()

READONLY_FIELDS = {
    "originactionstatus", "status", "usernum", "creatornum", 
    "actynum", "createdate", "updatedate", "q", "qt"
}


class FormFiller:
    def __init__(self, page: Page, form_url: str):
        self.page = page
        self.form_url = form_url

    def fill_and_save_draft(self, entry: Dict[str, Any]) -> bool:
        row_num = entry.get("_row_number", "?")
        console.print(f"\n[bold cyan]==================================================[/]")
        console.print(f"[bold cyan]  Memproses Data Baris ke-{row_num} ...[/]")
        console.print(f"[bold cyan]==================================================[/]")

        # 1. Navigate to Add Activity form
        console.print(f"[cyan]Membuka form input:[/] {self.form_url}")
        self.page.goto(self.form_url, wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(1500)

        # 2. Track start date (prefer the real report date field)
        start_date_val = None
        for key, val in entry.items():
            k_lower = str(key).lower()
            if k_lower == "activityreportdate" and str(val).strip():
                start_date_val = str(val).strip()
                break
        if not start_date_val:
            for key, val in entry.items():
                k_lower = str(key).lower()
                if k_lower in READONLY_FIELDS or k_lower.startswith("_"):
                    continue
                if "date" in k_lower and "end" not in k_lower and "extr" not in k_lower and str(val).strip():
                    start_date_val = str(val).strip()
                    break

        # 3. Fill fields
        for field_name, value in entry.items():
            if field_name.startswith("_") or not str(field_name).strip():
                continue

            clean_name = str(field_name).strip().lower()
            if clean_name in READONLY_FIELDS:
                continue

            val_str = str(value).strip()
            if not val_str:
                continue

            # Safe truncate description to 70 chars
            if "desc" in clean_name or "actydesc" in clean_name:
                if len(val_str) > 70:
                    console.print(f"[yellow]Peringatan: Memotong '{field_name}' menjadi 70 karakter: '{val_str[:70]}'[/]")
                    val_str = val_str[:70]

            console.print(f"[white]Mengisi [/][bold yellow]{field_name}[/][white] -> [/][green]{val_str}[/]")
            self._fill_field(field_name, val_str)

            # Cascading wait if serviceType was selected
            if "servicetype" in clean_name:
                console.print("[cyan]Menunggu cascading reload dropdown Detail (AJAX)...[/]")
                self.page.wait_for_timeout(2000)

        # 4. End Date is only used when Service Type = Administration
        # and Service Detail = Absence (leave). Otherwise it is ignored.
        if self._is_absence(entry):
            end_date_val = None
            for key, val in entry.items():
                if str(key).strip().lower() == "activityreportdateend" and str(val).strip():
                    end_date_val = str(val).strip()
                    break
            end_date_val = end_date_val or start_date_val

            if not end_date_val:
                console.print(f"[bold red]GAGAL - Absence membutuhkan End Date tetapi tidak ada nilai (baris {row_num}).[/]")
                return False

            loc = self._find_end_date_locator()
            if loc is None:
                console.print(f"[bold red]GAGAL - Field End Date tidak muncul setelah memilih Absence (baris {row_num}).[/]")
                return False

            console.print(f"[cyan]Absence terdeteksi, mengisi End Date dengan {end_date_val}...[/]")
            if not self._set_date_value(loc, end_date_val):
                console.print(f"[bold red]GAGAL - End Date tidak dapat diinput pada baris {row_num}.[/]")
                return False

        # 4b. Ensure the mandatory report date is not empty (server throws
        # ParseException: Unparseable date: "" on blank date)
        if not self._ensure_report_date(start_date_val):
            console.print(f"[bold red]GAGAL - Tanggal (activityReportDate) kosong pada baris {row_num}; baris dilewati agar tidak error di server CAS.[/]")
            return False

        # 4c. Move the cursor to another field so date inputs commit (blur/change)
        self._move_focus_away()

        self.page.wait_for_timeout(1000)

        # 5. Click Save as Draft
        console.print("[cyan]Menekan tombol 'Save as Draft'...[/]")
        save_result = self.page.evaluate("""
            () => {
                const buttons = Array.from(document.querySelectorAll('input[type="button"], input[type="submit"], button, a.ibm-btn-pri, a.ibm-btn-sec, input[value*="Draft"], input[value*="Save"]'));
                
                // Priority 1: Save as Draft
                for (let btn of buttons) {
                    const text = (btn.value || btn.innerText || btn.name || '').toLowerCase();
                    if (text.includes('draft') || text.includes('save as draft')) {
                        btn.click();
                        return { clicked: true, buttonText: (btn.value || btn.innerText || 'Save as Draft') };
                    }
                }

                // Priority 2: Generic Save / Submit
                for (let btn of buttons) {
                    const text = (btn.value || btn.innerText || btn.name || '').toLowerCase();
                    if (text.includes('save') || text.includes('simpan')) {
                        btn.click();
                        return { clicked: true, buttonText: (btn.value || btn.innerText || 'Save') };
                    }
                }

                return { clicked: false };
            }
        """)

        if save_result and save_result.get("clicked"):
            console.print(f"[bold green]Tombol [{save_result.get('buttonText')}] diklik! Menunggu respon konfirmasi server CAS...[/]")
        else:
            console.print("[yellow]Tombol Draft tidak ditemukan via JS, mencoba locator fallback...[/]")
            fallback_btn = self.page.locator("input[value*='Draft'], input[value*='Save'], button:has-text('Draft'), button:has-text('Save')").first
            if fallback_btn.count() > 0:
                fallback_btn.click()
            else:
                self.page.keyboard.press("Enter")

        # 6. EXPLICIT WAITING LOOP: Poll for server response (Success or Error banner)
        max_wait_seconds = 20
        poll_interval = 0.5
        elapsed = 0.0

        console.print("[cyan]Memverifikasi status penyimpanan ke server CAS...[/]")

        while elapsed < max_wait_seconds:
            self.page.wait_for_timeout(int(poll_interval * 1000))
            elapsed += poll_interval

            # Check for Success banner (e.g. CAS001700 - Activity has been saved as draft successfully.)
            try:
                page_text = self.page.inner_text("body")
                lower_text = page_text.lower()
                if "saved as draft successfully" in lower_text or "saved successfully" in lower_text:
                    for line in page_text.splitlines():
                        l_clean = line.strip()
                        if "saved as draft successfully" in l_clean.lower() or "saved successfully" in l_clean.lower():
                            console.print(f"[bold green]SUKSES TERVERIFIKASI: {l_clean}[/]")
                            # Jeda antar baris agar server stabil
                            self.page.wait_for_timeout(1500)
                            return True
            except Exception:
                pass

            # Check for Error banner
            try:
                errors = self.page.evaluate("""
                    () => {
                        const errElements = Array.from(document.querySelectorAll('.ibm-error, .errors, ul.errorMessage, font[color="red"], .error, span.error'));
                        return errElements.map(e => e.innerText.trim()).filter(t => t.length > 0 && !t.includes('*'));
                    }
                """)
                if errors:
                    console.print(f"[bold red]GAGAL - Server CAS menolak baris {row_num}:[/]")
                    for err in errors:
                        console.print(f"  [red]- {err}[/]")
                    return False
            except Exception:
                pass

        console.print(f"[bold yellow]Peringatan: Timeout menunggu konfirmasi respon CAS untuk baris {row_num}.[/]")
        return False

    def _move_focus_away(self):
        """Click a neutral field (description, else Project Num) so the last-edited
        date field loses focus and the page registers its value before saving."""
        console.print("[cyan]Memindahkan kursor ke field lain sebelum Save Draft...[/]")
        targets = ["#actyDesc", "input[name*='actyDesc']", "textarea[name*='actyDesc']",
                   "input[name*='projNum']", "input[name*='projectNum']"]
        for sel in targets:
            try:
                loc = self.page.locator(sel).first
                if loc.count() > 0 and loc.is_visible():
                    loc.click(timeout=2000)
                    self.page.wait_for_timeout(500)
                    return
            except Exception:
                continue
        try:
            self.page.keyboard.press("Tab")
            self.page.wait_for_timeout(500)
        except Exception:
            pass

    @staticmethod
    def _is_absence(entry: Dict[str, Any]) -> bool:
        service_type = ""
        service_detail = ""
        for key, val in entry.items():
            k = str(key).strip().lower()
            if k.endswith("servicetype"):
                service_type = str(val).strip().lower()
            elif k.endswith("servicedetl") or k.endswith("servicedetail"):
                service_detail = str(val).strip().lower()
        return service_type == "administration" and service_detail == "absence"

    def _find_end_date_locator(self, timeout_ms: int = 5000):
        """Wait for the End Date field to appear (shown via AJAX after Absence is selected)."""
        selectors = [
            "#activityReportDateEnd",
            "input[name*='activityReportDateEnd']",
            "input[name*='EndDate']",
            "input[name*='endDate']",
            "#EndDate",
        ]
        elapsed = 0
        while elapsed <= timeout_ms:
            for sel in selectors:
                loc = self.page.locator(sel).first
                if loc.count() > 0 and loc.is_visible():
                    return loc
            self.page.wait_for_timeout(500)
            elapsed += 500
        return None

    def _set_date_value(self, loc, value: str) -> bool:
        """Set a date input and verify it. Tries fill(), then JS (readonly/date-picker fields)."""
        try:
            if (loc.input_value(timeout=1000) or "").strip() == value:
                return True
        except Exception:
            pass
        try:
            loc.fill(value, timeout=2000)
        except Exception:
            pass
        try:
            if (loc.input_value(timeout=1000) or "").strip() == value:
                return True
            loc.evaluate(
                """(el, v) => {
                    el.removeAttribute('readonly');
                    el.value = v;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur', { bubbles: true }));
                }""",
                value,
            )
            return (loc.input_value(timeout=1000) or "").strip() == value
        except Exception:
            return False

    def _ensure_report_date(self, start_date_val) -> bool:
        loc = self.page.locator("#activityReportDate, input[name*='activityReportDate']:not([name*='End'])").first
        if loc.count() == 0:
            return True  # field not on this form
        try:
            if (loc.input_value(timeout=1000) or "").strip():
                return True
        except Exception:
            return False
        if not start_date_val:
            return False
        return self._set_date_value(loc, start_date_val)

    def _fill_field(self, field_name: str, val_str: str):
        fn = field_name.strip()
        selectors = [
            f"select[name='formBean.{fn}']",
            f"input[name='formBean.{fn}']",
            f"textarea[name='formBean.{fn}']",
            f"#{fn}",
            f"select[name='{fn}']",
            f"input[name='{fn}']",
            f"textarea[name='{fn}']",
            f"[name*='{fn}']"
        ]

        if "startTime" in fn:
            selectors = ["#startTime", "input[name*='actyStartTime']", "input[name*='startTime']"] + selectors
        elif "stopTime" in fn:
            selectors = ["#stopTime", "input[name*='actyStopTime']", "input[name*='stopTime']"] + selectors
        elif "desc" in fn.lower():
            selectors = ["#actyDesc", "input[name*='actyDesc']", "textarea[name*='actyDesc']"] + selectors
        elif "date" in fn.lower() and "end" not in fn.lower():
            selectors = ["#activityReportDate", "input[name*='activityReportDate']"] + selectors
        elif "end" in fn.lower():
            selectors = ["#activityReportDateEnd", "input[name*='activityReportDateEnd']"] + selectors

        for sel in selectors:
            loc = self.page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                try:
                    is_readonly = loc.evaluate("el => el.readOnly || el.disabled")
                    if is_readonly:
                        return

                    tag = loc.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "select":
                        self._select_option_with_retry(loc, val_str)
                        return
                    elif tag in ("input", "textarea"):
                        if loc.is_editable(timeout=1500):
                            loc.fill(val_str, timeout=2000)
                            return
                except Exception:
                    continue

    def _select_option_with_retry(self, locator, value_str: str, max_retries: int = 6):
        for attempt in range(max_retries):
            try:
                locator.select_option(label=value_str, timeout=1500)
                return
            except Exception:
                try:
                    locator.select_option(value=value_str, timeout=1500)
                    return
                except Exception:
                    self.page.wait_for_timeout(500)

        console.print(f"[yellow]Peringatan: Opsi '{value_str}' tidak dapat dipilih setelah beberapa percobaan.[/]")

    def process_all(self, entries: List[Dict[str, Any]]):
        console.print(f"[bold cyan]Memulai pengisian otomatis untuk {len(entries)} data baris...[/]")
        success_count = 0
        for entry in entries:
            try:
                if self.fill_and_save_draft(entry):
                    success_count += 1
            except Exception as e:
                console.print(f"[bold red]Error saat memproses baris {entry.get('_row_number')}: {e}[/]")

        console.print(f"\n[bold green]Hasil Proses: {success_count}/{len(entries)} data baris berhasil diverifikasi dan disimpan sebagai Draft di CAS![/]")
