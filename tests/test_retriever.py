import pytest
from unittest.mock import MagicMock
from src.retriever import MonthlyRetriever


def test_parse_month_query():
    from_d, to_d, tag = MonthlyRetriever.parse_month_query("oktober 2024")
    assert from_d == "2024-10-01"
    assert to_d == "2024-10-31"
    assert tag == "Oktober_2024"

    from_d, to_d, tag = MonthlyRetriever.parse_month_query("februari 2024")  # Leap year
    assert from_d == "2024-02-01"
    assert to_d == "2024-02-29"

    from_d, to_d, tag = MonthlyRetriever.parse_month_query("january")
    assert "-01-01" in from_d
    assert "-01-31" in to_d


def test_export_to_excel(tmp_path):
    records = [
        {"Acty Num": "1001", "Date": "2024-10-01", "Status": "Draft", "Desc": "Work 1"},
        {"Acty Num": "1002", "Date": "2024-10-02", "Status": "Draft", "Desc": "Work 2"}
    ]
    out_file = tmp_path / "CAS_Activities_Test.xlsx"

    retriever = MonthlyRetriever(MagicMock(), "http://example.com")
    saved_path = retriever.export_to_excel(records, str(out_file))

    assert str(out_file) == saved_path
    assert out_file.exists()
