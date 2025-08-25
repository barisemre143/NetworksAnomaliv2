"""
E-Ticaret Fiyat Takip ve Anomali Tespit Sistemi
Networks Tedarik için Akakçe fiyat karşılaştırması
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from datetime import datetime
import logging
from urllib.parse import quote_plus

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('price_monitor.log'),
        logging.StreamHandler()
    ]
)

class PriceMonitor:
    def __init__(self, config_file='../config.json'):
        """Fiyat takip sistemi başlatıcısı"""
        self.config = self.load_config(config_file)
        self.session = requests.Session()
        self.setup_session()
        
    def load_config(self, config_file):
        """Konfigürasyon dosyasını yükle"""
        default_config = {
            "networks_api": {
                "username": "networksAPIUser",
                "password": "zbx5eW6ADbMrvg17HxWP58zKQWND7BUA",
                "api_url": "https://networksadmin.netliste.com/api/getProductListWithCimriURL"
            },
            "akakce": {
                "base_url": "https://www.akakce.com",
                "search_url": "https://www.akakce.com/arama/?q="
            },
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": "",
                "recipient_email": ""
            },
            "settings": {
                "price_threshold": 0.10,  # %10 fark
                "min_sellers": 3,  # Minimum satıcı sayısı
                "request_delay": [2, 5],  # Saniye cinsinden bekleme aralığı
                "max_retries": 3
            }
        }
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Eksik anahtarları varsayılan değerlerle tamamla
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        else:
            # Varsayılan config dosyasını oluştur
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            logging.info(f"Yeni config dosyası oluşturuldu: {config_file}")
            return default_config
    
    def setup_session(self):
        """HTTP session ayarları"""
        self.session.headers.update({
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
            ]),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def random_delay(self):
        """Rastgele bekleme süresi"""
        delay = random.uniform(*self.config['settings']['request_delay'])
        time.sleep(delay)
    
    def get_networks_api_products(self):
        """Networks API'den ürün listesini al"""
        logging.info("Networks API'den ürünler alınıyor...")
        
        try:
            # API credentials hazırla
            auth = (self.config['networks_api']['username'], self.config['networks_api']['password'])
            
            # API isteği gönder
            response = self.session.get(self.config['networks_api']['api_url'], auth=auth)
            
            if response.status_code == 200:
                products_data = response.json()
                logging.info(f"Networks API'den {len(products_data)} ürün alındı")
                
                # Ürün verilerini standardize et
                products = []
                for product in products_data:
                    if float(product.get('sellPrice', 0)) > 0:  # Sadece fiyatı olan ürünler
                        products.append({
                            'id': product['productID'],
                            'name': product['productName'],
                            'full_name': product['productFullName'],
                            'current_price': float(product['sellPrice']),
                            'brand': product['brand'],
                            'category': product['productCategoryName'],
                            'stock_code': product['stockCode'],
                            'cimri_url': product.get('cimriURL', ''),
                            'source': 'networks_api'
                        })
                
                logging.info(f"{len(products)} aktif ürün hazırlandı")
                return products
                
            else:
                logging.error(f"Networks API hatası: {response.status_code}")
                return []
                
        except Exception as e:
            logging.error(f"Networks API bağlantı hatası: {e}")
            return []
    
    def get_products_from_netliste(self):
        """Netliste'den ürün listesini al"""
        logging.info("Netliste'den ürünler alınıyor...")
        
        try:
            response = self.session.get(self.config['netliste']['dashboard_url'])
            soup = BeautifulSoup(response.content, 'html.parser')
            
            products = []
            
            # Ürün tablolarını bul (sitenin yapısına göre düzenlenecek)
            product_rows = soup.find_all('tr')[1:]  # İlk satır başlık olabilir
            
            for row in product_rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:  # En az ürün adı, fiyat olmalı
                    try:
                        # Bu kısım sitenin gerçek yapısına göre düzenlenecek
                        product_name = cells[0].get_text(strip=True)
                        current_price_text = cells[1].get_text(strip=True)
                        
                        # Fiyatı sayıya çevir
                        current_price = float(''.join(filter(str.isdigit, current_price_text.replace(',', '.'))))
                        
                        if product_name and current_price > 0:
                            products.append({
                                'name': product_name,
                                'current_price': current_price,
                                'source': 'netliste'
                            })
                            
                    except (ValueError, IndexError) as e:
                        logging.warning(f"Ürün parse hatası: {e}")
                        continue
            
            logging.info(f"{len(products)} ürün bulundu")
            return products
            
        except Exception as e:
            logging.error(f"Netliste ürün alma hatası: {e}")
            return []
    
    def search_akakce_prices(self, product_name, brand="", max_sellers=5):
        """Akakçe'den ürün fiyatlarını ara"""
        search_term = f"{brand} {product_name}".strip()
        logging.info(f"Akakçe'de aranıyor: {search_term}")
        
        self.random_delay()
        
        try:
            # Ürün adını URL-safe hale getir
            search_query = quote_plus(search_term)
            search_url = f"{self.config['akakce']['search_url']}{search_query}"
            
            response = self.session.get(search_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            prices = []
            
            # Fiyat listelerini bul (Akakçe'nin yeni yapısına uygun)
            price_elements = soup.find_all(['span', 'div'], class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['price', 'fiyat', 'fy_v8', 'pt_v8']
            ))
            
            for element in price_elements[:max_sellers * 2]:  # Daha fazla element kontrol et
                try:
                    price_text = element.get_text(strip=True)
                    # Fiyat formatını temizle (₺, TL, virgül vs.)
                    price_clean = ''.join(c for c in price_text if c.isdigit() or c in '.,')
                    price_clean = price_clean.replace(',', '.')
                    
                    if price_clean and '.' in price_clean:
                        # Ondalık ayıracı kontrol et
                        parts = price_clean.split('.')
                        if len(parts) == 2 and len(parts[1]) <= 2:  # Normal fiyat formatı
                            price = float(price_clean)
                            if 1000 <= price <= 200000:  # Mantıklı fiyat aralığı
                                prices.append(price)
                                if len(prices) >= max_sellers:
                                    break
                    elif price_clean and len(price_clean) >= 4:  # Sadece rakam
                        price = float(price_clean)
                        if 1000 <= price <= 200000:
                            prices.append(price)
                            if len(prices) >= max_sellers:
                                break
                            
                except (ValueError, AttributeError):
                    continue
            
            if len(prices) >= self.config['settings']['min_sellers']:
                avg_price = sum(prices) / len(prices)
                logging.info(f"{search_term}: {len(prices)} satıcı, ortalama: {avg_price:.2f}₺")
                return {
                    'prices': prices,
                    'average': avg_price,
                    'seller_count': len(prices),
                    'min_price': min(prices),
                    'max_price': max(prices)
                }
            else:
                logging.warning(f"{search_term}: Yeterli satıcı bulunamadı ({len(prices)})")
                return None
                
        except Exception as e:
            logging.error(f"Akakçe arama hatası ({search_term}): {e}")
            return None
    
    def analyze_price_anomalies(self, products, max_products=10):
        """Fiyat anomalilerini tespit et"""
        anomalies = []
        processed_count = 0
        
        for product in products[:max_products]:  # Sınırlı sayıda ürün işle
            processed_count += 1
            logging.info(f"İşleniyor ({processed_count}/{min(len(products), max_products)}): {product['brand']} {product['name']}")
            
            # Brand bilgisi ile arama yap
            akakce_data = self.search_akakce_prices(product['name'], product['brand'])
            
            if akakce_data:
                current_price = product['current_price']
                market_avg = akakce_data['average']
                
                # Fark yüzdesini hesapla
                price_difference = abs(current_price - market_avg) / market_avg
                
                if price_difference > self.config['settings']['price_threshold']:
                    anomaly_type = "YÜKSEK" if current_price > market_avg else "DÜŞÜK"
                    
                    anomalies.append({
                        'product_id': product['id'],
                        'product_name': product['name'],
                        'full_name': product['full_name'],
                        'brand': product['brand'],
                        'category': product['category'],
                        'our_price': current_price,
                        'market_average': market_avg,
                        'market_min': akakce_data['min_price'],
                        'market_max': akakce_data['max_price'],
                        'difference_percent': price_difference * 100,
                        'anomaly_type': anomaly_type,
                        'seller_count': akakce_data['seller_count'],
                        'cimri_url': product.get('cimri_url', ''),
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    logging.warning(f"ANOMALI: {product['brand']} {product['name']} - Bizim: {current_price}₺, Piyasa: {market_avg:.2f}₺ ({price_difference*100:.1f}% fark)")
                else:
                    logging.info(f"Normal: {product['brand']} {product['name']} - Bizim: {current_price}₺, Piyasa: {market_avg:.2f}₺")
            else:
                logging.warning(f"Piyasa verisi bulunamadı: {product['brand']} {product['name']}")
        
        return anomalies
    
    def send_email_alert(self, anomalies):
        """Email uyarısı gönder"""
        if not anomalies:
            return True
            
        logging.info(f"{len(anomalies)} anomali için email gönderiliyor...")
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email']['sender_email']
            msg['To'] = self.config['email']['recipient_email']
            msg['Subject'] = f"🚨 Fiyat Anomalisi Tespit Edildi - {len(anomalies)} Ürün"
            
            # HTML email içeriği
            html_body = """
            <html>
            <body>
            <h2>🚨 Fiyat Anomalisi Raporu</h2>
            <p>Aşağıdaki ürünlerde piyasa ortalamasından %10'dan fazla fark tespit edilmiştir:</p>
            <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <th>Ürün</th>
                <th>Bizim Fiyat</th>
                <th>Piyasa Ortalaması</th>
                <th>Fark %</th>
                <th>Durum</th>
            </tr>
            """
            
            for anomaly in anomalies:
                color = "#ffebee" if anomaly['anomaly_type'] == "YÜKSEK" else "#e8f5e8"
                html_body += f"""
                <tr style="background-color: {color};">
                    <td>{anomaly['product_name']}</td>
                    <td>{anomaly['our_price']:.2f}₺</td>
                    <td>{anomaly['market_average']:.2f}₺</td>
                    <td>{anomaly['difference_percent']:.1f}%</td>
                    <td><strong>{anomaly['anomaly_type']}</strong></td>
                </tr>
                """
            
            html_body += """
            </table>
            <br>
            <p><small>Bu rapor otomatik olarak oluşturulmuştur.</small></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Email gönder
            server = smtplib.SMTP(self.config['email']['smtp_server'], self.config['email']['smtp_port'])
            server.starttls()
            server.login(self.config['email']['sender_email'], self.config['email']['sender_password'])
            text = msg.as_string()
            server.sendmail(self.config['email']['sender_email'], self.config['email']['recipient_email'], text)
            server.quit()
            
            logging.info("Email başarıyla gönderildi!")
            return True
            
        except Exception as e:
            logging.error(f"Email gönderme hatası: {e}")
            return False
    
    def save_results(self, anomalies):
        """Sonuçları dosyaya kaydet"""
        filename = f"price_anomalies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(anomalies, f, indent=4, ensure_ascii=False)
        
        logging.info(f"Sonuçlar kaydedildi: {filename}")
    
    def run(self, max_products=10):
        """Ana çalışma fonksiyonu"""
        logging.info("=== Networks Fiyat Takip Sistemi Başlıyor ===")
        
        # Networks API'den ürünleri al
        products = self.get_networks_api_products()
        if not products:
            logging.error("Networks API'den ürün alınamadı!")
            return False
        
        logging.info(f"Toplam {len(products)} ürün bulundu, {max_products} tanesi işlenecek")
        
        # Anomali analizi
        anomalies = self.analyze_price_anomalies(products, max_products)
        
        # Sonuçları kaydet
        self.save_results(anomalies)
        
        # Email gönder (anomali varsa - şu an pasif)
        if anomalies:
            logging.info(f"✅ {len(anomalies)} anomali tespit edildi!")
            for anomaly in anomalies:
                logging.info(f"   - {anomaly['brand']} {anomaly['product_name']}: {anomaly['our_price']}₺ vs {anomaly['market_average']:.2f}₺ ({anomaly['difference_percent']:.1f}% {anomaly['anomaly_type']})")
        else:
            logging.info("✅ Hiç anomali tespit edilmedi.")
        
        logging.info("=== İşlem Tamamlandı ===")
        return True

def main():
    """Manuel çalıştırma"""
    monitor = PriceMonitor()
    monitor.run(max_products=5)  # Test için 5 ürün

if __name__ == "__main__":
    main()