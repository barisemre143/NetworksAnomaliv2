#!/usr/bin/env python3
"""
Örnek veri oluşturma scripti
Web dashboard'un çalışması için gerçekçi örnek veriler oluşturur
"""

import sys
import os
import random
from datetime import datetime, timedelta
import json

# Proje dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database.models import (
    init_database, get_db_session, 
    Product, PriceHistory, MarketPrice, PriceAnomaly, PricePrediction
)

def create_sample_products():
    """Örnek ürünler oluştur"""
    session = get_db_session()
    
    # Teknoloji ürünleri
    products = [
        {
            'name': 'iPhone 15 Pro 128GB',
            'brand': 'Apple',
            'category': 'Telefon',
            'subcategory': 'Akıllı Telefon',
            'our_price': 45000.00,
            'our_stock': 25,
            'our_sku': 'APL-IP15P-128'
        },
        {
            'name': 'Samsung Galaxy S24 Ultra 256GB',
            'brand': 'Samsung',
            'category': 'Telefon', 
            'subcategory': 'Akıllı Telefon',
            'our_price': 52000.00,
            'our_stock': 18,
            'our_sku': 'SAM-GS24U-256',
            # 'barcode': '8806095055602'
        },
        {
            'name': 'MacBook Pro 14" M3 512GB',
            'brand': 'Apple',
            'category': 'Bilgisayar',
            'subcategory': 'Laptop',
            'our_price': 89000.00,
            'our_stock': 8,
            'our_sku': 'APL-MBP14-M3-512',
            # 'barcode': '195949042411'
        },
        {
            'name': 'Dell XPS 13 Plus i7 1TB',
            'brand': 'Dell',
            'category': 'Bilgisayar',
            'subcategory': 'Laptop',
            'our_price': 67000.00,
            'our_stock': 12,
            'our_sku': 'DEL-XPS13P-I7-1TB',
            # 'barcode': '884116347514'
        },
        {
            'name': 'Sony WH-1000XM5 Kulaklık',
            'brand': 'Sony',
            'category': 'Ses',
            'subcategory': 'Kulaklık',
            'our_price': 8500.00,
            'our_stock': 45,
            'our_sku': 'SNY-WH1000XM5',
            # 'barcode': '4548736142134'
        },
        {
            'name': 'AirPods Pro 2. Nesil',
            'brand': 'Apple',
            'category': 'Ses',
            'subcategory': 'Kulaklık',
            'our_price': 7800.00,
            'our_stock': 32,
            'our_sku': 'APL-APPRO2',
            # 'barcode': '194253398875'
        },
        {
            'name': 'iPad Air 11" M2 256GB Wi-Fi',
            'brand': 'Apple',
            'category': 'Tablet',
            'subcategory': 'Tablet',
            'our_price': 24000.00,
            'our_stock': 15,
            'our_sku': 'APL-IPADAIR11-M2-256',
            # 'barcode': '195949570217'
        },
        {
            'name': 'Samsung Tab S9 Ultra 512GB',
            'brand': 'Samsung',
            'category': 'Tablet',
            'subcategory': 'Tablet',
            'our_price': 38000.00,
            'our_stock': 6,
            'our_sku': 'SAM-TABS9U-512',
            # 'barcode': '8806094965704'
        },
        {
            'name': 'Nintendo Switch OLED Konsol',
            'brand': 'Nintendo',
            'category': 'Oyun',
            'subcategory': 'Konsol',
            'our_price': 12500.00,
            'our_stock': 22,
            'our_sku': 'NTD-SWOLED',
            # 'barcode': '045496882693'
        },
        {
            'name': 'PlayStation 5 Digital Edition',
            'brand': 'Sony',
            'category': 'Oyun',
            'subcategory': 'Konsol',
            'our_price': 16000.00,
            'our_stock': 5,
            'our_sku': 'SNY-PS5DE',
            # 'barcode': '711719541592'
        }
    ]
    
    created_product_ids = []
    for product_data in products:
        product = Product(**product_data)
        session.add(product)
        session.flush()  # ID'yi almak için
        created_product_ids.append(product.id)
    
    session.commit()
    session.close()
    
    print(f"✅ {len(created_product_ids)} ürün oluşturuldu")
    return created_product_ids

