import os
import random
import sys
from pathlib import Path
import click
from rich.console import Console

from src.browser import BrowserController
from src.config import config
from src.discovery import FormDiscovery
from src.excel_generator import ExcelTemplateGenerator
from src.excel_reader import ExcelReader
from src.form_filler import FormFiller
from src.retriever import MonthlyRetriever
from src import parking as _parking

console = Console()


@click.group()
def cli():
    """Hermes CAS ReportFlow CLI"""
    pass


@cli.command()
@click.option("--url", default=None, help="Add Activity Form URL")
@click.option("--output", default=None, help="Output metadata JSON path")
@click.option("--auto-close", is_flag=True, default=False, help="Close browser automatically")
def discover(url, output, auto_close):
    """Discover fields from CAS Add Activity page and save schema."""
    target_url = url or config.url_add_activity
    out_file = output or config.discovered_fields_path

    browser = BrowserController(
        user_data_dir=config.user_data_dir,
        headless=config.headless,
        slow_mo=config.slow_mo
    )
    try:
        page = browser.navigate_and_wait_for_auth(target_url)
        engine = FormDiscovery(page)
        metadata = engine.discover()
        engine.save_metadata(metadata, out_file)
        if not auto_close:
            input("\n>>> Proses selesai. Tekan [ENTER] di sini untuk menutup browser... <<<\n")
    finally:
        browser.close()


@cli.command()
@click.option("--input", "input_json", default=None, help="Discovered fields JSON")
@click.option("--output", default=None, help="Excel template destination path")
def template(input_json, output):
    """Generate Excel entry template with dropdowns & validations."""
    meta_path = input_json or config.discovered_fields_path
    dest_path = output or config.excel_template_path

    if not Path(meta_path).exists():
        console.print(f"[bold red]Metadata field belum ditemukan di {meta_path}. Jalankan 'rpa discover' terlebih dahulu.[/]")
        sys.exit(1)

    gen = ExcelTemplateGenerator.from_json(meta_path)
    gen.generate(dest_path)


@cli.command()
@click.option("--excel", default=None, help="Path to filled Excel file")
@click.option("--auto-close", is_flag=True, default=False, help="Close browser automatically")
def fill(excel, auto_close):
    """Read filled Excel rows and submit each record to CAS as Draft."""
    excel_file = excel or config.excel_template_path
    if not Path(excel_file).exists():
        console.print(f"[bold red]File input Excel tidak ditemukan di: {excel_file}[/]")
        sys.exit(1)

    reader = ExcelReader(excel_file)
    entries = reader.read_entries()

    if not entries:
        console.print("[yellow]Tidak ada baris data pada sheet Excel. Silakan isi data mulai dari baris 4.[/]")
        return

    browser = BrowserController(
        user_data_dir=config.user_data_dir,
        headless=config.headless,
        slow_mo=config.slow_mo
    )
    try:
        page = browser.navigate_and_wait_for_auth(config.url_add_activity)
        filler = FormFiller(page, config.url_add_activity)
        filler.process_all(entries)

        if not auto_close:
            input("\n>>> Proses pengisian selesai! Browser tetap terbuka agar Anda bisa memeriksa halaman. Tekan [ENTER] di terminal untuk menutup browser... <<<\n")
    finally:
        browser.close()


@cli.command()
@click.argument("month_query", required=False, default=None)
@click.option("--output", default=None, help="Custom export path for Excel")
@click.option("--auto-close", is_flag=True, default=False, help="Close browser automatically")
def retrieve(month_query, output, auto_close):
    """Retrieve activities for a specified month (e.g. 'oktober', 'january 2024') and export to Excel."""
    if not month_query or not month_query.strip():
        console.print("\n[bold cyan]=== PENCARIAN & EKSPOR LAPORAN AKTIVITAS BULANAN ===[/]")
        month_query = input(">> Masukkan bulan yang ingin di-retrieve (contoh: 'oktober', '10', 'oktober 2024') [Tekan Enter untuk bulan ini]: ").strip()
        if not month_query:
            month_query = None

    from_date, to_date, file_tag = MonthlyRetriever.parse_month_query(month_query)
    out_dir = Path(config.output_dir)
    dest_path = output or str(out_dir / f"CAS_Activities_{file_tag}.xlsx")

    browser = BrowserController(
        user_data_dir=config.user_data_dir,
        headless=config.headless,
        slow_mo=config.slow_mo
    )
    try:
        page = browser.navigate_and_wait_for_auth(config.url_search_activity)
        retriever = MonthlyRetriever(page, config.url_search_activity)
        records = retriever.search_by_date_range(from_date, to_date)
        retriever.export_to_excel(records, dest_path)

        if not auto_close:
            input("\n>>> Proses retrieve selesai! File Excel tersimpan. Tekan [ENTER] di sini untuk menutup browser... <<<\n")
    finally:
        browser.close()


