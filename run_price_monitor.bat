@echo off
echo ===================================
echo Networks Tedarik Fiyat Takip Sistemi
echo ===================================

REM Python yolu kontrol et
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo HATA: Python bulunamadi! Python yukleyin.
    pause
    exit /b 1
)

REM Gerekli kutuphaneleri yukle
echo Gerekli kutuphaneler kontrol ediliyor...
pip install requests beautifulsoup4 pandas schedule >nul 2>&1

REM Calisma dizinine git
cd /d "%~dp0"

echo.
echo Secenekler:
echo 1. Tek seferlik calistir
echo 2. Zamanlanmis calistir (gunluk)
echo 3. Config dosyasini duzenle
echo.

set /p choice="Seciminizi yapin (1-3): "

if "%choice%"=="1" (
    echo.
    echo Tek seferlik fiyat kontrolu basliyor...
    python price_monitor.py
    echo.
    echo Islem tamamlandi!
    pause
) else if "%choice%"=="2" (
    echo.
    set /p run_time="Calisma saati (HH:MM formatinda, ornek: 09:00): "
    if "%run_time%"=="" set run_time=09:00
    echo.
    echo Zamanlanmis sistem basliyor - Her gun %run_time%
    echo CTRL+C ile durdurmak icin...
    python scheduler.py %run_time%
) else if "%choice%"=="3" (
    echo.
    echo Config dosyasi aciliyor...
    if exist config.json (
        notepad config.json
    ) else (
        echo Config dosyasi bulunamadi. Once programi calistirin.
        pause
    )
) else (
    echo Gecersiz secim!
    pause
)

echo.
echo Cikis yapiliyor...
pause