def create_price_history(product_ids, days=90):
    """Fiyat geçmişi oluştur"""
    session = get_db_session()
    
    # Ürünleri yükle
    products = session.query(Product).filter(Product.id.in_(product_ids)).all()
    
    total_records = 0
    
    for product in products:
        print(f"📊 {product.name} için fiyat geçmişi oluşturuluyor...")
        
        # Başlangıç fiyatı
        base_price = product.our_price
        current_our_price = base_price
        
        # Son N günün verilerini oluştur
        start_date = datetime.now() - timedelta(days=days)
        
        for day in range(days + 1):
            current_date = start_date + timedelta(days=day)
            
            # Fiyat dalgalanması simülasyonu
            # Günlük %±3 değişim
            price_change = random.uniform(-0.03, 0.03) 
            current_our_price *= (1 + price_change)
            
            # Minimum fiyat kontrolü (base_price'ın %80'i minimum)
            if current_our_price < base_price * 0.8:
                current_our_price = base_price * random.uniform(0.8, 0.85)
            
            # Maksimum fiyat kontrolü (base_price'ın %130'u maksimum)
            if current_our_price > base_price * 1.3:
                current_our_price = base_price * random.uniform(1.25, 1.3)
            
            # Piyasa fiyatları
            market_variation = random.uniform(-0.15, 0.20)  # ±%15-20 piyasa farkı
            market_avg = current_our_price * (1 + market_variation)
            market_min = market_avg * random.uniform(0.85, 0.95)
            market_max = market_avg * random.uniform(1.05, 1.25)
            market_median = (market_min + market_max) / 2 + random.uniform(-500, 500)
            
            # Rekabetçi sayısı
            competitor_count = random.randint(3, 15)
            
            # Hafta sonu etkisi (Cumartesi-Pazar daha az güncelleme)
            if current_date.weekday() in [5, 6]:  # Cumartesi, Pazar
                if random.random() < 0.3:  # %30 ihtimalle veri yok
                    continue
            
            # Fiyat geçmişi kaydı
            history = PriceHistory(
                product_id=product.id,
                our_price=round(current_our_price, 2),
                market_min_price=round(market_min, 2),
                market_max_price=round(market_max, 2),
                market_avg_price=round(market_avg, 2),
                market_median_price=round(market_median, 2),
                competitor_count=competitor_count,
                date=current_date
            )
            session.add(history)
            total_records += 1
            
            # Piyasa fiyat detayları (çoklu satıcı simülasyonu)
            for i in range(min(competitor_count, 8)):  # Maksimum 8 satıcı
                competitor_price = market_avg * random.uniform(0.9, 1.15)
                competitor_names = [
                    'Trendyol', 'Hepsiburada', 'GittiGidiyor', 'N11',
                    'Amazon', 'Vatanbilgisayar', 'MediaMarkt', 'Teknosa'
                ]
                
                source_name = random.choice(competitor_names)
                market_price = MarketPrice(
                    product_id=product.id,
                    source=source_name.lower(),
                    seller_name=source_name,
                    price=round(competitor_price, 2),
                    scraped_at=current_date + timedelta(
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59)
                    )
                )
                session.add(market_price)
        
        # Ürünün güncel fiyatını güncelle
        product.our_price = round(current_our_price, 2)
        session.add(product)
    
    session.commit()
    session.close()
    
    print(f"✅ {total_records} fiyat geçmişi kaydı oluşturuldu")

