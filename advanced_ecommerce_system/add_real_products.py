#!/usr/bin/env python3
"""
Gerçek ürünleri sisteme ekleme scripti
Kendi ürünlerinizi buraya ekleyip Akakçe ile karşılaştırın
"""

import sys
import os
from datetime import datetime

# Proje dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database.models import init_database, get_db_session, Product

def add_real_products():
    """Gerçek ürünlerinizi buraya ekleyin"""
    
    # Veritabanını başlat
    init_database()
    session = get_db_session()
    
    # 🛍️ GERÇEK ÜRÜNLERİNİZİ BURAYA EKLEYİN
    # Akakçe'de arama yapabilmek için ürün adlarını doğru yazın
    
    real_products = [
        # Örnek - Bu satırları kendi ürünlerinizle değiştirin
        {
            'name': 'iPhone 15 128GB',  # Akakçe'de bu isimle arama yapılacak
            'brand': 'Apple',
            'category': 'Telefon',
            'subcategory': 'Akıllı Telefon',
            'our_price': 42000.00,  # Sizin satış fiyatınız
            'our_stock': 10,         # Stok miktarınız
            'our_sku': 'IP15-128',   # Ürün kodunuz
        },
        {
            'name': 'Samsung Galaxy S24 256GB',
            'brand': 'Samsung', 
            'category': 'Telefon',
            'subcategory': 'Akıllı Telefon',
            'our_price': 38000.00,
            'our_stock': 5,
            'our_sku': 'GS24-256',
        },
        {
            'name': 'MacBook Air M2 256GB',
            'brand': 'Apple',
            'category': 'Bilgisayar',
            'subcategory': 'Laptop',
            'our_price': 45000.00,
            'our_stock': 3,
            'our_sku': 'MBA-M2-256',
        },
        # Daha fazla ürün ekleyebilirsiniz...
    ]
    
    added_products = []
    
    for product_data in real_products:
        # Ürün zaten var mı kontrol et
        existing = session.query(Product).filter(
            Product.name == product_data['name']
        ).first()
        
        if existing:
            print(f"⚠️ Ürün zaten mevcut: {product_data['name']}")
            continue
            
        # Yeni ürün oluştur
        product = Product(
            name=product_data['name'],
            brand=product_data['brand'],
            category=product_data['category'],
            subcategory=product_data['subcategory'],
            our_price=product_data['our_price'],
            our_stock=product_data['our_stock'],
            our_sku=product_data['our_sku'],
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        session.add(product)
        session.flush()  # ID'yi al
        added_products.append({
            'id': product.id,
            'name': product.name,
            'price': product.our_price
        })
    
    session.commit()
    session.close()
    
    print(f"\n✅ {len(added_products)} gerçek ürün eklendi:")
    for product in added_products:
        print(f"   • ID:{product['id']} - {product['name']} - {product['price']} ₺")
    
    return added_products

def main():
    """Ana fonksiyon"""
    print("🛍️ Gerçek ürünler sisteme ekleniyor...")
    
    added_products = add_real_products()
    
    if added_products:
        print(f"\n🎉 Toplam {len(added_products)} ürün eklendi!")
        print("\n📊 Şimdi şunları yapabilirsiniz:")
        print("1. Web dashboard'u açın: http://127.0.0.1:5000")
        print("2. Ürün detay sayfasından 'Akakçe'den Veri Çek' butonuna tıklayın")
        print("3. Gerçek piyasa fiyatları ile karşılaştırma yapın")
        print("\n🔍 Anomali tespiti gerçek verilerle çalışacak!")
    else:
        print("\n⚠️ Hiç yeni ürün eklenmedi.")
        print("add_real_products.py dosyasını düzenleyip gerçek ürünlerinizi ekleyin.")

if __name__ == "__main__":
    main()