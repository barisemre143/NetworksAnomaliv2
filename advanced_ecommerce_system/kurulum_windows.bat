@echo off
echo =========================================
echo Gelişmiş E-Ticaret Fiyat Analiz Sistemi
echo Windows Kurulum Script'i
echo =========================================
echo.

REM Python versiyonu kontrol
python --version
if %ERRORLEVEL% NEQ 0 (
    echo HATA: Python bulunamadi!
    echo Python 3.8+ gereklidir.
    pause
    exit /b 1
)

echo.
echo 1. Virtual environment temizleniyor...
if exist "venv" rmdir /s /q venv

echo 2. Yeni virtual environment olusturuluyor...
python -m venv venv

echo 3. Virtual environment aktif ediliyor...
call venv\Scripts\activate.bat

echo 4. pip guncelleniyor...
python -m pip install --upgrade pip

echo 5. Temel paketler yukleniyor...
pip install flask==2.3.3
pip install flask-cors==4.0.0
pip install sqlalchemy==1.4.53
pip install pandas==2.0.3
pip install numpy==1.24.4
pip install plotly==5.15.0
pip install requests==2.31.0
pip install beautifulsoup4==4.12.2
pip install lxml==4.9.3
pip install python-dateutil==2.8.2

echo.
echo =========================================
echo Kurulum tamamlandi!
echo Web dashboard'u baslatmak icin:
echo run_dashboard.bat dosyasini calistirin
echo =========================================
pause