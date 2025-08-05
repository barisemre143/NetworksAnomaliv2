
@echo off
echo ========================================
echo E-Ticaret Dashboard Başlatılıyor...
echo ========================================
echo.

cd /d %~dp0

echo 1. Python versiyonu kontrol ediliyor...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo HATA: Python bulunamadi!
    pause
    exit /b 1
)

echo.
echo 2. Virtual environment aktif ediliyor...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo Virtual environment aktif edildi.
) else (
    echo Uyari: Virtual environment bulunamadi, sistem Python kullanilacak.
)

echo.
echo 3. Web dashboard baslatiliyor...
cd web_dashboard
python app.py

pause

