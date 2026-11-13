import calendar
from datetime import datetime
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from playwright.sync_api import Page
from rich.console import Console

console = Console()

INDONESIAN_MONTHS = {
    "januari": 1, "january": 1, "jan": 1,
    "februari": 2, "february": 2, "feb": 2,
    "maret": 3, "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5, "may": 5,
    "juni": 6, "june": 6, "jun": 6,
    "juli": 7, "july": 7, "jul": 7,
    "agustus": 8, "august": 8, "aug": 8, "agt": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "october": 10, "okt": 10, "oct": 10,
    "november": 11, "nov": 11,
    "desember": 12, "december": 12, "des": 12, "dec": 12
}


class MonthlyRetriever:
    def __init__(self, page: Page, search_url: str):
        self.page = page
        self.search_url = search_url

    @staticmethod
    def parse_month_query(query: str = None) -> Tuple[str, str, str]:
        now = datetime.now()
        current_year = now.year

        if not query or not query.strip():
            month_num = now.month
            year = current_year
            month_name = [k for k, v in INDONESIAN_MONTHS.items() if v == month_num and len(k) > 3][0]
        else:
            cleaned = query.strip()
            parts = cleaned.lower().split()
            if len(parts) == 2 and "-" in parts[0] and "-" in parts[1]:
                return parts[0], parts[1], f"Range_{parts[0]}_to_{parts[1]}"

            month_name = None
            year = None

            for part in parts:
                if part.isdigit() and len(part) == 4:
                    year = int(part)
                elif part.isdigit() and 1 <= int(part) <= 12:
                    month_num = int(part)
                    month_name = [k for k, v in INDONESIAN_MONTHS.items() if v == month_num and len(k) > 3][0]
                elif part in INDONESIAN_MONTHS:
                    month_name = part

            if not month_name:
                for k in INDONESIAN_MONTHS.keys():
                    if k in cleaned.lower():
                        month_name = k
                        break

            if not month_name:
                raise ValueError(f"Bulan tidak dapat dikenali dari input: '{query}'")

            month_num = INDONESIAN_MONTHS[month_name]
            if year is None:
                year = current_year

        last_day = calendar.monthrange(year, month_num)[1]
        from_date = f"{year}-{month_num:02d}-01"
        to_date = f"{year}-{month_num:02d}-{last_day:02d}"
        display_month = month_name.capitalize()

        return from_date, to_date, f"{display_month}_{year}"

    def search_by_date_range(self, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        console.print(f"[bold cyan]Membuka halaman pencarian:[/] {self.search_url}")
        self.page.goto(self.search_url, wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(2000)

        console.print(f"[cyan]Target Filter Tanggal:[/] Report Date From = [bold yellow]{from_date}[/], Report Date To = [bold yellow]{to_date}[/]")

        # 1. Identify all text inputs in the CAS search form
        found_elements = self.page.evaluate("""
            () => {
                const inputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type])')).filter(el => {
                    return !el.closest('#ibm-masthead, #ibm-search-form, header, footer') && el.id !== 'q' && el.name !== 'qt';
                });

                let fromSelector = null;
                let toSelector = null;

                // Priority A: Inputs with labels or table cells containing 'date from' / 'date to'
                for (let inp of inputs) {
                    let labelText = '';
                    if (inp.id) {
                        const lbl = document.querySelector(`label[for="${inp.id}"]`);
                        if (lbl) labelText = lbl.innerText;
                    }
                    if (!labelText) {
                        const td = inp.closest('td');
                        if (td && td.previousElementSibling) labelText = td.previousElementSibling.innerText;
                        if (!labelText && td) labelText = td.innerText;
                    }
                    labelText = (labelText || '').toLowerCase();
                    const name = (inp.name || '').toLowerCase();
                    const id = (inp.id || '').toLowerCase();

                    if ((labelText.includes('date from') || labelText.includes('from') || name.includes('datefrom') || name.includes('from') || id.includes('from')) && !fromSelector) {
                        inp.id = inp.id || '__cas_date_from_input';
                        fromSelector = '#' + inp.id;
                    }
                    if ((labelText.includes('date to') || labelText.includes('to') || name.includes('dateto') || name.includes('to') || id.includes('to')) && !toSelector) {
                        inp.id = inp.id || '__cas_date_to_input';
                        toSelector = '#' + inp.id;
                    }
                }

                // Priority B: Inputs with adjacent calendar links [1]
                if (!fromSelector || !toSelector) {
                    const calLinks = Array.from(document.querySelectorAll('a')).filter(a => {
                        const h = (a.href || '').toLowerCase();
                        return h.includes('cal') || h.includes('date') || h.includes('showcalendar');
                    });
                    if (calLinks.length >= 2) {
                        const inp1 = calLinks[0].closest('td, div').querySelector('input');
                        const inp2 = calLinks[1].closest('td, div').querySelector('input');
                        if (inp1 && inp2) {
                            inp1.id = inp1.id || '__cas_date_from_input';
                            inp2.id = inp2.id || '__cas_date_to_input';
                            fromSelector = '#' + inp1.id;
                            toSelector = '#' + inp2.id;
                        }
                    }
                }

                // Priority C: Sequential inputs in the form
                if (!fromSelector || !toSelector) {
                    if (inputs.length >= 2) {
                        inputs[0].id = inputs[0].id || '__cas_date_from_input';
                        inputs[1].id = inputs[1].id || '__cas_date_to_input';
                        fromSelector = '#' + inputs[0].id;
                        toSelector = '#' + inputs[1].id;
                    }
                }

                return {
                    fromSelector: fromSelector,
                    toSelector: toSelector,
                    totalInputs: inputs.length,
                    inputNames: inputs.map(i => i.name || i.id)
                };
            }
        """)

        from_sel = found_elements.get("fromSelector")
        to_sel = found_elements.get("toSelector")

        if not from_sel or not to_sel:
            console.print(f"[bold red]Gagal menemukan kotak input tanggal pada form CAS.[/]")
            console.print(f"[yellow]Input yang ditemukan di halaman: {found_elements.get('inputNames')}[/]")
            return []

        # 2. Fill inputs and verify in DOM
        from_input = self.page.locator(from_sel).first
        to_input = self.page.locator(to_sel).first

        from_input.click()
        from_input.fill(from_date)
        from_input.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")

        to_input.click()
        to_input.fill(to_date)
        to_input.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")

        # Move focus/cursor away from the date fields before pressing Search,
        # so the Report Date To value is committed by the page.
        to_input.blur()
        self.page.mouse.move(5, 300)
        self.page.wait_for_timeout(1000)

        actual_from = from_input.input_value()
        actual_to = to_input.input_value()
        console.print(f"[bold green]Verifikasi Pengisian Form:[/] Report Date From = '{actual_from}' | Report Date To = '{actual_to}'")

        if actual_from != from_date or actual_to != to_date:
            console.print(f"[bold red]Nilai input tidak sesuai dengan target! Membatalkan pencarian.[/]")
            return []

        # 3. Click Search Button
        console.print("[cyan]Mencari dan menekan tombol [ Search ]...[/]")
        search_clicked = self.page.evaluate("""
            () => {
                const buttons = Array.from(document.querySelectorAll('input[type="submit"], input[type="button"], button, a.ibm-btn-pri, input[value*="Search"]'));
                for (let b of buttons) {
                    const text = (b.value || b.innerText || b.name || '').toLowerCase();
                    if (text.includes('search') || text.includes('cari')) {
                        b.click();
                        return { clicked: true, text: text };
                    }
                }
                return { clicked: false };
            }
        """)

        if search_clicked and search_clicked.get("clicked"):
            console.print(f"[bold green]Tombol [{search_clicked.get('text')}] berhasil diklik![/]")
        else:
            fallback_btn = self.page.locator("input[value*='Search'], button:has-text('Search'), input[type='submit']").first
            if fallback_btn.count() > 0:
                fallback_btn.click()
            else:
                self.page.keyboard.press("Enter")

        # 4. Wait for server to process and return search results
        console.print("[cyan]Menunggu tabel hasil pencarian dari server CAS...[/]")
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=25000)
        except Exception:
            pass
        self.page.wait_for_timeout(4000)

        # 5. Extract results table specifically
        return self._extract_results_table()

    def _extract_results_table(self) -> List[Dict[str, Any]]:
        console.print("[cyan]Mengekstrak tabel data aktivitas...[/]")
        
        for attempt in range(3):
            try:
                records = self.page.evaluate("""
                    () => {
                        const results = [];
                        
                        // Find all tables, excluding header/masthead and search filter input form
                        const allTables = Array.from(document.querySelectorAll('table')).filter(t => {
                            if (t.closest('#ibm-masthead, #ibm-universal-nav, header, footer')) return false;
                            
                            // Check if this table is the search input form (contains date inputs, select dropdowns, search buttons)
                            const isSearchForm = t.querySelector('input[name*="DateFrom"], input[name*="DateTo"], input[value*="Search"], select[name*="actyStatus"]');
                            if (isSearchForm) return false;

                            const trs = t.querySelectorAll('tr');
                            return trs.length >= 2;
                        });

                        if (allTables.length === 0) {
                            return results;
                        }

                        // Pick the table with the most rows or largest result set
                        allTables.sort((a, b) => b.querySelectorAll('tr').length - a.querySelectorAll('tr').length);
                        const targetTable = allTables[0];

                        const rows = Array.from(targetTable.querySelectorAll('tr'));
                        if (rows.length < 2) return results;

                        // Extract Headers
                        let headerRow = rows[0];
                        let headers = Array.from(headerRow.querySelectorAll('th, td')).map(c => c.innerText.trim());

                        // If first row has no text or is title, check row 2
                        if (headers.filter(h => h.length > 0).length === 0 && rows.length > 2) {
                            headerRow = rows[1];
                            headers = Array.from(headerRow.querySelectorAll('th, td')).map(c => c.innerText.trim());
                        }

                        for (let i = 1; i < rows.length; i++) {
                            const cells = Array.from(rows[i].querySelectorAll('td'));
                            if (cells.length === 0) continue;

                            // Skip repeated header row, pagination row, or total rows
                            const rowText = cells.map(c => c.innerText.trim()).join(' ');
                            if (!rowText || rowText.includes('Total') || rowText === headers.join(' ') || rowText.includes('Page 1 of')) continue;

                            const rowObj = {};
                            cells.forEach((cell, idx) => {
                                const h = headers[idx] || `Kolom_${idx + 1}`;
                                rowObj[h] = cell.innerText.trim();
                            });
                            results.push(rowObj);
                        }

                        return results;
                    }
                """)
                if records:
                    console.print(f"[bold green]Berhasil mengekstrak {len(records)} baris data aktivitas hasil pencarian CAS![/]")
                    return records
                else:
                    self.page.wait_for_timeout(1500)
            except Exception:
                self.page.wait_for_timeout(1500)

        console.print("[yellow]Tidak ada baris data aktivitas yang ditemukan di tabel hasil pencarian.[/]")
        return []

    def export_to_excel(self, records: List[Dict[str, Any]], output_path: str) -> str:
        console.print(f"[cyan]Menyimpan {len(records)} data ke file Excel:[/] {output_path}")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "CAS_Activities"

        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        data_font = Font(name="Segoe UI", size=10)
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )

        if not records:
            ws.cell(row=1, column=1, value="Tidak ada data aktivitas yang ditemukan untuk periode tersebut.")
        else:
            headers = list(records[0].keys())
            for col_idx, h in enumerate(headers, start=1):
                cell = ws.cell(row=1, column=col_idx, value=h)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for row_idx, rec in enumerate(records, start=2):
                for col_idx, h in enumerate(headers, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=rec.get(h, ""))
                    cell.font = data_font
                    cell.border = thin_border

            for col_idx in range(1, len(headers) + 1):
                col_letter = openpyxl.utils.get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = 22

        out_path = Path(output_path)
        os.makedirs(out_path.parent, exist_ok=True)

        # Handle PermissionError if file is open in Excel
        try:
            wb.save(str(out_path))
            console.print(f"[bold green]Ekspor selesai! File berhasil disimpan di:[/] {out_path}")
            return str(out_path)
        except PermissionError:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alt_path = out_path.parent / f"{out_path.stem}_{timestamp}{out_path.suffix}"
            wb.save(str(alt_path))
            console.print(f"[bold yellow]Peringatan: File '{out_path.name}' sedang terbuka di Excel.[/]")
            console.print(f"[bold green]Berhasil disimpan ke file baru:[/] {alt_path}")
            return str(alt_path)
