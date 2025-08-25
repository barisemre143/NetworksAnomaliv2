"""
Networks API ile veritabanını senkronize etme modülü
Networks API'den gelen ürünleri SQLite veritabanına aktarır
"""

import requests
import json
from datetime import datetime
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database.models import get_db_session, Product

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworksAPISyncer:
    def __init__(self, config_file='../config.json'):
        """Networks API sync'i başlat"""
        self.config = self.load_config(config_file)
        self.session = requests.Session()
    
    def load_config(self, config_file):
        """Konfigürasyonu yükle"""
        config_path = os.path.join(os.path.dirname(__file__), config_file)
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.error(f"Config dosyası bulunamadı: {config_path}")
            return None
    
    def fetch_networks_products(self):
        """Networks API'den ürün listesini al"""
        logger.info("Networks API'den ürünler çekiliyor...")
        
        try:
            if not self.config or 'networks_api' not in self.config:
                logger.error("Networks API konfigürasyonu bulunamadı!")
                return []
            
            api_config = self.config['networks_api']
            auth = (api_config['username'], api_config['password'])
            
            response = self.session.get(api_config['api_url'], auth=auth, timeout=30)
            
            if response.status_code == 200:
                products_data = response.json()
                logger.info(f"Networks API'den {len(products_data)} ürün alındı")
                return products_data
            else:
                logger.error(f"Networks API hatası: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Networks API bağlantı hatası: {e}")
            return []
    
    def sync_products_to_database(self):
        """Networks API verilerini veritabanına sync et"""
        logger.info("Networks API ile veritabanı sync'i başlıyor...")
        
        # Networks API'den ürünleri al
        networks_products = self.fetch_networks_products()
        if not networks_products:
            logger.error("Networks API'den ürün alınamadı!")
            return False
        
        # Veritabanı session'ı aç
        session = get_db_session()
        
        try:
            # Önce mevcut Networks ürünlerini temizle (is_active=False yap)
            logger.info("Mevcut Networks ürünleri pasif yapılıyor...")
            session.query(Product).filter(
                Product.our_sku.like('HBCV%')
            ).update({Product.is_active: False})
            
            sync_count = 0
            update_count = 0
            
            # Networks API'den gelen her ürünü işle
            for api_product in networks_products:
                try:
                    # Fiyatı kontrol et
                    sell_price = float(api_product.get('sellPrice', 0))
                    if sell_price <= 0:
                        continue
                    
                    # Mevcut ürünü stock code ile bul
                    existing_product = session.query(Product).filter(
                        Product.our_sku == api_product['stockCode']
                    ).first()
                    
                    if existing_product:
                        # Mevcut ürünü güncelle
                        existing_product.name = api_product['productName']
                        existing_product.brand = api_product['brand']
                        existing_product.category = api_product['productCategoryName']
                        existing_product.our_price = sell_price
                        existing_product.our_stock = int(api_product.get('stockQuantity', 0))
                        existing_product.is_active = True
                        existing_product.updated_at = datetime.utcnow()
                        
                        # Açıklama alanına full name ekle
                        existing_product.description = api_product['productFullName']
                        
                        update_count += 1
                        logger.debug(f"Güncellendi: {api_product['productName']}")
                        
                    else:
                        # Yeni ürün oluştur
                        new_product = Product(
                            name=api_product['productName'],
                            brand=api_product['brand'],
                            category=api_product['productCategoryName'],
                            description=api_product['productFullName'],
                            our_sku=api_product['stockCode'],
                            our_price=sell_price,
                            our_stock=int(api_product.get('stockQuantity', 0)),
                            is_active=True,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        
                        session.add(new_product)
                        sync_count += 1
                        logger.debug(f"Eklendi: {api_product['productName']}")
                
                except Exception as product_error:
                    logger.warning(f"Ürün işlenemedi ({api_product.get('productName', 'Unknown')}): {product_error}")
                    continue
            
            # Değişiklikleri kaydet
            session.commit()
            
            logger.info(f"✅ Sync tamamlandı: {sync_count} yeni, {update_count} güncelleme")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Database sync hatası: {e}")
            return False
            
        finally:
            session.close()
    
    def get_sync_stats(self):
        """Sync istatistiklerini al"""
        session = get_db_session()
        
        try:
            total_products = session.query(Product).count()
            active_products = session.query(Product).filter(Product.is_active == True).count()
            networks_products = session.query(Product).filter(
                Product.our_sku.like('HBCV%'),
                Product.is_active == True
            ).count()
            
            return {
                'total_products': total_products,
                'active_products': active_products,
                'networks_products': networks_products,
                'sync_timestamp': datetime.now().isoformat()
            }
            
        finally:
            session.close()

def main():
    """Manuel sync çalıştırma"""
    logger.info("=== Networks API Manual Sync ===")
    
    syncer = NetworksAPISyncer()
    success = syncer.sync_products_to_database()
    
    if success:
        stats = syncer.get_sync_stats()
        logger.info(f"✅ Sync başarılı! Stats: {stats}")
    else:
        logger.error("❌ Sync başarısız!")

if __name__ == "__main__":
    main()