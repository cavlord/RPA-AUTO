import openpyxl
from src.excel_generator import ExcelTemplateGenerator


def test_excel_generator(tmp_path):
    metadata = {
        "fields": [
            {
                "field_id": "serviceType",
                "name": "formBean.serviceType",
                "label": "Service Type",
                "required": True,
                "options": [{"value": "1", "label": "Administration"}, {"value": "2", "label": "Project"}]
            },
            {
                "field_id": "actyDesc",
                "name": "formBean.actyDesc",
                "label": "Activity Description",
                "required": True,
                "max_length": 70,
                "options": []
            },
            {
                "field_id": "startTime",
                "name": "formBean.actyStartTime",
                "label": "Start Time",
                "max_length": 5,
                "options": []
            }
        ]
    }

    out_file = tmp_path / "test_template.xlsx"
    gen = ExcelTemplateGenerator(metadata)
    result_path = gen.generate(str(out_file))

    assert str(out_file) == result_path
    assert out_file.exists()

    wb = openpyxl.load_workbook(str(out_file))
    assert "Activity_Reports" in wb.sheetnames
    assert "Lookup_Data" in wb.sheetnames

    ws = wb["Activity_Reports"]
    # Row 1 is tech ID
    assert ws.cell(row=1, column=1).value == "serviceType"
    # Row 2 is Label
    assert ws.cell(row=2, column=1).value == "Service Type"
    assert ws.cell(row=1, column=2).value == "actyDesc"
    assert ws.cell(row=2, column=2).value == "Activity Description"
