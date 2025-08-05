"""
Makine Öğrenmesi Veri Pipeline'ı
Fiyat verilerini ML modelleri için hazırlama ve işleme
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from datetime import datetime, timedelta
import logging
from typing import Tuple, List, Dict, Optional
import pickle
import os

# Logging yapılandırması
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataPipeline:
    """
    ML modelleri için veri hazırlama pipeline'ı
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.scalers = {}
        self.encoders = {}
        self.feature_columns = []
        self.target_column = None
        
        # Dizinleri kontrol et/oluştur
        os.makedirs(f"{data_dir}/processed", exist_ok=True)
        os.makedirs(f"{data_dir}/models", exist_ok=True)
        
    def load_price_data(self, product_id: Optional[int] = None) -> pd.DataFrame:
        """
        Veritabanından fiyat verilerini yükle
        """
        try:
            from core.database.models import get_db_session, Product, PriceHistory, MarketPrice
            
            session = get_db_session()
            
            # Base query
            query = session.query(
                PriceHistory.id,
                PriceHistory.product_id,
                PriceHistory.our_price,
                PriceHistory.market_min_price,
                PriceHistory.market_max_price,
                PriceHistory.market_avg_price,
                PriceHistory.market_median_price,
                PriceHistory.competitor_count,
                PriceHistory.date,
                Product.name.label('product_name'),
                Product.brand,
                Product.category,
                Product.subcategory
            ).join(Product, PriceHistory.product_id == Product.id)
            
            if product_id:
                query = query.filter(PriceHistory.product_id == product_id)
                
            # DataFrame'e çevir
            df = pd.read_sql(query.statement, session.bind)
            session.close()
            
            logger.info(f"Loaded {len(df)} price records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading price data: {e}")
            return pd.DataFrame()
    
    def create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Zaman bazlı özellikler oluştur
        """
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        # Temel zaman özellikleri
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day'] = df['date'].dt.day
        df['dayofweek'] = df['date'].dt.dayofweek
        df['quarter'] = df['date'].dt.quarter
        df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
        
        # Sezonsal özellikler
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        df['day_sin'] = np.sin(2 * np.pi * df['day'] / 31)
        df['day_cos'] = np.cos(2 * np.pi * df['day'] / 31)
        
        # Tatil günleri (basit Türkiye tatilleri)
        turkish_holidays = [
            (1, 1),   # Yılbaşı
            (4, 23),  # Ulusal Egemenlik
            (5, 1),   # İşçi Bayramı
            (5, 19),  # Gençlik ve Spor
            (8, 30),  # Zafer Bayramı
            (10, 29), # Cumhuriyet Bayramı
        ]
        
        df['is_holiday'] = df.apply(
            lambda row: (row['month'], row['day']) in turkish_holidays, axis=1
        ).astype(int)
        
        return df
    
    def create_lag_features(self, df: pd.DataFrame, target_col: str, lags: List[int] = [1, 3, 7, 14, 30]) -> pd.DataFrame:
        """
        Gecikmeli özellikler oluştur (lag features)
        """
        df = df.copy()
        df = df.sort_values(['product_id', 'date'])
        
        for lag in lags:
            df[f'{target_col}_lag_{lag}'] = df.groupby('product_id')[target_col].shift(lag)
        
        # Rolling window features
        for window in [3, 7, 14, 30]:
            df[f'{target_col}_rolling_mean_{window}'] = df.groupby('product_id')[target_col].rolling(window).mean().reset_index(0, drop=True)
            df[f'{target_col}_rolling_std_{window}'] = df.groupby('product_id')[target_col].rolling(window).std().reset_index(0, drop=True)
            df[f'{target_col}_rolling_min_{window}'] = df.groupby('product_id')[target_col].rolling(window).min().reset_index(0, drop=True)
            df[f'{target_col}_rolling_max_{window}'] = df.groupby('product_id')[target_col].rolling(window).max().reset_index(0, drop=True)
        
        return df
    
    def create_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fiyat bazlı özellikler oluştur
        """
        df = df.copy()
        
        # Fiyat oranları
        df['our_vs_avg_ratio'] = df['our_price'] / df['market_avg_price']
        df['our_vs_min_ratio'] = df['our_price'] / df['market_min_price']
        df['our_vs_max_ratio'] = df['our_price'] / df['market_max_price']
        
        # Piyasa spread
        df['market_spread'] = df['market_max_price'] - df['market_min_price']
        df['market_spread_pct'] = df['market_spread'] / df['market_avg_price']
        
        # Fiyat volatilite
        df = df.sort_values(['product_id', 'date'])
        for window in [3, 7, 14]:
            df[f'price_volatility_{window}'] = df.groupby('product_id')['our_price'].rolling(window).std().reset_index(0, drop=True)
        
        # Fiyat momentum
        df['price_change_1d'] = df.groupby('product_id')['our_price'].pct_change()
        df['price_change_7d'] = df.groupby('product_id')['our_price'].pct_change(periods=7)
        df['price_change_30d'] = df.groupby('product_id')['our_price'].pct_change(periods=30)
        
        return df
    
    def encode_categorical_features(self, df: pd.DataFrame, categorical_columns: List[str]) -> pd.DataFrame:
        """
        Kategorik değişkenleri encode et
        """
        df = df.copy()
        
        for col in categorical_columns:
            if col in df.columns:
                if col not in self.encoders:
                    self.encoders[col] = LabelEncoder()
                    df[f'{col}_encoded'] = self.encoders[col].fit_transform(df[col].fillna('unknown'))
                else:
                    # Handle unseen categories
                    df[f'{col}_temp'] = df[col].fillna('unknown')
                    mask = df[f'{col}_temp'].isin(self.encoders[col].classes_)
                    df[f'{col}_encoded'] = 0  # Default for unseen categories
                    df.loc[mask, f'{col}_encoded'] = self.encoders[col].transform(df.loc[mask, f'{col}_temp'])
                    df = df.drop(f'{col}_temp', axis=1)
        
        return df
    
    def handle_missing_values(self, df: pd.DataFrame, strategy: str = 'median') -> pd.DataFrame:
        """
        Eksik değerleri işle
        """
        df = df.copy()
        
        # Numeric columns için imputation
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        imputer = SimpleImputer(strategy=strategy)
        df[numeric_columns] = imputer.fit_transform(df[numeric_columns])
        
        return df
    
    def scale_features(self, df: pd.DataFrame, method: str = 'standard') -> pd.DataFrame:
        """
        Özellikleri normalize et
        """
        df = df.copy()
        
        # Numeric columns (excluding target and IDs)
        exclude_cols = ['id', 'product_id', 'date', 'our_price']  # Target korunur
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        numeric_columns = [col for col in numeric_columns if col not in exclude_cols]
        
        if method == 'standard':
            if 'scaler' not in self.scalers:
                self.scalers['scaler'] = StandardScaler()
                df[numeric_columns] = self.scalers['scaler'].fit_transform(df[numeric_columns])
            else:
                df[numeric_columns] = self.scalers['scaler'].transform(df[numeric_columns])
        elif method == 'minmax':
            if 'minmax_scaler' not in self.scalers:
                self.scalers['minmax_scaler'] = MinMaxScaler()
                df[numeric_columns] = self.scalers['minmax_scaler'].fit_transform(df[numeric_columns])
            else:
                df[numeric_columns] = self.scalers['minmax_scaler'].transform(df[numeric_columns])
        
        return df
    
    def prepare_ml_dataset(self, product_id: Optional[int] = None, 
                          target_col: str = 'our_price',
                          test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        ML için hazır dataset oluştur
        """
        logger.info(f"Preparing ML dataset for product_id: {product_id}")
        
        # 1. Veri yükleme
        df = self.load_price_data(product_id)
        if df.empty:
            raise ValueError("No data loaded")
        
        # 2. Zaman özellikleri
        df = self.create_time_features(df)
        
        # 3. Lag features
        df = self.create_lag_features(df, target_col)
        
        # 4. Fiyat özellikleri
        df = self.create_price_features(df)
        
        # 5. Kategorik encoding
        categorical_cols = ['brand', 'category', 'subcategory']
        df = self.encode_categorical_features(df, categorical_cols)
        
        # 6. Missing values
        df = self.handle_missing_values(df)
        
        # 7. Feature selection
        feature_cols = [col for col in df.columns if col not in [
            'id', 'product_id', 'date', 'product_name', 'our_price',
            'brand', 'category', 'subcategory'  # Original kategorik columns
        ]]
        
        self.feature_columns = feature_cols
        self.target_column = target_col
        
        # 8. Train-test split
        X = df[feature_cols].dropna()
        y = df.loc[X.index, target_col]
        
        # Zaman bazlı split (son %20 test için)
        df_sorted = df.loc[X.index].sort_values('date')
        split_idx = int(len(df_sorted) * (1 - test_size))
        
        train_idx = df_sorted.index[:split_idx]
        test_idx = df_sorted.index[split_idx:]
        
        X_train = X.loc[train_idx]
        X_test = X.loc[test_idx]
        y_train = y.loc[train_idx]
        y_test = y.loc[test_idx]
        
        # 9. Scaling
        X_train = self.scale_features(X_train)
        X_test = self.scale_features(X_test)
        
        logger.info(f"Dataset prepared: Train shape: {X_train.shape}, Test shape: {X_test.shape}")
        
        return X_train, X_test, y_train, y_test
    
    def save_pipeline(self, filepath: str):
        """
        Pipeline objesini kaydet
        """
        pipeline_data = {
            'scalers': self.scalers,
            'encoders': self.encoders,
            'feature_columns': self.feature_columns,
            'target_column': self.target_column
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(pipeline_data, f)
        
        logger.info(f"Pipeline saved to {filepath}")
    
    def load_pipeline(self, filepath: str):
        """
        Pipeline objesini yükle
        """
        with open(filepath, 'rb') as f:
            pipeline_data = pickle.load(f)
        
        self.scalers = pipeline_data['scalers']
        self.encoders = pipeline_data['encoders']
        self.feature_columns = pipeline_data['feature_columns']
        self.target_column = pipeline_data['target_column']
        
        logger.info(f"Pipeline loaded from {filepath}")

# Yardımcı fonksiyonlar
def create_sample_data():
    """
    Test için örnek veri oluştur
    """
    from core.database.models import get_db_session, Product, PriceHistory
    import random
    
    session = get_db_session()
    
    # Örnek ürün
    product = Product(
        name="iPhone 15 128GB",
        brand="Apple",
        category="Telefon",
        subcategory="Akıllı Telefon",
        our_price=42000.0
    )
    session.add(product)
    session.commit()
    
    # 90 günlük fiyat geçmişi
    base_date = datetime.now() - timedelta(days=90)
    
    for i in range(90):
        current_date = base_date + timedelta(days=i)
        
        # Rastgele fiyat dalgalanması
        our_price = 42000 + random.randint(-2000, 2000)
        market_avg = our_price + random.randint(-5000, 8000)
        market_min = market_avg - random.randint(1000, 3000)
        market_max = market_avg + random.randint(2000, 5000)
        
        history = PriceHistory(
            product_id=product.id,
            our_price=our_price,
            market_min_price=market_min,
            market_max_price=market_max,
            market_avg_price=market_avg,
            market_median_price=market_avg + random.randint(-500, 500),
            competitor_count=random.randint(5, 15),
            date=current_date
        )
        session.add(history)
    
    session.commit()
    session.close()
    
    print("✅ Sample data created!")

if __name__ == "__main__":
    # Test the pipeline
    from core.database.models import init_database
    
    # Initialize database
    init_database()
    
    # Create sample data
    create_sample_data()
    
    # Test pipeline
    pipeline = DataPipeline()
    
    try:
        X_train, X_test, y_train, y_test = pipeline.prepare_ml_dataset()
        print(f"✅ Pipeline test successful!")
        print(f"Training set: {X_train.shape}")
        print(f"Test set: {X_test.shape}")
        print(f"Features: {len(pipeline.feature_columns)}")
        
        # Save pipeline
        pipeline.save_pipeline("data/models/pipeline.pkl")
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")