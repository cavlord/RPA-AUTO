import openpyxl
from src.excel_reader import ExcelReader


def test_excel_reader(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Activity_Reports"

    # Row 1: Technical ID / name
    ws.cell(row=1, column=1, value="formBean.serviceType")
    ws.cell(row=1, column=2, value="formBean.actyDesc")

    # Row 2: Header
    ws.cell(row=2, column=1, value="Service Type")
    ws.cell(row=2, column=2, value="Description")

    # Row 3: Hints
    ws.cell(row=3, column=1, value="REQUIRED")
    ws.cell(row=3, column=2, value="Max 70 chars")

    # Row 4: Data Row 1
    ws.cell(row=4, column=1, value="Administration")
    ws.cell(row=4, column=2, value="Cuti Tahunan")

    # Row 5: Data Row 2
    ws.cell(row=5, column=1, value="Administration")
    ws.cell(row=5, column=2, value="Sakit")

    file_path = tmp_path / "test_input.xlsx"
    wb.save(str(file_path))

    reader = ExcelReader(str(file_path))
    entries = reader.read_entries()

    assert len(entries) == 2
    assert entries[0]["formBean.serviceType"] == "Administration"
    assert entries[0]["formBean.actyDesc"] == "Cuti Tahunan"
    assert entries[0]["_row_number"] == 4
    assert entries[1]["_row_number"] == 5
