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
    def __init__(self, config_file='config.json'):
        """Fiyat takip sistemi başlatıcısı"""
        self.config = self.load_config(config_file)
        self.session = requests.Session()
        self.setup_session()
        
    def load_config(self, config_file):
        """Konfigürasyon dosyasını yükle"""
        default_config = {
            "netliste": {
                "email": "",
                "password": "",
                "login_url": "https://networkstedarik.netliste.com/login",
                "dashboard_url": "https://networkstedarik.netliste.com/purchaseDashboard"
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
    
    def login_netliste(self):
        """Netliste sitesine giriş yap"""
        logging.info("Netliste'ye giriş yapılıyor...")
        
        try:
            # Login sayfasını al
            login_page = self.session.get(self.config['netliste']['login_url'])
            soup = BeautifulSoup(login_page.content, 'html.parser')
            
            # CSRF token'ı bul (varsa)
            csrf_token = soup.find('input', {'name': 'csrf_token'})
            
            # Login verilerini hazırla
            login_data = {
                'email': self.config['netliste']['email'],
                'password': self.config['netliste']['password']
            }
            
            if csrf_token:
                login_data['csrf_token'] = csrf_token.get('value')
            
            # Login isteği gönder
            response = self.session.post(
                self.config['netliste']['login_url'],
                data=login_data,
                allow_redirects=True
            )
            
            if "dashboard" in response.url.lower() or response.status_code == 200:
                logging.info("Netliste girişi başarılı!")
                return True
            else:
                logging.error("Netliste girişi başarısız!")
                return False
                
        except Exception as e:
            logging.error(f"Netliste giriş hatası: {e}")
            return False
    
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
    
    def search_akakce_prices(self, product_name, max_sellers=5):
        """Akakçe'den ürün fiyatlarını ara"""
        logging.info(f"Akakçe'de aranıyor: {product_name}")
        
        self.random_delay()
        
        try:
            # Ürün adını URL-safe hale getir
            search_query = quote_plus(product_name)
            search_url = f"{self.config['akakce']['search_url']}{search_query}"
            
            response = self.session.get(search_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            prices = []
            
            # Fiyat listelerini bul
            price_elements = soup.find_all(['span', 'div'], class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['price', 'fiyat', 'fy_v8']
            ))
            
            for element in price_elements[:max_sellers]:
                try:
                    price_text = element.get_text(strip=True)
                    # Fiyat formatını temizle (₺, TL, virgül vs.)
                    price_clean = ''.join(c for c in price_text if c.isdigit() or c in '.,')
                    price_clean = price_clean.replace(',', '.')
                    
                    if price_clean:
                        price = float(price_clean)
                        if price > 0:
                            prices.append(price)
                            
                except (ValueError, AttributeError):
                    continue
            
            if len(prices) >= self.config['settings']['min_sellers']:
                avg_price = sum(prices) / len(prices)
                logging.info(f"{product_name}: {len(prices)} satıcı, ortalama: {avg_price:.2f}₺")
                return {
                    'prices': prices,
                    'average': avg_price,
                    'seller_count': len(prices)
                }
            else:
                logging.warning(f"{product_name}: Yeterli satıcı bulunamadı ({len(prices)})")
                return None
                
        except Exception as e:
            logging.error(f"Akakçe arama hatası ({product_name}): {e}")
            return None
    
    def analyze_price_anomalies(self, products):
        """Fiyat anomalilerini tespit et"""
        anomalies = []
        
        for product in products:
            akakce_data = self.search_akakce_prices(product['name'])
            
            if akakce_data:
                current_price = product['current_price']
                market_avg = akakce_data['average']
                
                # Fark yüzdesini hesapla
                price_difference = abs(current_price - market_avg) / market_avg
                
                if price_difference > self.config['settings']['price_threshold']:
                    anomaly_type = "YÜKSEK" if current_price > market_avg else "DÜŞÜK"
                    
                    anomalies.append({
                        'product_name': product['name'],
                        'our_price': current_price,
                        'market_average': market_avg,
                        'difference_percent': price_difference * 100,
                        'anomaly_type': anomaly_type,
                        'seller_count': akakce_data['seller_count'],
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    logging.warning(f"ANOMALI: {product['name']} - Bizim: {current_price}₺, Piyasa: {market_avg:.2f}₺")
        
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
    
    def run(self):
        """Ana çalışma fonksiyonu"""
        logging.info("=== Fiyat Takip Sistemi Başlıyor ===")
        
        # Netliste'ye giriş yap
        if not self.login_netliste():
            return False
        
        # Ürünleri al
        products = self.get_products_from_netliste()
        if not products:
            logging.error("Ürün bulunamadı!")
            return False
        
        # Anomali analizi
        anomalies = self.analyze_price_anomalies(products)
        
        # Sonuçları kaydet
        self.save_results(anomalies)
        
        # Email gönder (anomali varsa)
        if anomalies:
            self.send_email_alert(anomalies)
            logging.info(f"✅ {len(anomalies)} anomali tespit edildi ve email gönderildi!")
        else:
            logging.info("✅ Hiç anomali tespit edilmedi.")
        
        logging.info("=== İşlem Tamamlandı ===")
        return True

def main():
    """Manuel çalıştırma"""
    monitor = PriceMonitor()
    monitor.run()

if __name__ == "__main__":
    main()