def create_price_anomalies(product_ids):
    """Fiyat anomalileri oluştur"""
    session = get_db_session()
    
    # Ürünleri yükle
    products = session.query(Product).filter(Product.id.in_(product_ids)).all()
    
    anomaly_types = ['price_spike', 'price_drop', 'competitor_anomaly', 'seasonal_anomaly']
    severities = ['low', 'medium', 'high']
    
    anomalies_created = 0
    
    for product in products:
        # Her ürün için 2-5 anomali oluştur
        num_anomalies = random.randint(2, 5)
        
        for _ in range(num_anomalies):
            anomaly_type = random.choice(anomaly_types)
            severity = random.choice(severities)
            
            # Sapma yüzdesi
            if severity == 'high':
                deviation = random.uniform(15, 35)
            elif severity == 'medium':
                deviation = random.uniform(8, 15)
            else:
                deviation = random.uniform(3, 8)
            
            # Pozitif/negatif sapma
            if anomaly_type == 'price_drop':
                deviation = -deviation
            elif random.random() < 0.3:  # %30 ihtimalle negatif
                deviation = -deviation
            
            # Tespit zamanı (son 30 gün içinde)
            detected_at = datetime.now() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            # Bazı anomaliler çözümlenmiş
            is_resolved = random.random() < 0.4  # %40 çözümlenme oranı
            resolved_at = None
            notes = None
            
            if is_resolved:
                resolved_at = detected_at + timedelta(
                    hours=random.randint(1, 72)
                )
                resolution_notes = [
                    'Manuel fiyat ayarlaması yapıldı',
                    'Geçici piyasa dalgalanması, normal seviyeye döndü',
                    'Rekabetçi analiz sonrası fiyat güncellendi',
                    'Sezonsal değişiklik, beklenen anomali',
                    'Sistem hatası düzeltildi'
                ]
                notes = random.choice(resolution_notes)
            
            anomaly = PriceAnomaly(
                product_id=product.id,
                anomaly_type=anomaly_type,
                severity=severity,
                deviation_percent=round(deviation, 2),
                detected_at=detected_at,
                is_resolved=is_resolved,
                resolved_at=resolved_at,
                notes=notes
            )
            session.add(anomaly)
            anomalies_created += 1
    
    session.commit()
    session.close()
    
    print(f"✅ {anomalies_created} anomali kaydı oluşturuldu")

def create_predictions(product_ids):
    """Fiyat tahminleri oluştur"""
    session = get_db_session()
    
    # Ürünleri yükle
    products = session.query(Product).filter(Product.id.in_(product_ids)).all()
    
    predictions_created = 0
    models = ['arima', 'lstm', 'prophet', 'ensemble']
    
    for product in products:
        for model in models:
            # 7 günlük tahmin
            prediction_date = datetime.now() + timedelta(days=7)
            
            # Mevcut fiyata göre tahmin
            base_price = product.our_price
            
            # Model doğruluğu simülasyonu
            if model == 'arima':
                accuracy = random.uniform(0.85, 0.92)
                predicted_price = base_price * random.uniform(0.95, 1.08)
            elif model == 'lstm':
                accuracy = random.uniform(0.88, 0.95)
                predicted_price = base_price * random.uniform(0.97, 1.05)
            elif model == 'prophet':
                accuracy = random.uniform(0.82, 0.90)
                predicted_price = base_price * random.uniform(0.94, 1.10)
            else:  # ensemble
                accuracy = random.uniform(0.90, 0.96)
                predicted_price = base_price * random.uniform(0.98, 1.03)
            
            # Güven aralığı
            confidence_lower = predicted_price * 0.95
            confidence_upper = predicted_price * 1.05
            
            prediction = PricePrediction(
                product_id=product.id,
                model_name=model,
                prediction_horizon=7,  # 7 gün sonrası
                predicted_price=round(predicted_price, 2),
                confidence_score=round(accuracy, 4),
                created_at=datetime.now()
            )
            session.add(prediction)
            predictions_created += 1
    
    session.commit()
    session.close()
    
    print(f"✅ {predictions_created} tahmin kaydı oluşturuldu")

def main():
    """Ana fonksiyon"""
    print("🚀 Örnek veri oluşturma başlıyor...")
    
    # Veritabanını başlat
    init_database()
    print("✅ Veritabanı başlatıldı")
    
    # Örnek veriler oluştur
    product_ids = create_sample_products()
    create_price_history(product_ids, days=90)
    create_price_anomalies(product_ids)
    create_predictions(product_ids)
    
    print("\n🎉 Örnek veri oluşturma tamamlandı!")
    print(f"📊 Toplam {len(product_ids)} ürün")
    print("💰 90 günlük fiyat geçmişi")
    print("⚠️ Anomali kayıtları")
    print("🔮 ML tahmin kayıtları")
    print("\n🌐 Web dashboard'u şimdi test edebilirsiniz: http://127.0.0.1:5000")

if __name__ == "__main__":
    main()