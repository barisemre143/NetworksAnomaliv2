#!/usr/bin/env python3
"""
Akakçe Entegre Scraper - Dashboard İçin
Gerçek Akakçe verilerini çekip veritabanına kaydeder
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import json
import sys
import os
from datetime import datetime, timedelta
import logging
from urllib.parse import quote_plus
import re

# Proje dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database.models import get_db_session, Product, MarketPrice, PriceAnomaly

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AkakceScraper:
    def __init__(self):
        """Akakçe scraper başlatıcısı"""
        self.session = requests.Session()
        self.setup_session()
        self.anomaly_threshold = 10.0  # %10 fark anomali sayılır
        
    def setup_session(self):
        """HTTP session ayarları"""
        self.session.headers.update({
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def search_product(self, product_name):
        """Akakçe'de ürün ara"""
        try:
            # URL encode
            search_query = quote_plus(product_name)
            search_url = f"https://www.akakce.com/arama/?q={search_query}"
            
            logger.info(f"Akakçe'de aranıyor: {product_name}")
            
            # İstek gönder
            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ürün linklerini bul
            product_links = []
            
            # Ana ürün listesi
            product_elements = soup.find_all('div', class_='p')
            for element in product_elements[:3]:  # İlk 3 sonuç
                link_elem = element.find('a')
                if link_elem and link_elem.get('href'):
                    product_url = 'https://www.akakce.com' + link_elem['href']
                    product_title = link_elem.get_text(strip=True)
                    product_links.append({
                        'url': product_url,
                        'title': product_title
                    })
            
            if not product_links:
                # Alternatif arama
                product_elements = soup.find_all('a', href=re.compile(r'/[^/]+\.html'))
                for element in product_elements[:3]:
                    if element.get('href') and element.get_text(strip=True):
                        product_url = 'https://www.akakce.com' + element['href']
                        product_title = element.get_text(strip=True)
                        if len(product_title) > 10 and product_name.lower().split()[0] in product_title.lower():
                            product_links.append({
                                'url': product_url,
                                'title': product_title
                            })
            
            logger.info(f"{len(product_links)} ürün bulundu")
            return product_links
            
        except Exception as e:
            logger.error(f"Ürün arama hatası: {e}")
            return []
    
    def get_product_prices(self, product_url):
        """Ürün sayfasından fiyatları çek"""
        try:
            logger.info(f"Fiyatlar çekiliyor: {product_url}")
            
            response = self.session.get(product_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            prices = []
            
            # Debug: Sayfa içeriğini kontrol et
            logger.debug(f"Sayfa başlığı: {soup.title.string if soup.title else 'Yok'}")
            
            # Modern Akakçe fiyat yapısını ara
            # 1. Yeni tablo yapısı
            price_table = soup.find('table', class_='w')
            if price_table:
                rows = price_table.find_all('tr')[1:]  # İlk satır başlık
                for row in rows[:10]:
                    try:
                        # Satıcı adı (genellikle ikinci td)
                        cells = row.find_all('td')
                        if len(cells) < 2:
                            continue
                            
                        merchant_cell = cells[1] if len(cells) > 1 else cells[0]
                        merchant_name = merchant_cell.get_text(strip=True)
                        
                        # Fiyat - farklı olası pozisyonlar
                        price_text = None
                        for cell in cells:
                            text = cell.get_text(strip=True)
                            if '₺' in text or 'TL' in text:
                                price_text = text
                                break
                        
                        if not price_text:
                            continue
                            
                        # Fiyatı temizle ve çevir
                        price_clean = re.sub(r'[^\d,.]', '', price_text)
                        price_clean = price_clean.replace('.', '').replace(',', '.')
                        
                        try:
                            price = float(price_clean)
                            if price > 100:  # Çok düşük fiyatları filtrele
                                prices.append({
                                    'merchant': merchant_name[:50],  # Uzun isimleri kısalt
                                    'price': price,
                                    'currency': 'TRY'
                                })
                        except ValueError:
                            continue
                            
                    except Exception as e:
                        logger.debug(f"Satır parse hatası: {e}")
                        continue
            
            # 2. Alternatif: Tüm fiyat patternlerini ara
            if not prices:
                price_patterns = [
                    r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*₺',
                    r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*TL',
                    r'₺\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                ]
                
                page_text = soup.get_text()
                for pattern in price_patterns:
                    matches = re.findall(pattern, page_text)
                    for match in matches[:5]:
                        try:
                            price_clean = match.replace('.', '').replace(',', '.')
                            price = float(price_clean)
                            if 1000 < price < 200000:  # Makul fiyat aralığı
                                prices.append({
                                    'merchant': 'Akakçe Fiyat',
                                    'price': price,
                                    'currency': 'TRY'
                                })
                        except ValueError:
                            continue
                    if prices:
                        break
            
            # 3. Son alternatif: Tüm sayısal değerleri kontrol et
            if not prices:
                all_numbers = re.findall(r'\d{2,6}', soup.get_text())
                for num_str in all_numbers[:10]:
                    try:
                        num = float(num_str)
                        if 10000 < num < 100000:  # iPhone fiyat aralığı
                            prices.append({
                                'merchant': 'Akakçe Tahmin',
                                'price': num,
                                'currency': 'TRY'
                            })
                    except ValueError:
                        continue
                    if len(prices) >= 3:
                        break
            
            # Fiyatları temizle ve sırala
            if prices:
                # Duplikatları kaldır
                unique_prices = []
                seen_prices = set()
                for p in prices:
                    price_key = (p['merchant'], int(p['price']))
                    if price_key not in seen_prices:
                        unique_prices.append(p)
                        seen_prices.add(price_key)
                
                prices = sorted(unique_prices, key=lambda x: x['price'])[:8]
            
            logger.info(f"{len(prices)} fiyat bulundu")
            return prices
            
        except Exception as e:
            logger.error(f"Fiyat çekme hatası: {e}")
            return []
    
    def scrape_product_data(self, product_name):
        """Ürün için tüm veriyi çek"""
        try:
            # Rastgele gecikme
            time.sleep(random.uniform(2, 5))
            
            # Ürün ara
            product_links = self.search_product(product_name)
            if not product_links:
                logger.warning(f"Ürün bulunamadı: {product_name}")
                return None
            
            all_prices = []
            
            # Her ürün linkinden fiyat çek
            for product_link in product_links[:2]:  # İlk 2 ürün
                prices = self.get_product_prices(product_link['url'])
                for price_data in prices:
                    price_data['product_title'] = product_link['title']
                    price_data['product_url'] = product_link['url']
                all_prices.extend(prices)
                
                # Saygılı gecikme
                time.sleep(random.uniform(1, 3))
            
            if not all_prices:
                logger.warning(f"Fiyat bulunamadı: {product_name}")
                return None
            
            # İstatistikleri hesapla
            price_values = [p['price'] for p in all_prices]
            
            result = {
                'product_name': product_name,
                'scraped_at': datetime.now(),
                'prices': all_prices,
                'min_price': min(price_values),
                'max_price': max(price_values),
                'avg_price': sum(price_values) / len(price_values),
                'median_price': sorted(price_values)[len(price_values)//2],
                'price_count': len(price_values)
            }
            
            logger.info(f"✅ {product_name}: {len(price_values)} fiyat - Ort: ₺{result['avg_price']:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Scraping hatası {product_name}: {e}")
            return None
    
    def save_to_database(self, product_id, scraped_data):
        """Çekilen veriyi veritabanına kaydet"""
        if not scraped_data:
            return False
        
        try:
            session = get_db_session()
            
            # Her fiyat için MarketPrice kaydı oluştur
            for price_data in scraped_data['prices']:
                market_price = MarketPrice(
                    product_id=product_id,
                    source='akakce',
                    seller_name=price_data['merchant'],
                    price=price_data['price'],
                    currency=price_data.get('currency', 'TRY'),
                    scraped_at=scraped_data['scraped_at']
                )
                session.add(market_price)
            
            session.commit()
            session.close()
            
            logger.info(f"✅ Veritabanına kaydedildi: {scraped_data['product_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Veritabanı kayıt hatası: {e}")
            return False
    
    def detect_price_anomalies(self, product_id, our_price, market_data):
        """Fiyat anomalilerini tespit et"""
        if not market_data:
            logger.info("Market data yok, anomali tespiti yapılamıyor")
            return []
        
        anomalies = []
        session = get_db_session()
        
        try:
            market_avg = market_data['avg_price']
            
            # Fiyat farkını hesapla
            price_diff_percent = ((our_price - market_avg) / market_avg) * 100
            
            logger.info(f"🔍 Anomali kontrolü: Bizim=₺{our_price}, Piyasa=₺{market_avg:.2f}, Fark=%{price_diff_percent:.1f}")
            logger.info(f"🔍 Threshold: %{self.anomaly_threshold}")
            
            # Anomali kontrolü
            if abs(price_diff_percent) > self.anomaly_threshold:
                
                # Anomali türünü belirle
                if price_diff_percent > 0:
                    anomaly_type = 'price_high'
                else:
                    anomaly_type = 'price_low'
                
                # Önem derecesi
                if abs(price_diff_percent) > 25:
                    severity = 'high'
                elif abs(price_diff_percent) > 15:
                    severity = 'medium'
                else:
                    severity = 'low'
                
                logger.info(f"⚠️ Anomali tespit edildi! Tip: {anomaly_type}, Önem: {severity}")
                
                # Anomali kaydı oluştur
                anomaly = PriceAnomaly(
                    product_id=product_id,
                    anomaly_type=anomaly_type,
                    severity=severity,
                    deviation_percent=price_diff_percent,
                    detected_at=datetime.now(),
                    is_resolved=False,
                    notes=f"Akakçe scraping ile tespit edildi - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                )
                
                session.add(anomaly)
                session.flush()  # ID almak için
                logger.info(f"✅ Anomali veritabanına eklendi: ID={anomaly.id}")
                
                anomalies.append({
                    'type': anomaly_type,
                    'severity': severity,
                    'deviation': price_diff_percent,
                    'our_price': our_price,
                    'market_avg': market_avg
                })
            else:
                logger.info(f"ℹ️ Anomali yok: Fark %{abs(price_diff_percent):.1f} < threshold %{self.anomaly_threshold}")
            
            session.commit()
            logger.info(f"💾 Database commit yapıldı")
            session.close()
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomali tespit hatası: {e}")
            import traceback
            logger.error(traceback.format_exc())
            session.rollback()
            session.close()
            return []
    
    def scrape_all_products(self):
        """Veritabanındaki tüm aktif ürünler için scraping yap"""
        session = get_db_session()
        
        try:
            # Aktif ürünleri al
            products = session.query(Product).filter(Product.is_active == True).all()
            session.close()
            
            logger.info(f"🚀 {len(products)} ürün için Akakçe scraping başlıyor...")
            
            scraped_count = 0
            anomaly_count = 0
            
            for product in products:
                try:
                    logger.info(f"📊 İşleniyor: {product.name}")
                    
                    # Ürün için Akakçe'den veri çek
                    scraped_data = self.scrape_product_data(product.name)
                    
                    if scraped_data:
                        # Veritabanına kaydet
                        if self.save_to_database(product.id, scraped_data):
                            scraped_count += 1
                        
                        # Anomali tespiti
                        anomalies = self.detect_price_anomalies(
                            product.id, 
                            product.our_price, 
                            scraped_data
                        )
                        
                        if anomalies:
                            anomaly_count += len(anomalies)
                            logger.warning(f"⚠️ {len(anomalies)} anomali tespit edildi: {product.name}")
                            for anomaly in anomalies:
                                logger.warning(
                                    f"   {anomaly['type']} - {anomaly['severity']}: "
                                    f"Bizim: ₺{anomaly['our_price']:.2f}, "
                                    f"Piyasa: ₺{anomaly['market_avg']:.2f}, "
                                    f"Fark: %{anomaly['deviation']:.1f}"
                                )
                    
                    # Saygılı gecikme
                    time.sleep(random.uniform(3, 7))
                    
                except Exception as e:
                    logger.error(f"Ürün işleme hatası {product.name}: {e}")
                    continue
            
            logger.info(f"🎉 Scraping tamamlandı!")
            logger.info(f"✅ {scraped_count}/{len(products)} ürün işlendi")
            logger.info(f"⚠️ {anomaly_count} anomali tespit edildi")
            
            return {
                'total_products': len(products),
                'scraped_products': scraped_count,
                'anomalies_detected': anomaly_count
            }
            
        except Exception as e:
            logger.error(f"Toplu scraping hatası: {e}")
            return None

def main():
    """Test çalıştırması"""
    scraper = AkakceScraper()
    
    # Tek ürün testi
    test_product = "iPhone 15 128GB"
    result = scraper.scrape_product_data(test_product)
    
    if result:
        print(f"\n🎉 Test Başarılı: {test_product}")
        print(f"💰 Ortalama Fiyat: ₺{result['avg_price']:.2f}")
        print(f"📊 Fiyat Aralığı: ₺{result['min_price']:.2f} - ₺{result['max_price']:.2f}")
        print(f"🏪 Satıcı Sayısı: {result['price_count']}")
    else:
        print("❌ Test başarısız")

if __name__ == "__main__":
    main()