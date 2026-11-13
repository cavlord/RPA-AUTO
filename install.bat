@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo   Hermes CAS ReportFlow - Installer
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python belum terinstall. Install Python 3.10+ dari https://www.python.org/downloads/
    echo         Centang "Add python.exe to PATH" saat instalasi, lalu jalankan installer ini lagi.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/5] Membuat virtual environment...
    python -m venv .venv || goto :fail
) else (
    echo [1/5] Virtual environment sudah ada.
)

echo [2/5] Install dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail

echo [3/5] Install browser Chromium untuk Playwright...
".venv\Scripts\python.exe" -m playwright install chromium || goto :fail

echo [4/5] Install perintah global 'rpa'...
".venv\Scripts\python.exe" install_launcher.py || goto :fail

echo [5/5] Membuat folder Documents\RPA dan file Excel...
".venv\Scripts\python.exe" main.py setup || goto :fail

echo.
echo ============================================
echo   Instalasi selesai!
echo   Buka terminal BARU lalu jalankan: rpa --help
echo ============================================
pause
exit /b 0

:fail
echo.
echo [ERROR] Instalasi gagal. Periksa pesan di atas.
pause
exit /b 1
