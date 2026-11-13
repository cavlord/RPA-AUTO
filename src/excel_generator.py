import json
import os
from pathlib import Path
from typing import Any, Dict, List
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from rich.console import Console

console = Console()


class ExcelTemplateGenerator:
    def __init__(self, metadata: Dict[str, Any]):
        self.metadata = metadata
        raw_fields = metadata.get("fields", [])
        # Filter out hidden fields
        self.fields = [
            f for f in raw_fields
            if f.get("field_type") != "hidden" and f.get("type") != "hidden"
        ]

    @classmethod
    def from_json(cls, json_path: str = "artifacts/discovered_fields.json") -> "ExcelTemplateGenerator":
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)

    def generate(self, output_path: str) -> str:
        console.print(f"[cyan]Generating Excel Template at:[/] {output_path}")
        wb = openpyxl.Workbook()

        # Data Sheet
        ws = wb.active
        ws.title = "Activity_Reports"

        # Reference / Options Sheet for long dropdowns
        ws_ref = wb.create_sheet(title="Lookup_Data")
        ws_ref.sheet_state = "hidden"

        # Styling
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        req_font = Font(name="Segoe UI", size=10, bold=True, color="FFC000")
        meta_font = Font(name="Segoe UI", size=9, italic=True, color="595959")
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )

        ref_col_idx = 1

        for col_idx, field in enumerate(self.fields, start=1):
            col_letter = openpyxl.utils.get_column_letter(col_idx)
            name = field.get("name", "")
            field_id = field.get("field_id", name)
            label = field.get("label", name) or name

            # Row 1: Technical ID
            cell_r1 = ws.cell(row=1, column=col_idx, value=field_id or name)
            cell_r1.font = meta_font
            cell_r1.alignment = Alignment(horizontal="center", vertical="center")

            # Row 2: Human-readable Label / Header
            cell_r2 = ws.cell(row=2, column=col_idx, value=label)
            cell_r2.fill = header_fill
            cell_r2.font = req_font if field.get("required") else header_font
            cell_r2.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            # Row 3: Hint / Constraints
            hints = []
            if field.get("required"):
                hints.append("REQUIRED")
            
            # Formats & Hints
            lower_name = (name + " " + field_id).lower()
            if "time" in lower_name:
                hints.append("Format: HH:MM (e.g. 09:00)")
            elif "date" in lower_name:
                hints.append("Format: YYYY-MM-DD")
            elif field.get("max_length"):
                hints.append(f"Max {field['max_length']} chars")
            
            hint_text = " | ".join(hints) if hints else "Optional"
            cell_r3 = ws.cell(row=3, column=col_idx, value=hint_text)
            cell_r3.font = meta_font
            cell_r3.alignment = Alignment(horizontal="center", vertical="center")

            # Column width auto-adjust
            max_len = max(len(str(label)), len(str(name)), 16)
            ws.column_dimensions[col_letter].width = min(max_len + 4, 38)

            # Dropdown validations
            options = field.get("options", [])
            if options:
                ref_letter = openpyxl.utils.get_column_letter(ref_col_idx)
                for opt_row_idx, opt in enumerate(options, start=1):
                    opt_val = opt.get("label") or opt.get("text") or opt.get("value", "")
                    ws_ref.cell(row=opt_row_idx, column=ref_col_idx, value=opt_val)

                dv = DataValidation(
                    type="list",
                    formula1=f"='Lookup_Data'!${ref_letter}$1:${ref_letter}${len(options)}",
                    allow_blank=True
                )
                dv.error = "Please select a valid option from the dropdown list."
                dv.errorTitle = "Invalid Option"
                ws.add_data_validation(dv)
                dv.add(f"{col_letter}4:{col_letter}200")
                ref_col_idx += 1

            # Only add textLength validation for long free-text descriptions (e.g. actyDesc)
            is_time_or_date = "time" in lower_name or "date" in lower_name
            if field.get("max_length") and field.get("max_length") > 10 and not is_time_or_date:
                dv_len = DataValidation(
                    type="textLength",
                    operator="lessThanOrEqual",
                    formula1=str(field["max_length"]),
                    allow_blank=True
                )
                dv_len.error = f"Input exceeds maximum allowed length of {field['max_length']} characters."
                dv_len.errorTitle = "Character Limit Exceeded"
                ws.add_data_validation(dv_len)
                dv_len.add(f"{col_letter}4:{col_letter}200")

        # Freeze Header Rows
        ws.freeze_panes = "A4"

        # Apply borders to entry grid (uses standard General format so formulas work!)
        for r in range(4, 50):
            for c in range(1, len(self.fields) + 1):
                cell = ws.cell(row=r, column=c)
                cell.border = thin_border

        out_path = Path(output_path)
        os.makedirs(out_path.parent, exist_ok=True)
        wb.save(str(out_path))
        console.print(f"[bold green]Excel entry template generated successfully at:[/] {output_path}")
        return str(out_path)
