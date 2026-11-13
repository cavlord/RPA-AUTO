import os
from pathlib import Path

from rich.console import Console

console = Console()

WORKSPACE_DIR = Path(__file__).resolve().parent
BIN_DIR = Path.home() / "bin"
PYTHON_EXE = WORKSPACE_DIR / ".venv" / "Scripts" / "python.exe"

CMD_SCRIPT_CONTENT = f"""@echo off
setlocal
set "VENV_PYTHON={PYTHON_EXE}"
if not exist "%VENV_PYTHON%" (
    python "{WORKSPACE_DIR}\\main.py" %*
) else (
    "%VENV_PYTHON%" "{WORKSPACE_DIR}\\main.py" %*
)
"""

PS1_SCRIPT_CONTENT = f"""$venvPython = "{PYTHON_EXE}"
if (Test-Path $venvPython) {{
    & $venvPython "{WORKSPACE_DIR}\\main.py" @args
}} else {{
    python "{WORKSPACE_DIR}\\main.py" @args
}}
"""


def add_to_user_path(directory: Path) -> None:
    """Persistently add directory to the user PATH (Windows only)."""
    if os.name != "nt":
        return
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        try:
            current, kind = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current, kind = "", winreg.REG_EXPAND_SZ
        entries = [p for p in current.split(";") if p]
        if str(directory).lower() in (e.lower() for e in entries):
            return
        entries.append(str(directory))
        winreg.SetValueEx(key, "Path", 0, kind, ";".join(entries))
    console.print(f"[green]Added to user PATH:[/] {directory} (buka terminal baru agar aktif)")


def install():
    BIN_DIR.mkdir(parents=True, exist_ok=True)

    for name in ["rpa.cmd", "RPA.cmd"]:
        cmd_path = BIN_DIR / name
        with open(cmd_path, "w", encoding="utf-8") as f:
            f.write(CMD_SCRIPT_CONTENT)
        console.print(f"[green]Installed launcher:[/] {cmd_path}")

    for name in ["rpa.ps1", "RPA.ps1"]:
        ps1_path = BIN_DIR / name
        with open(ps1_path, "w", encoding="utf-8") as f:
            f.write(PS1_SCRIPT_CONTENT)
        console.print(f"[green]Installed launcher:[/] {ps1_path}")

    add_to_user_path(BIN_DIR)
    console.print(f"[bold green]Global 'rpa' launcher successfully installed in {BIN_DIR}![/]")


if __name__ == "__main__":
    install()
