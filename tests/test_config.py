from src.config import Config


def test_config_load_defaults():
    cfg = Config({})
    assert cfg.app_name == "Hermes CAS ReportFlow"
    assert cfg.headless is False
    assert "actvReport_addInit" in cfg.url_add_activity


def test_config_custom_values():
    custom = {
        "app": {"name": "TestApp"},
        "browser": {"headless": True, "slow_mo_ms": 200},
        "urls": {"add_activity": "http://example.com/add"}
    }
    cfg = Config(custom)
    assert cfg.app_name == "TestApp"
    assert cfg.headless is True
    assert cfg.slow_mo == 200
    assert cfg.url_add_activity == "http://example.com/add"
