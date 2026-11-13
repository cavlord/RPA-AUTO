import os
from pathlib import Path
from typing import Any, Dict
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "default_config.yaml"


def _documents_dir() -> Path:
    """Real Documents folder of the current user (handles OneDrive redirection)."""
    if os.name == "nt":
        try:
            import ctypes

            guid = ctypes.c_buffer(16)
            # FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
            ctypes.windll.ole32.CLSIDFromString("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}", guid)
            out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(guid, 0, None, ctypes.byref(out)) == 0:
                path = Path(out.value)
                ctypes.windll.ole32.CoTaskMemFree(out)
                return path
        except Exception:
            pass
    return Path.home() / "Documents"


def get_rpa_home() -> Path:
    """Per-user workspace: <Documents>/RPA (override with RPA_HOME env var)."""
    env = os.environ.get("RPA_HOME")
    return Path(env).expanduser() if env else _documents_dir() / "RPA"


RPA_HOME = get_rpa_home()


def resolve_project_path(path_str: str) -> str:
    path_str = path_str.replace("{RPA_HOME}", RPA_HOME.as_posix())
    p = Path(path_str)
    if not p.is_absolute():
        return str((PROJECT_ROOT / p).resolve())
    return str(p.resolve())


class Config:
    def __init__(self, config_dict: Dict[str, Any]):
        self._raw = config_dict
        self.project_root = PROJECT_ROOT

        self.app_name = config_dict.get("app", {}).get("name", "Hermes CAS ReportFlow")
        self.version = config_dict.get("app", {}).get("version", "1.0.0")

        urls = config_dict.get("urls", {})
        self.url_add_activity = urls.get(
            "add_activity",
            "https://cas-prd.cas.wdc.app.cirrus.ibm.com/cas/action/actvReport_addInit",
        )
        self.url_search_activity = urls.get(
            "search_activity",
            "https://cas-prd.cas.wdc.app.cirrus.ibm.com/cas/action/actvReport_preSearch",
        )

        browser = config_dict.get("browser", {})
        self.headless = browser.get("headless", False)
        self.slow_mo = browser.get("slow_mo_ms", 100)
        self.timeout = browser.get("timeout_ms", 30000)
        self.viewport = browser.get("viewport", {"width": 1280, "height": 800})
        
        raw_user_data_dir = browser.get("user_data_dir", ".browser_session")
        self.user_data_dir = resolve_project_path(raw_user_data_dir)

        paths = config_dict.get("paths", {})
        self.artifacts_dir = resolve_project_path(paths.get("artifacts_dir", "artifacts"))
        self.discovered_fields_path = resolve_project_path(
            paths.get("discovered_fields", "artifacts/discovered_fields.json")
        )
        self.rpa_home = str(RPA_HOME)
        self.input_dir = resolve_project_path(
            paths.get("input_dir", "{RPA_HOME}/REPORT")
        )
        self.output_dir = resolve_project_path(
            paths.get("output_dir", "{RPA_HOME}/REPORT")
        )
        self.excel_template_path = resolve_project_path(
            paths.get("excel_template", "{RPA_HOME}/REPORT/CAS_Activity_Entry_Template.xlsx")
        )
        self.parking_dir = resolve_project_path(
            paths.get("parking_dir", "{RPA_HOME}/PARKING")
        )
        self.parking_template_path = resolve_project_path(
            paths.get("parking_template", "{RPA_HOME}/PARKING/Template Parkir MDT.xlsx")
        )

    @classmethod
    def load(cls, config_path: str = None) -> "Config":
        path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
        return cls(data)


config = Config.load()
