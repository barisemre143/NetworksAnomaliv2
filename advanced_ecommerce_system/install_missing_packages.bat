@echo off
echo ========================================
echo Eksik Python paketleri kuruluyor...
echo ========================================
echo.

cd /d %~dp0

echo Virtual environment aktif ediliyor...
call venv\Scripts\activate.bat

echo.
echo Eksik paketler kuruluyor...
pip install matplotlib
pip install seaborn
pip install scikit-learn
pip install statsmodels
pip install lxml

echo.
echo ========================================
echo Kurulum tamamlandı! 
echo Şimdi run_dashboard_DEBUG.bat çalıştırın
echo ========================================
pause