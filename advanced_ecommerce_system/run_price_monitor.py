#!/usr/bin/env python3
"""
Networks Price Monitor Runner
Advanced E-commerce System içinden price monitoring çalıştırma scripti
"""

import sys
import os

# Add core directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

from price_monitor import PriceMonitor

def main():
    """Ana çalıştırma fonksiyonu"""
    print("=== Networks Advanced E-commerce Price Monitoring ===")
    
    try:
        # Price monitor oluştur ve çalıştır
        monitor = PriceMonitor()
        success = monitor.run(max_products=10)
        
        if success:
            print("✅ Price monitoring successfully completed!")
        else:
            print("❌ Price monitoring failed!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()