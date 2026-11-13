import json
from unittest.mock import MagicMock
from src.discovery import FormDiscovery


def test_form_discovery_mock(tmp_path):
    mock_page = MagicMock()
    mock_page.evaluate.return_value = {
        "url": "http://example.com",
        "title": "Add Activity",
        "fields": [
            {
                "name": "formBean.serviceType",
                "label": "Service Type",
                "tag": "select",
                "type": "select",
                "required": True,
                "options": [{"value": "Administration", "text": "Administration"}]
            }
        ]
    }

    discovery = FormDiscovery(mock_page)
    meta = discovery.discover()
    assert len(meta["fields"]) == 1
    assert meta["fields"][0]["name"] == "formBean.serviceType"

    out_file = tmp_path / "discovered.json"
    discovery.save_metadata(meta, str(out_file))
    assert out_file.exists()

    with open(out_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["fields"][0]["label"] == "Service Type"
