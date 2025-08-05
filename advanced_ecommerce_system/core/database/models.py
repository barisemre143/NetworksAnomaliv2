"""
E-Ticaret Fiyat Analiz Sistemi - Veritabanı Modelleri
SQLAlchemy ORM ile veritabanı şeması tanımları
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()

class Product(Base):
    """Ürün modeli"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(500), nullable=False)
    brand = Column(String(200))
    category = Column(String(200))
    subcategory = Column(String(200))
    description = Column(Text)
    image_url = Column(String(1000))
    our_sku = Column(String(100))
    our_price = Column(Float)
    our_stock = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    price_histories = relationship("PriceHistory", back_populates="product")
    market_prices = relationship("MarketPrice", back_populates="product")
    anomalies = relationship("PriceAnomaly", back_populates="product")
    predictions = relationship("PricePrediction", back_populates="product")

class MarketPrice(Base):
    """Piyasa fiyatları (Akakçe, Trendyol vs.)"""
    __tablename__ = 'market_prices'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    source = Column(String(100), nullable=False)  # 'akakce', 'trendyol', 'amazon'
    seller_name = Column(String(200))
    price = Column(Float, nullable=False)
    currency = Column(String(3), default='TRY')
    shipping_cost = Column(Float, default=0.0)
    is_in_stock = Column(Boolean, default=True)
    seller_rating = Column(Float)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    product = relationship("Product", back_populates="market_prices")

class PriceHistory(Base):
    """Fiyat geçmişi"""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    our_price = Column(Float)
    market_min_price = Column(Float)
    market_max_price = Column(Float)
    market_avg_price = Column(Float)
    market_median_price = Column(Float)
    competitor_count = Column(Integer, default=0)
    date = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    product = relationship("Product", back_populates="price_histories")

class PriceAnomaly(Base):
    """Fiyat anomalileri"""
    __tablename__ = 'price_anomalies'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    anomaly_type = Column(String(50))  # 'high_price', 'low_price', 'sudden_change'
    our_price = Column(Float)
    market_avg_price = Column(Float)
    deviation_percent = Column(Float)
    severity = Column(String(20))  # 'low', 'medium', 'high', 'critical'
    detected_at = Column(DateTime, default=datetime.utcnow)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    notes = Column(Text)
    
    # İlişkiler
    product = relationship("Product", back_populates="anomalies")

class PricePrediction(Base):
    """Fiyat tahminleri"""
    __tablename__ = 'price_predictions'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    model_name = Column(String(100))  # 'lstm', 'arima', 'random_forest'
    prediction_horizon = Column(Integer)  # Kaç gün sonrası için tahmin
    predicted_price = Column(Float)
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    actual_price = Column(Float)  # Gerçekleşen fiyat (sonradan güncellenir)
    accuracy_score = Column(Float)  # Tahmin doğruluğu
    
    # İlişkiler
    product = relationship("Product", back_populates="predictions")

class Competitor(Base):
    """Rakip firmalar"""
    __tablename__ = 'competitors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    website = Column(String(500))
    source = Column(String(100))  # Hangi platformda
    rating = Column(Float)
    total_products = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TrendAnalysis(Base):
    """Trend analizi sonuçları"""
    __tablename__ = 'trend_analysis'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    analysis_type = Column(String(50))  # 'seasonal', 'growth', 'decline'
    trend_direction = Column(String(20))  # 'up', 'down', 'stable'
    trend_strength = Column(Float)  # 0-1 arası
    seasonality_detected = Column(Boolean, default=False)
    cycle_length = Column(Integer)  # Sezonluk döngü uzunluğu (gün)
    analysis_period = Column(Integer)  # Analiz edilen dönem (gün)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # JSON veriler
    trend_data = Column(JSON)  # Detaylı trend verileri
    forecast_data = Column(JSON)  # Tahmin verileri

class Alert(Base):
    """Uyarı sistemi"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50))  # 'price_anomaly', 'trend_change', 'competitor_change'
    product_id = Column(Integer, ForeignKey('products.id'))
    title = Column(String(200))
    message = Column(Text)
    severity = Column(String(20))  # 'info', 'warning', 'error', 'critical'
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # JSON metadata
    alert_metadata = Column(JSON)

class ScrapingJob(Base):
    """Scraping işleri"""
    __tablename__ = 'scraping_jobs'
    
    id = Column(Integer, primary_key=True)
    job_uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    source = Column(String(100))  # 'akakce', 'trendyol'
    job_type = Column(String(50))  # 'full_scan', 'product_update', 'price_check'
    status = Column(String(20))  # 'pending', 'running', 'completed', 'failed'
    products_total = Column(Integer, default=0)
    products_scraped = Column(Integer, default=0)
    products_failed = Column(Integer, default=0)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    error_message = Column(Text)
    
    # JSON logs
    log_data = Column(JSON)

class UserSession(Base):
    """Kullanıcı oturumları (basit auth)"""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True)
    user_name = Column(String(100))
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

# Veritabanı bağlantısı ve session yönetimi
class DatabaseManager:
    def __init__(self, database_url="sqlite:///ecommerce_analytics.db"):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Tabloları oluştur"""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        """Veritabanı session'ı al"""
        return self.SessionLocal()
        
    def drop_tables(self):
        """Tabloları sil (sadece development için)"""
        Base.metadata.drop_all(bind=self.engine)

# Singleton pattern ile global database manager
_db_manager = None

def get_db_manager(database_url=None):
    global _db_manager
    if _db_manager is None:
        url = database_url or "sqlite:///ecommerce_analytics.db"
        _db_manager = DatabaseManager(url)
    return _db_manager

def get_db_session():
    """Kolay session erişimi"""
    db_manager = get_db_manager()
    return db_manager.get_session()

# Örnek kullanım ve yardımcı fonksiyonlar
def init_database():
    """Veritabanını başlat"""
    db_manager = get_db_manager()
    db_manager.create_tables()
    print("✅ Veritabanı tabloları oluşturuldu!")

if __name__ == "__main__":
    # Test amaçlı database oluşturma
    init_database()
    
    # Test verisi ekleme
    session = get_db_session()
    
    # Örnek ürün
    sample_product = Product(
        name="iPhone 15 128GB",
        brand="Apple",
        category="Telefon",
        subcategory="Akıllı Telefon",
        our_sku="APL-IP15-128",
        our_price=42000.0,
        our_stock=50
    )
    
    session.add(sample_product)
    session.commit()
    
    print("✅ Test verisi eklendi!")
    session.close()