"""
Fiyat Takip Sistemi Zamanlayıcısı
Günde 1 kez belirli saatte çalışır
"""

import schedule
import time
import logging
from datetime import datetime
from price_monitor import PriceMonitor

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

class PriceScheduler:
    def __init__(self, run_time="09:00"):
        """
        Zamanlayıcı başlatıcısı
        run_time: Çalışma saati (HH:MM formatında)
        """
        self.run_time = run_time
        self.monitor = PriceMonitor()
        
    def run_price_check(self):
        """Fiyat kontrolü çalıştır"""
        try:
            logging.info(f"🕐 Zamanlanmış fiyat kontrolü başlıyor - {datetime.now()}")
            success = self.monitor.run()
            
            if success:
                logging.info("✅ Zamanlanmış kontrol başarıyla tamamlandı")
            else:
                logging.error("❌ Zamanlanmış kontrol başarısız")
                
        except Exception as e:
            logging.error(f"Zamanlayıcı hatası: {e}")
    
    def start_scheduler(self):
        """Zamanlayıcıyı başlat"""
        logging.info(f"🚀 Fiyat takip zamanlayıcısı başlatılıyor - Her gün {self.run_time}")
        
        # Günlük çalışma zamanını planla
        schedule.every().day.at(self.run_time).do(self.run_price_check)
        
        # Test çalışması (hemen 1 kez çalıştır)
        logging.info("🧪 Test çalışması yapılıyor...")
        self.run_price_check()
        
        # Sonsuz döngü
        logging.info("⏰ Zamanlayıcı aktif - Çalışma bekleniyor...")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Her dakika kontrol et
                
                # Her saat başı durum mesajı
                now = datetime.now()
                if now.minute == 0:
                    next_run = schedule.next_run()
                    logging.info(f"📅 Sistem aktif - Sonraki çalışma: {next_run}")
                    
            except KeyboardInterrupt:
                logging.info("⛔ Zamanlayıcı durduruldu (Ctrl+C)")
                break
            except Exception as e:
                logging.error(f"Zamanlayıcı döngü hatası: {e}")
                time.sleep(300)  # 5 dakika bekle ve devam et

def main():
    """Manuel başlatma"""
    import sys
    
    # Komut satırından saat alabilir
    run_time = "09:00"  # Varsayılan: Sabah 9
    
    if len(sys.argv) > 1:
        run_time = sys.argv[1]
        logging.info(f"Özel çalışma saati: {run_time}")
    
    scheduler = PriceScheduler(run_time=run_time)
    scheduler.start_scheduler()

if __name__ == "__main__":
    main()