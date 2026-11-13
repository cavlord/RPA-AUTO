import os
from datetime import datetime, date, time
from pathlib import Path
from typing import Any, Dict, List
import openpyxl
from rich.console import Console

console = Console()


class ExcelReader:
    def __init__(self, excel_path: str):
        self.excel_path = Path(excel_path)
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel file not found at: {excel_path}")

    def read_entries(self) -> List[Dict[str, Any]]:
        wb = openpyxl.load_workbook(str(self.excel_path), data_only=True)
        ws = wb.active

        # Map column index to field technical name
        # Row 1 is technical name / field_id; if empty, fallback to Row 2
        field_names = {}
        for col_idx in range(1, ws.max_column + 1):
            r1_val = ws.cell(row=1, column=col_idx).value
            r2_val = ws.cell(row=2, column=col_idx).value
            name = str(r1_val or r2_val or "").strip()
            if name:
                field_names[col_idx] = name

        entries = []
        # Data rows start from row 4
        for row_idx in range(4, ws.max_row + 1):
            row_data = {}
            has_data = False

            for col_idx, field_name in field_names.items():
                val = ws.cell(row=row_idx, column=col_idx).value
                if val is not None:
                    # Format time/date values properly
                    if isinstance(val, time):
                        val = val.strftime("%H:%M")
                    elif isinstance(val, datetime):
                        if val.hour != 0 or val.minute != 0:
                            val = val.strftime("%H:%M")
                        else:
                            val = val.strftime("%Y-%m-%d")
                    elif isinstance(val, date):
                        val = val.strftime("%Y-%m-%d")
                    else:
                        val = str(val).strip()

                    if val != "":
                        has_data = True
                        row_data[field_name] = val

            if has_data:
                row_data["_row_number"] = row_idx
                entries.append(row_data)

        console.print(f"[green]Successfully loaded {len(entries)} valid data rows from Excel.[/]")
        return entries
