"""
First-run setup — create <Documents>/RPA workspace and generate required Excel files.
Called by the installer and via: rpa setup
"""
import shutil
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font
from rich.console import Console

from src.config import PROJECT_ROOT, config
from src.excel_generator import ExcelTemplateGenerator
from src import parking

console = Console()

BUNDLED_PARKING_TEMPLATE = PROJECT_ROOT / "templates" / "Template Parkir MDT.xlsx"


def create_blank_parking_template(path: Path) -> None:
    """Fallback parking template matching the slot layout used by src/parking.py."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = parking.SHEET_NAME
    bold = Font(bold=True)

    for n, (col, row) in enumerate(parking.SLOTS, start=1):
        c = ws[f"{col}{row}"].column
        title = ws.cell(row=row - 2, column=c, value=f"STRUK PARKIR #{n}")
        title.font = bold
        ws.cell(row=row, column=c - 1, value="MASUK").font = bold
        ws.cell(row=row + 1, column=c - 1, value="KELUAR").font = bold
        for r in (row, row + 1):
            cell = ws.cell(row=r, column=c)
            cell.number_format = "dd/mm/yyyy hh:mm:ss"
            cell.alignment = Alignment(horizontal="left")
        ws.column_dimensions[ws.cell(row=1, column=c).column_letter].width = 22

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(path))


def run_setup(force: bool = False) -> None:
    """Create workspace folders and generate all required Excel files."""
    home = Path(config.rpa_home)
    report_dir = Path(config.input_dir)
    parking_dir = Path(config.parking_dir)

    for d in (home, report_dir, Path(config.output_dir), parking_dir):
        d.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]Workspace folder:[/] {home}")

    # 1. CAS activity entry template
    cas_template = Path(config.excel_template_path)
    if cas_template.exists() and not force:
        console.print(f"[yellow]Skip (already exists):[/] {cas_template}")
    elif not Path(config.discovered_fields_path).exists():
        console.print(f"[red]{config.discovered_fields_path} tidak ditemukan. Jalankan 'rpa discover' lalu 'rpa template'.[/]")
    else:
        ExcelTemplateGenerator.from_json(config.discovered_fields_path).generate(str(cas_template))

    # 2. Parking template
    parking_template = Path(config.parking_template_path)
    if parking_template.exists() and not force:
        console.print(f"[yellow]Skip (already exists):[/] {parking_template}")
    elif BUNDLED_PARKING_TEMPLATE.exists():
        shutil.copyfile(BUNDLED_PARKING_TEMPLATE, parking_template)
        console.print(f"[green]Parking template copied:[/] {parking_template}")
    else:
        create_blank_parking_template(parking_template)
        console.print(f"[green]Parking template generated (basic layout):[/] {parking_template}")

    console.print(f"\n[bold green]Setup selesai.[/] Semua file ada di: {home}")
