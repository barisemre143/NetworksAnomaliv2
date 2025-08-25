#!/usr/bin/env python3
"""
Networks API entegrasyonu test scripti
"""

import requests
import json
from datetime import datetime
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_networks_api():
    """Networks API'yi test et"""
    logging.info("Networks API test başlıyor...")
    
    # API credentials
    username = 'networksAPIUser'
    password = 'zbx5eW6ADbMrvg17HxWP58zKQWND7BUA'
    api_url = 'https://networksadmin.netliste.com/api/getProductListWithCimriURL'
    
    try:
        # API isteği
        response = requests.get(api_url, auth=(username, password), timeout=10)
        
        if response.status_code == 200:
            products = response.json()
            logging.info(f"✅ API başarılı: {len(products)} ürün alındı")
            
            # İlk 5 ürünü göster
            logging.info("İlk 5 ürün:")
            for i, product in enumerate(products[:5], 1):
                logging.info(f"{i}. {product['brand']} {product['productName']} - {product['sellPrice']}₺")
            
            # Kategorilere göre grup
            categories = {}
            for product in products:
                cat = product['productCategoryName']
                if cat not in categories:
                    categories[cat] = 0
                categories[cat] += 1
            
            logging.info(f"Kategoriler: {list(categories.keys())}")
            
            # Test sonuçları kaydet
            test_result = {
                'timestamp': datetime.now().isoformat(),
                'api_status': 'success',
                'total_products': len(products),
                'categories': categories,
                'sample_products': products[:3]
            }
            
            with open('networks_api_test_result.json', 'w', encoding='utf-8') as f:
                json.dump(test_result, f, indent=4, ensure_ascii=False)
            
            return True
            
        else:
            logging.error(f"❌ API hatası: {response.status_code}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Bağlantı hatası: {e}")
        return False

def create_sample_anomaly_data(products):
    """Örnek anomali verisi oluştur"""
    sample_anomalies = []
    
    # İlk 3 ürün için simüle edilmiş anomaliler
    for i, product in enumerate(products[:3], 1):
        # Rastgele piyasa fiyatı simülasyonu
        our_price = float(product['sellPrice'])
        market_price = our_price * (0.85 + i * 0.1)  # Değişken piyasa fiyatları
        
        difference = abs(our_price - market_price) / market_price * 100
        
        if difference > 10:  # %10'dan fazla fark varsa anomali
            anomaly_type = "YÜKSEK" if our_price > market_price else "DÜŞÜK"
            
            sample_anomalies.append({
                'product_id': product['productID'],
                'product_name': product['productName'],
                'brand': product['brand'],
                'our_price': our_price,
                'simulated_market_price': market_price,
                'difference_percent': difference,
                'anomaly_type': anomaly_type,
                'timestamp': datetime.now().isoformat()
            })
    
    return sample_anomalies

def main():
    """Ana test fonksiyonu"""
    logging.info("=== Networks API Entegrasyon Testi ===")
    
    if test_networks_api():
        # Test başarılıysa örnek anomali verisi oluştur
        with open('networks_api_test_result.json', 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        sample_anomalies = create_sample_anomaly_data(result['sample_products'])
        
        logging.info(f"Örnek anomali verisi oluşturuldu: {len(sample_anomalies)} anomali")
        
        for anomaly in sample_anomalies:
            logging.info(f"  - {anomaly['brand']} {anomaly['product_name']}: {anomaly['our_price']}₺ vs {anomaly['simulated_market_price']:.2f}₺ ({anomaly['difference_percent']:.1f}% {anomaly['anomaly_type']})")
        
        # Anomali verilerini kaydet
        filename = f"sample_anomalies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(sample_anomalies, f, indent=4, ensure_ascii=False)
        
        logging.info(f"Örnek anomali verileri kaydedildi: {filename}")
        logging.info("✅ Test tamamlandı!")
    else:
        logging.error("❌ API testi başarısız!")

if __name__ == "__main__":
    main()