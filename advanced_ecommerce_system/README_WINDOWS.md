# Windows Kurulum Rehberi

## 🚀 Hızlı Başlangıç

### 1. Otomatik Kurulum
```bash
kurulum_windows.bat
```
Bu dosyaya çift tıklayın - otomatik olarak tüm paketleri yükler.

### 2. Dashboard Başlatma
```bash
run_dashboard.bat
```
Bu dosyaya çift tıklayın - web dashboard'u başlatır.

### 3. Tarayıcıda Açın
http://127.0.0.1:5000

## 🔧 Manuel Kurulum (Sorun Olursa)

```bash
# 1. Virtual environment oluştur
python -m venv venv

# 2. Aktif et
venv\Scripts\activate

# 3. Temel paketleri yükle
pip install flask==2.3.3
pip install flask-cors==4.0.0
pip install sqlalchemy==1.4.53
pip install pandas==2.0.3
pip install numpy==1.24.4
pip install plotly==5.15.0
pip install requests==2.31.0
pip install beautifulsoup4==4.12.2

# 4. Dashboard başlat
python web_dashboard\app.py
```

## ⚠️ Sorun Giderme

### "Python bulunamadı" Hatası
- Python 3.8+ yükleyin: https://python.org
- Kurulum sırasında "Add to PATH" seçin

### "ModuleNotFoundError" Hatası
- Virtual environment aktif mi kontrol edin
- `kurulum_windows.bat` tekrar çalıştırın

### Port 5000 Kullanımda
- `web_dashboard\app.py` dosyasında port'u değiştirin (5001 yapın)

## 📊 Sistem Özellikleri

- ✅ **10 Örnek Ürün**: iPhone, Samsung, MacBook vb.
- ✅ **90 Günlük Fiyat Geçmişi**: Gerçekçi veriler 
- ✅ **38+ Anomali**: Otomatik tespit
- ✅ **ML Analizler**: Trend, tahmin modelleri
- ✅ **Modern UI**: Bootstrap 5 arayüzü

## 🎯 Kullanım

1. **Dashboard**: Ana sayfa - genel istatistikler
2. **Analitik**: Gelişmiş ML analizleri
3. **Anomaliler**: Fiyat anomalilerini yönetim
4. **Ürün Seçimi**: Dropdown'dan ürün seçip analiz

**🎉 Başarılar! Data science öğreniminizde faydalı olması dileğiyle.**