#!/usr/bin/env python3
"""
Duplicate Anomali Temizleme Script'i
Her ürün için sadece en son anomaliyi bırakır, eskilerini çözümlenmiş olarak işaretler.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database.models import get_db_session, PriceAnomaly, Product

def clean_duplicate_anomalies():
    """Her ürün için duplicate anomalileri temizle"""
    session = get_db_session()
    
    try:
        print("🧹 Duplicate anomali temizleme başlıyor...")
        
        # Tüm açık anomalileri ürüne göre grupla
        all_anomalies = session.query(PriceAnomaly).filter(
            PriceAnomaly.is_resolved == False
        ).order_by(PriceAnomaly.product_id, PriceAnomaly.detected_at.desc()).all()
        
        # Ürün ID'lerine göre grupla
        product_anomalies = {}
        for anomaly in all_anomalies:
            if anomaly.product_id not in product_anomalies:
                product_anomalies[anomaly.product_id] = []
            product_anomalies[anomaly.product_id].append(anomaly)
        
        resolved_count = 0
        kept_count = 0
        
        # Her ürün için en son anomali dışındakileri çözümle
        for product_id, anomalies in product_anomalies.items():
            if len(anomalies) > 1:
                # İlk anomali (en son) hariç diğerlerini çözümle
                latest_anomaly = anomalies[0]  # En son (desc order)
                duplicate_anomalies = anomalies[1:]  # Eskiler
                
                # Ürün adını al
                product = session.query(Product).get(product_id)
                product_name = product.name if product else f"ID:{product_id}"
                
                print(f"📦 {product_name}: {len(duplicate_anomalies)} duplicate temizleniyor")
                
                # Duplicate'ları çözümlenmiş olarak işaretle
                for dup_anomaly in duplicate_anomalies:
                    dup_anomaly.is_resolved = True
                    dup_anomaly.resolved_at = datetime.now()
                    dup_anomaly.notes += f" | Otomatik temizleme ile çözümlendi - {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                    resolved_count += 1
                
                kept_count += 1
                print(f"  ✅ En son anomali korundu: {latest_anomaly.detected_at.strftime('%d.%m.%Y %H:%M')}")
                
            else:
                kept_count += 1
                print(f"📦 {session.query(Product).get(product_id).name if session.query(Product).get(product_id) else f'ID:{product_id}'}: Tek anomali, dokunulmadı")
        
        # Değişiklikleri kaydet
        session.commit()
        
        print(f"\n✅ Temizleme tamamlandı!")
        print(f"📊 Özet:")
        print(f"   🗑️  Çözümlenen duplicate'lar: {resolved_count}")
        print(f"   ✅ Korunan anomaliler: {kept_count}")
        print(f"   📦 İşlenen ürün sayısı: {len(product_anomalies)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Hata oluştu: {e}")
        session.rollback()
        return False
        
    finally:
        session.close()

def show_duplicate_stats():
    """Duplicate istatistiklerini göster"""
    session = get_db_session()
    
    try:
        print("📊 Mevcut anomali durumu:")
        
        # Toplam açık anomaliler
        total_open = session.query(PriceAnomaly).filter(
            PriceAnomaly.is_resolved == False
        ).count()
        
        # Ürün başına anomali sayıları
        from sqlalchemy import func
        product_counts = session.query(
            PriceAnomaly.product_id,
            func.count(PriceAnomaly.id).label('count'),
            Product.name
        ).join(Product, PriceAnomaly.product_id == Product.id).filter(
            PriceAnomaly.is_resolved == False
        ).group_by(PriceAnomaly.product_id, Product.name).having(
            func.count(PriceAnomaly.id) > 1
        ).order_by(func.count(PriceAnomaly.id).desc()).all()
        
        print(f"   🔢 Toplam açık anomali: {total_open}")
        print(f"   🔄 Duplicate olan ürün sayısı: {len(product_counts)}")
        
        if product_counts:
            print("   📋 Duplicate'ı olan ürünler:")
            for product_id, count, name in product_counts[:10]:  # İlk 10'u göster
                print(f"      - {name}: {count} anomali")
            
            if len(product_counts) > 10:
                print(f"      ... ve {len(product_counts) - 10} ürün daha")
        
    except Exception as e:
        print(f"❌ İstatistik hatası: {e}")
        
    finally:
        session.close()

if __name__ == "__main__":
    print("🧹 Duplicate Anomali Temizleme Aracı")
    print("=" * 50)
    
    # Önce durumu göster
    show_duplicate_stats()
    
    print("\n" + "=" * 50)
    response = input("Temizleme işlemini başlatmak istiyor musunuz? (y/N): ")
    
    if response.lower() in ['y', 'yes', 'evet', 'e']:
        clean_duplicate_anomalies()
        print("\n" + "=" * 50)
        print("🔄 Güncel durum:")
        show_duplicate_stats()
    else:
        print("İşlem iptal edildi.")