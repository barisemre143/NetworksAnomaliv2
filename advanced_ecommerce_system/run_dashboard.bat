@echo off
echo =========================================
echo Web Dashboard Baslatiliyor...
echo =========================================
echo.

REM Virtual environment aktif et
call venv\Scripts\activate.bat

REM Veritabanı kontrolü
if not exist "ecommerce_analytics.db" (
    echo Veritabani bulunamadi, olusturuluyor...
    python create_sample_data.py
)

echo.
echo =========================================
echo Dashboard baslatiliyor...
echo Tarayicinizda su adresi acin:
echo http://127.0.0.1:5000
echo.
echo Durdurmak icin Ctrl+C basin
echo =========================================
echo.

REM Flask uygulamasını başlat
python web_dashboard\app.py

pause