@cli.command()
@click.option("--cas", default=None, help="Path file CAS Activities (.xlsx)")
@click.option("--out", default=None, help="Path file output parkir (.xlsx)")
@click.option("--skip", default="", help="Rentang tanggal dibuang, mis. 5-10")
@click.option("--seed", type=int, default=None, help="Seed acak agar hasil bisa diulang")
def parking(cas, out, skip, seed):
    """Generate Template Parkir MDT dari file CAS Activities secara interaktif."""
    REPORT_DIR  = config.input_dir
    PARKING_DIR = config.parking_dir
    TEMPLATE    = config.parking_template_path

    # ── Pilih file CAS ────────────────────────────────────────────────────────
    if cas:
        cas_path = cas
    else:
        files = sorted(
            f for f in os.listdir(REPORT_DIR)
            if f.lower().endswith(".xlsx")
        )
        if not files:
            console.print(f"[bold red]Tidak ada file .xlsx di: {REPORT_DIR}[/]")
            sys.exit(1)

        console.print(f"\n[bold cyan]File CAS yang tersedia di {REPORT_DIR}:[/]")
        for i, name in enumerate(files, 1):
            console.print(f"  [[bold]{i}[/]] {name}")

        while True:
            raw = input("\nPilih nomor file: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(files):
                cas_path = os.path.join(REPORT_DIR, files[int(raw) - 1])
                break
            console.print("  [yellow]Input tidak valid, coba lagi.[/]")

    console.print(f"  File: [green]{os.path.basename(cas_path)}[/]")

    # ── Skip ──────────────────────────────────────────────────────────────────
    if not skip:
        raw_skip = input("\nSkip tanggal? (mis. 5-10, kosongkan jika tidak): ").strip()
        skip = raw_skip

    skip_range = None
    if skip:
        parts = skip.split("-")
        if len(parts) == 2 and all(p.isdigit() for p in parts):
            skip_range = (int(parts[0]), int(parts[1]))
        else:
            console.print("  [yellow]Format skip tidak dikenali, diabaikan.[/]")

    # ── Seed ──────────────────────────────────────────────────────────────────
    if seed is None:
        raw_seed = input("\nSeed acak (kosongkan untuk acak murni): ").strip()
        if raw_seed.isdigit():
            seed = int(raw_seed)

    if seed is not None:
        random.seed(seed)

    # ── Nama output ───────────────────────────────────────────────────────────
    if not out:
        default_out = _parking.default_output_name(cas_path, PARKING_DIR)
        raw_out = input(f"\nNama file output [{os.path.basename(default_out)}]: ").strip()
        out = os.path.join(PARKING_DIR, raw_out) if raw_out else default_out

    # ── Proses ────────────────────────────────────────────────────────────────
    console.print("\n[bold]Memproses...[/]")
    rows    = _parking.read_cas(cas_path)
    entries = _parking.build_entries(rows)

    if skip_range:
        lo, hi  = skip_range
        entries = [(m, k) for m, k in entries if not lo <= m.day <= hi]

    entries = _parking.apply_jitter(entries)

    if not entries:
        console.print("[bold red]Tidak ada data yang diproses. Periksa file CAS.[/]")
        sys.exit(1)

    n_slots = len(_parking.SLOTS)
    if len(entries) > n_slots:
        console.print(
            f"[yellow][PERINGATAN] {len(entries)} entri ditemukan, "
            f"template hanya punya {n_slots} slot. "
            f"{len(entries) - n_slots} entri terakhir tidak masuk.[/]"
        )

    if not os.path.isfile(TEMPLATE):
        console.print(f"[bold red]Template tidak ditemukan: {TEMPLATE}[/]")
        sys.exit(1)

    _parking.write_template(TEMPLATE, entries, out)

    # ── Laporan ───────────────────────────────────────────────────────────────
    n = min(len(entries), n_slots)
    console.print(f"\n[bold green]Selesai! {n} struk -> {out}[/]")
    console.print("-" * 54)
    for masuk, keluar in entries[:n]:
        console.print(f"  {masuk:%d/%m %H:%M:%S}  ->  {keluar:%d/%m %H:%M:%S}")
    console.print("-" * 54)


@cli.command()
@click.option("--force", is_flag=True, default=False, help="Overwrite existing Excel files")
def setup(force):
    """Create <Documents>/RPA folders and generate all required Excel files."""
    from src.setup import run_setup
    run_setup(force=force)


def main():
    cli()


if __name__ == "__main__":
    main()
