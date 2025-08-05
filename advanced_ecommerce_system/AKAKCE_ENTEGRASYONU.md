# 🛒 Akakçe Entegrasyonu - Gerçek Fiyat Karşılaştırması

## ✅ Yeni Özellikler

### 📊 Dashboard Akakçe Entegrasyonu
- **Gerçek zamanlı Akakçe verisi çekme**
- **Fiyat karşılaştırması ve anomali tespiti**  
- **İnteraktif scraping butonları**
- **Otomatik veritabanı kayıt**

### 🎯 Nasıl Kullanılır

#### 1. Dashboard'dan Tek Ürün Çekme
```
1. Dashboard sayfasına gidin (http://127.0.0.1:5000)
2. "Hızlı Analiz" bölümünden bir ürün seçin
3. "Akakçe'den Çek" butonuna tıklayın
4. Sonuçları gerçek zamanlı bildirimde görün
```

#### 2. Scraping Durumu Kontrolü
```
1. Bir ürün seçtikten sonra "Durum" butonuna tıklayın
2. Toplam veri, bugünkü çekme sayısı görüntülenir
3. Son scraping zamanını kontrol edin
```

#### 3. API Üzerinden Kullanım
```bash
# Tek ürün için scraping
curl -X POST http://127.0.0.1:5000/api/scraping/akakce/single/1

# Tüm ürünler için scraping  
curl -X POST http://127.0.0.1:5000/api/scraping/akakce/all

# Scraping durumu
curl http://127.0.0.1:5000/api/scraping/status
```

### 🚀 Otomatik Özellikler

#### ⚠️ Anomali Tespiti
- **%10'dan fazla fark** anomali olarak işaretlenir
- **Üç seviye önem:** High, Medium, Low
- **Otomatik veritabanı kaydı**

#### 📈 Karşılaştırma Metrikleri
- **Minimum piyasa fiyatı**
- **Maksimum piyasa fiyatı**  
- **Ortalama piyasa fiyatı**
- **Satıcı sayısı**
- **Bizim fiyat pozisyonu**

### 🔧 Teknik Detaylar

#### Dosya Yapısı
```
scrapers/
├── __init__.py
└── akakce_scraper.py      # Ana scraper sınıfı

web_dashboard/
├── app.py                 # Yeni API endpoint'leri
└── templates/
    └── dashboard.html     # JavaScript fonksiyonları
```

#### Yeni API Endpoint'leri
- `POST /api/scraping/akakce/single/<product_id>` 
- `POST /api/scraping/akakce/all`
- `GET /api/scraping/status`

#### JavaScript Fonksiyonları
- `scrapeSelectedProduct()` - Tek ürün scraping
- `checkScrapingStatus()` - Durum kontrolü
- `showNotification()` - Sonuç bildirimleri
- `showStatusModal()` - Durum modal'ı

### 📋 Veritabanı Yapısı

#### MarketPrice Tablosu
```sql
CREATE TABLE market_prices (
    id INTEGER PRIMARY KEY,
    product_id INTEGER,
    source VARCHAR(50),        # 'akakce'
    seller_name VARCHAR(200),
    price FLOAT,
    currency VARCHAR(10),
    scraped_at DATETIME
);
```

#### PriceAnomaly Tablosu  
```sql
CREATE TABLE price_anomalies (
    id INTEGER PRIMARY KEY,
    product_id INTEGER,
    anomaly_type VARCHAR(50),   # 'price_high', 'price_low'
    severity VARCHAR(20),       # 'high', 'medium', 'low'
    deviation_percent FLOAT,
    detected_at DATETIME,
    is_resolved BOOLEAN
);
```

### ⚡ Performans ve Güvenlik

#### Saygılı Scraping
- **2-5 saniye rastgele gecikme** her istek arasında
- **Dönen User-Agent** başlıkları
- **Hata yönetimi** ve yeniden deneme mantığı

#### Veri Kalitesi
- **Minimum fiyat filtreleme** (10 TL altı fiyatlar elenir)
- **Veri doğrulama** ve temizleme
- **Detaylı loglama** ve hata takibi

### 🎉 Kullanım Senaryoları

1. **Günlük Fiyat Kontrolü:** Ürünlerinizin piyasadaki durumunu kontrol edin
2. **Rekabet Analizi:** Rakip fiyatlarını takip edin  
3. **Anomali Takibi:** Fiyat değişikliklerini otomatik tespit edin
4. **Strateji Geliştirme:** Piyasa verilerine dayalı fiyat stratejisi oluşturun

### ⚠️ Önemli Notlar

- İlk kullanımda bazı ürünler için fiyat bulunamayabilir (site yapısı değişikliği)
- Scraping işlemi internet bağlantınıza bağlı olarak 30-60 saniye sürebilir
- Anomali tespit eşiği dashboard ayarlarından değiştirilebilir
- Tüm veriler yerel SQLite veritabanında saklanır

## 🔄 Güncellemeler

### v2.1 - Akakçe Entegrasyonu
- ✅ Gerçek Akakçe veri çekme
- ✅ İnteraktif dashboard butonları  
- ✅ Otomatik anomali tespiti
- ✅ API endpoint'leri
- ✅ Real-time bildirimler

---

**Geliştirici:** Claude Code
**Tarih:** 31 Temmuz 2025
**Sürüm:** 2.1.0