from unittest.mock import MagicMock
from src.form_filler import FormFiller


def test_form_filler_fill_and_save():
    mock_page = MagicMock()
    mock_locator = MagicMock()
    mock_locator.count.return_value = 1
    mock_locator.first = mock_locator
    mock_locator.is_visible.return_value = True
    mock_locator.get_attribute.return_value = "Save as Draft"
    mock_locator.evaluate.return_value = "input"

    mock_page.locator.return_value = mock_locator
    mock_page.inner_text.return_value = "CAS001700 - Activity has been saved as draft successfully."
    mock_page.evaluate.return_value = {"clicked": True, "buttonText": "Save as Draft"}

    filler = FormFiller(mock_page, "http://example.com/add")
    entry = {
        "formBean.actyDesc": "A" * 80,  # Should be truncated to 70
        "formBean.serviceType": "Administration",
        "_row_number": 4
    }

    result = filler.fill_and_save_draft(entry)
    assert result is True
    mock_page.goto.assert_called_with("http://example.com/add", wait_until="domcontentloaded", timeout=60000)
