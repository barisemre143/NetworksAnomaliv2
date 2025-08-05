"""
Akakçe Fiyat Çekme Test Sistemi
Netliste hesabı onaylanana kadar test için
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import json
from datetime import datetime
import logging
from urllib.parse import quote_plus

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('akakce_test.log'),
        logging.StreamHandler()
    ]
)

class AkakceTest:
    def __init__(self):
        """Test sistemi başlatıcısı"""
        self.session = requests.Session()
        self.setup_session()
        
        # Test ürünleri (Networks Tedarik'te olabilecek ürünler)
        self.test_products = [
            "iPhone 15 128GB",
            "Samsung Galaxy S24",
            "MacBook Air M2",
            "iPad Pro 11",
            "AirPods Pro 2",
            "Dell XPS 13",
            "HP LaserJet",
            "Canon EOS R6"
        ]
        
    def setup_session(self):
        """HTTP session ayarları"""
        self.session.headers.update({
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
            ]),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
    
    def random_delay(self):
        """2-5 saniye rastgele bekleme"""
        delay = random.uniform(2, 5)
        logging.info(f"⏳ {delay:.1f} saniye bekleniyor...")
        time.sleep(delay)
    
    def search_akakce_prices(self, product_name, max_sellers=5):
        """Akakçe'den ürün fiyatlarını ara"""
        logging.info(f"🔍 Akakçe'de aranıyor: {product_name}")
        
        self.random_delay()
        
        try:
            # Ürün adını URL-safe hale getir
            search_query = quote_plus(product_name)
            search_url = f"https://www.akakce.com/arama/?q={search_query}"
            
            logging.info(f"📡 İstek gönderiliyor: {search_url}")
            response = self.session.get(search_url, timeout=15)
            
            if response.status_code != 200:
                logging.error(f"❌ HTTP Hatası: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            logging.info(f"✅ Sayfa başarıyla yüklendi")
            
            # Farklı fiyat selectorlarını dene
            price_selectors = [
                'span.p_price',
                'span.price_p',
                '.pr_p',
                '.pt_price',
                'span[class*="price"]',
                'div[class*="price"]'
            ]
            
            prices = []
            
            for selector in price_selectors:
                elements = soup.select(selector)
                logging.info(f"🎯 '{selector}' ile {len(elements)} element bulundu")
                
                for element in elements[:max_sellers]:
                    try:
                        price_text = element.get_text(strip=True)
                        
                        # Fiyat regex ile temizle
                        import re
                        price_numbers = re.findall(r'[\d.,]+', price_text)
                        
                        for price_str in price_numbers:
                            price_clean = price_str.replace('.', '').replace(',', '.')
                            try:
                                price = float(price_clean)
                                if 10 <= price <= 100000:  # Makul fiyat aralığı
                                    prices.append(price)
                                    logging.info(f"💰 Fiyat bulundu: {price:.2f}₺")
                            except ValueError:
                                continue
                            
                    except Exception as e:
                        logging.debug(f"Element parse hatası: {e}")
                        continue
                
                if len(prices) >= 3:  # Yeterli fiyat bulunduysa dur
                    break
            
            # Alternatif yöntem: Genel metin araması
            if len(prices) < 3:
                logging.info("🔄 Alternatif fiyat arama yöntemi deneniyor...")
                text_content = soup.get_text()
                import re
                
                # TL, ₺ işaretli fiyatları bul
                price_patterns = [
                    r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*₺',
                    r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*TL',
                    r'₺\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                ]
                
                for pattern in price_patterns:
                    matches = re.findall(pattern, text_content)
                    for match in matches[:10]:
                        try:
                            price_clean = match.replace('.', '').replace(',', '.')
                            price = float(price_clean)
                            if 10 <= price <= 100000:
                                prices.append(price)
                                if len(prices) >= max_sellers:
                                    break
                        except ValueError:
                            continue
                    if len(prices) >= 3:
                        break
            
            # Duplikatları temizle
            prices = list(set([round(p, 2) for p in prices]))
            prices.sort()
            
            if len(prices) >= 3:
                avg_price = sum(prices) / len(prices)
                min_price = min(prices)
                max_price = max(prices)
                
                result = {
                    'product_name': product_name,
                    'prices': prices[:max_sellers],
                    'average': round(avg_price, 2),
                    'min_price': round(min_price, 2),
                    'max_price': round(max_price, 2),
                    'seller_count': len(prices),
                    'timestamp': datetime.now().isoformat()
                }
                
                logging.info(f"✅ {product_name}: {len(prices)} fiyat - Ort: {avg_price:.2f}₺ | Min: {min_price:.2f}₺ | Max: {max_price:.2f}₺")
                return result
            else:
                logging.warning(f"⚠️ {product_name}: Yeterli fiyat bulunamadı ({len(prices)} adet)")
                return None
                
        except requests.RequestException as e:
            logging.error(f"❌ İstek hatası ({product_name}): {e}")
            return None
        except Exception as e:
            logging.error(f"❌ Genel hata ({product_name}): {e}")
            return None
    
    def simulate_price_comparison(self, market_data):
        """Fiyat karşılaştırması simülasyonu"""
        logging.info("📊 Fiyat anomali analizi başlıyor...")
        
        # Sahte bizim fiyatlarımız (test için)
        our_prices = {
            "iPhone 15 128GB": 42000,
            "Samsung Galaxy S24": 38000,
            "MacBook Air M2": 35000,
            "iPad Pro 11": 28000,
            "AirPods Pro 2": 8500,
            "Dell XPS 13": 25000,
            "HP LaserJet": 3500,
            "Canon EOS R6": 45000
        }
        
        anomalies = []
        
        for product_data in market_data:
            product_name = product_data['product_name']
            if product_name in our_prices:
                our_price = our_prices[product_name]
                market_avg = product_data['average']
                
                # Fark yüzdesini hesapla
                if market_avg > 0:
                    price_difference = abs(our_price - market_avg) / market_avg
                    
                    if price_difference > 0.10:  # %10'dan fazla fark
                        anomaly_type = "YÜKSEK" if our_price > market_avg else "DÜŞÜK"
                        
                        anomaly = {
                            'product_name': product_name,
                            'our_price': our_price,
                            'market_average': market_avg,
                            'difference_percent': round(price_difference * 100, 1),
                            'anomaly_type': anomaly_type,
                            'market_prices': product_data['prices'],
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        anomalies.append(anomaly)
                        logging.warning(f"🚨 ANOMALI: {product_name} - Bizim: {our_price}₺ | Piyasa: {market_avg:.2f}₺ | Fark: %{price_difference*100:.1f}")
        
        return anomalies
    
    def run_test(self):
        """Test sistemini çalıştır"""
        logging.info("🚀 === Akakçe Fiyat Çekme Testi Başlıyor ===")
        
        successful_searches = []
        failed_searches = []
        
        for i, product in enumerate(self.test_products, 1):
            logging.info(f"\n📦 [{i}/{len(self.test_products)}] Test ediliyor: {product}")
            
            result = self.search_akakce_prices(product)
            
            if result:
                successful_searches.append(result)
            else:
                failed_searches.append(product)
        
        # Sonuçları kaydet
        results = {
            'test_date': datetime.now().isoformat(),
            'successful_count': len(successful_searches),
            'failed_count': len(failed_searches),
            'successful_products': successful_searches,
            'failed_products': failed_searches
        }
        
        # JSON dosyasına kaydet
        filename = f"akakce_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        
        # Anomali testi
        if successful_searches:
            anomalies = self.simulate_price_comparison(successful_searches)
            
            if anomalies:
                anomaly_filename = f"price_anomalies_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(anomaly_filename, 'w', encoding='utf-8') as f:
                    json.dump(anomalies, f, indent=4, ensure_ascii=False)
                logging.info(f"📋 {len(anomalies)} anomali kaydedildi: {anomaly_filename}")
        
        # Özet rapor
        logging.info("\n" + "="*50)
        logging.info("📊 TEST SONUÇLARI:")
        logging.info(f"✅ Başarılı: {len(successful_searches)}")
        logging.info(f"❌ Başarısız: {len(failed_searches)}")
        logging.info(f"📁 Sonuçlar: {filename}")
        
        if successful_searches:
            logging.info("\n💰 BAŞARILI FİYAT ÇEKİMLERİ:")
            for result in successful_searches:
                logging.info(f"  {result['product_name']}: {result['seller_count']} satıcı, ort: {result['average']}₺")
        
        if failed_searches:
            logging.info(f"\n⚠️ BAŞARISIZ ARAMALAR: {', '.join(failed_searches)}")
        
        logging.info("="*50)
        return results

def main():
    """Test çalıştırıcısı"""
    tester = AkakceTest()
    tester.run_test()

if __name__ == "__main__":
    main()