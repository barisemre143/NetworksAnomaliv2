"""
Gelişmiş Trend Analizi ve Fiyat Tahmini
ARIMA, LSTM, Prophet modelleri ile fiyat trend analizi
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Time series analysis
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

# Machine Learning
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

# TensorFlow (optional)
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    HAS_TENSORFLOW = True
except ImportError:
    print("Warning: TensorFlow not available. LSTM models will be disabled.")
    HAS_TENSORFLOW = False

# Prophet for forecasting
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    print("Warning: Prophet not available. Install with: pip install prophet")

import logging
from typing import Dict, List, Tuple, Optional
import json
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """
    Gelişmiş trend analizi ve fiyat tahmini sınıfı
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.results = {}
        
    def load_price_data(self, product_id: int, days: int = 90) -> pd.DataFrame:
        """
        Belirli bir ürün için fiyat verilerini yükle
        """
        try:
            from core.database.models import get_db_session, PriceHistory, Product
            
            session = get_db_session()
            
            # Son N günün verilerini al
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            query = session.query(
                PriceHistory.date,
                PriceHistory.our_price,
                PriceHistory.market_avg_price,
                PriceHistory.market_min_price,
                PriceHistory.market_max_price,
                PriceHistory.competitor_count,
                Product.name.label('product_name')
            ).join(Product, PriceHistory.product_id == Product.id).filter(
                PriceHistory.product_id == product_id,
                PriceHistory.date >= start_date
            ).order_by(PriceHistory.date)
            
            df = pd.read_sql(query.statement, session.bind)
            session.close()
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                
            logger.info(f"Loaded {len(df)} price records for product {product_id}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading price data: {e}")
            return pd.DataFrame()
    
    def decompose_time_series(self, df: pd.DataFrame, price_col: str = 'our_price') -> Dict:
        """
        Zaman serisi decomposition analizi
        """
        if len(df) < 14:  # Minimum data requirement
            return {'error': 'Insufficient data for decomposition'}
        
        try:
            # Seasonal decomposition
            decomposition = seasonal_decompose(
                df[price_col].dropna(), 
                model='additive', 
                period=7  # Weekly seasonality
            )
            
            # Extract components
            trend = decomposition.trend.dropna()
            seasonal = decomposition.seasonal
            residual = decomposition.resid.dropna()
            
            # Calculate trend strength
            trend_strength = 1 - (residual.var() / (trend + residual).var())
            seasonal_strength = 1 - (residual.var() / (seasonal + residual).var())
            
            # Trend direction
            if len(trend) >= 2:
                trend_slope = (trend.iloc[-1] - trend.iloc[0]) / len(trend)
                if trend_slope > 0:
                    trend_direction = 'increasing'
                elif trend_slope < 0:
                    trend_direction = 'decreasing'
                else:
                    trend_direction = 'stable'
            else:
                trend_direction = 'unknown'
            
            return {
                'trend_strength': float(trend_strength),
                'seasonal_strength': float(seasonal_strength),
                'trend_direction': trend_direction,
                'trend_slope': float(trend_slope) if 'trend_slope' in locals() else 0,
                'components': {
                    'trend': trend.to_dict(),
                    'seasonal': seasonal.to_dict(),
                    'residual': residual.to_dict()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in time series decomposition: {e}")
            return {'error': str(e)}
    
    def detect_seasonality(self, df: pd.DataFrame, price_col: str = 'our_price') -> Dict:
        """
        Sezonluk desenleri tespit et
        """
        try:
            # Haftalık pattern
            df_copy = df.copy()
            df_copy['day_of_week'] = df_copy.index.dayofweek
            df_copy['hour'] = df_copy.index.hour
            
            # Günlük ortalamalar
            daily_pattern = df_copy.groupby('day_of_week')[price_col].mean()
            daily_std = df_copy.groupby('day_of_week')[price_col].std()
            
            # Sezonluk kuvveti hesapla
            seasonal_variance = daily_pattern.var()
            total_variance = df_copy[price_col].var()
            seasonality_strength = seasonal_variance / total_variance if total_variance > 0 else 0
            
            # Peak ve valley günleri
            peak_day = daily_pattern.idxmax()
            valley_day = daily_pattern.idxmin()
            
            days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            return {
                'seasonality_detected': seasonality_strength > 0.1,
                'seasonality_strength': float(seasonality_strength),
                'peak_day': days_of_week[peak_day],
                'valley_day': days_of_week[valley_day],
                'daily_pattern': {days_of_week[i]: float(daily_pattern.iloc[i]) for i in range(len(daily_pattern))},
                'daily_volatility': {days_of_week[i]: float(daily_std.iloc[i]) for i in range(len(daily_std))}
            }
            
        except Exception as e:
            logger.error(f"Error in seasonality detection: {e}")
            return {'error': str(e)}
    
    def fit_arima_model(self, df: pd.DataFrame, price_col: str = 'our_price') -> Dict:
        """
        ARIMA model fit et ve tahmin yap
        """
        try:
            data = df[price_col].dropna()
            
            if len(data) < 30:
                return {'error': 'Insufficient data for ARIMA model'}
            
            # Stationarity test
            adf_result = adfuller(data)
            is_stationary = adf_result[1] < 0.05
            
            # Auto ARIMA (basit heuristik)
            best_aic = float('inf')
            best_order = (1, 1, 1)
            
            for p in range(0, 3):
                for d in range(0, 2):
                    for q in range(0, 3):
                        try:
                            model = ARIMA(data, order=(p, d, q))
                            fitted_model = model.fit()
                            if fitted_model.aic < best_aic:
                                best_aic = fitted_model.aic
                                best_order = (p, d, q)
                        except:
                            continue
            
            # Best model fit
            model = ARIMA(data, order=best_order)
            fitted_model = model.fit()
            
            # 7 günlük tahmin
            forecast = fitted_model.forecast(steps=7)
            conf_int = fitted_model.get_forecast(steps=7).conf_int()
            
            # Model performance
            fitted_values = fitted_model.fittedvalues
            mae = mean_absolute_error(data[1:], fitted_values)  # Skip first value
            rmse = np.sqrt(mean_squared_error(data[1:], fitted_values))
            
            self.models['arima'] = fitted_model
            
            return {
                'model_order': best_order,
                'aic': float(fitted_model.aic),
                'bic': float(fitted_model.bic),
                'is_stationary': is_stationary,
                'mae': float(mae),
                'rmse': float(rmse),
                'forecast': forecast.tolist(),
                'forecast_conf_lower': conf_int.iloc[:, 0].tolist(),
                'forecast_conf_upper': conf_int.iloc[:, 1].tolist(),
                'forecast_dates': [(datetime.now() + timedelta(days=i+1)).isoformat() for i in range(7)]
            }
            
        except Exception as e:
            logger.error(f"Error in ARIMA modeling: {e}")
            return {'error': str(e)}
    
    def fit_lstm_model(self, df: pd.DataFrame, price_col: str = 'our_price', 
                      sequence_length: int = 10) -> Dict:
        """
        LSTM model ile fiyat tahmini
        """
        if not HAS_TENSORFLOW:
            return {'error': 'TensorFlow not available for LSTM model'}
            
        try:
            data = df[price_col].dropna().values.reshape(-1, 1)
            
            if len(data) < 50:
                return {'error': 'Insufficient data for LSTM model'}
            
            # Normalization
            scaler = MinMaxScaler()
            scaled_data = scaler.fit_transform(data)
            self.scalers['lstm'] = scaler
            
            # Create sequences
            X, y = [], []
            for i in range(sequence_length, len(scaled_data)):
                X.append(scaled_data[i-sequence_length:i, 0])
                y.append(scaled_data[i, 0])
            
            X, y = np.array(X), np.array(y)
            X = X.reshape((X.shape[0], X.shape[1], 1))
            
            # Train-test split
            split = int(0.8 * len(X))
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            
            # Build LSTM model
            model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(sequence_length, 1)),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(25),
                Dense(1)
            ])
            
            model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
            
            # Train model
            history = model.fit(
                X_train, y_train,
                batch_size=32,
                epochs=50,
                validation_split=0.1,
                verbose=0
            )
            
            # Predictions
            y_pred = model.predict(X_test)
            
            # Inverse transform
            y_test_actual = scaler.inverse_transform(y_test.reshape(-1, 1))
            y_pred_actual = scaler.inverse_transform(y_pred)
            
            # Metrics
            mae = mean_absolute_error(y_test_actual, y_pred_actual)
            rmse = np.sqrt(mean_squared_error(y_test_actual, y_pred_actual))
            
            # Future prediction
            last_sequence = scaled_data[-sequence_length:].reshape(1, sequence_length, 1)
            future_predictions = []
            
            for _ in range(7):  # 7 day forecast
                next_pred = model.predict(last_sequence, verbose=0)
                future_predictions.append(next_pred[0, 0])
                # Update sequence
                last_sequence = np.roll(last_sequence, -1, axis=1)
                last_sequence[0, -1, 0] = next_pred[0, 0]
            
            # Inverse transform future predictions
            future_predictions = np.array(future_predictions).reshape(-1, 1)
            future_predictions = scaler.inverse_transform(future_predictions)
            
            self.models['lstm'] = model
            
            return {
                'mae': float(mae),
                'rmse': float(rmse),
                'train_loss': float(np.min(history.history['loss'])),
                'val_loss': float(np.min(history.history['val_loss'])),
                'forecast': future_predictions.flatten().tolist(),
                'forecast_dates': [(datetime.now() + timedelta(days=i+1)).isoformat() for i in range(7)]
            }
            
        except Exception as e:
            logger.error(f"Error in LSTM modeling: {e}")
            return {'error': str(e)}
    
    def fit_prophet_model(self, df: pd.DataFrame, price_col: str = 'our_price') -> Dict:
        """
        Facebook Prophet ile fiyat tahmini
        """
        if not PROPHET_AVAILABLE:
            return {'error': 'Prophet not available'}
        
        try:
            # Prepare data for Prophet
            prophet_df = df.reset_index()
            prophet_df = prophet_df.rename(columns={'date': 'ds', price_col: 'y'})
            prophet_df = prophet_df[['ds', 'y']].dropna()
            
            if len(prophet_df) < 20:
                return {'error': 'Insufficient data for Prophet model'}
            
            # Create and fit model
            model = Prophet(
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=False,
                changepoint_prior_scale=0.05
            )
            
            model.fit(prophet_df)
            
            # Make future dataframe
            future = model.make_future_dataframe(periods=7)
            forecast = model.predict(future)
            
            # Calculate performance on historical data
            historical_pred = forecast[:-7]  # Exclude future predictions
            mae = mean_absolute_error(prophet_df['y'], historical_pred['yhat'])
            rmse = np.sqrt(mean_squared_error(prophet_df['y'], historical_pred['yhat']))
            
            # Extract future predictions
            future_forecast = forecast[-7:]
            
            self.models['prophet'] = model
            
            return {
                'mae': float(mae),
                'rmse': float(rmse),
                'forecast': future_forecast['yhat'].tolist(),
                'forecast_lower': future_forecast['yhat_lower'].tolist(),
                'forecast_upper': future_forecast['yhat_upper'].tolist(),
                'forecast_dates': future_forecast['ds'].dt.strftime('%Y-%m-%d').tolist(),
                'trend': future_forecast['trend'].tolist(),
                'seasonal': future_forecast['weekly'].tolist()
            }
            
        except Exception as e:
            logger.error(f"Error in Prophet modeling: {e}")
            return {'error': str(e)}
    
    def comprehensive_analysis(self, product_id: int, days: int = 90) -> Dict:
        """
        Kapsamlı trend analizi - tüm modelleri çalıştır
        """
        logger.info(f"Starting comprehensive analysis for product {product_id}")
        
        # Load data
        df = self.load_price_data(product_id, days)
        if df.empty:
            return {'error': 'No data available'}
        
        results = {
            'product_id': product_id,
            'analysis_date': datetime.now().isoformat(),
            'data_points': len(df),
            'date_range': {
                'start': df.index.min().isoformat(),
                'end': df.index.max().isoformat()
            }
        }
        
        # 1. Time series decomposition
        logger.info("Running time series decomposition...")
        results['decomposition'] = self.decompose_time_series(df)
        
        # 2. Seasonality detection
        logger.info("Detecting seasonality patterns...")
        results['seasonality'] = self.detect_seasonality(df)
        
        # 3. ARIMA model
        logger.info("Fitting ARIMA model...")
        results['arima'] = self.fit_arima_model(df)
        
        # 4. LSTM model
        logger.info("Training LSTM model...")
        results['lstm'] = self.fit_lstm_model(df)
        
        # 5. Prophet model
        if PROPHET_AVAILABLE:
            logger.info("Fitting Prophet model...")
            results['prophet'] = self.fit_prophet_model(df)
        
        # 6. Ensemble prediction
        results['ensemble'] = self.create_ensemble_forecast(results)
        
        # 7. Risk assessment
        results['risk_assessment'] = self.assess_price_risk(df)
        
        self.results[product_id] = results
        
        logger.info("Comprehensive analysis completed")
        return results
    
    def create_ensemble_forecast(self, results: Dict) -> Dict:
        """
        Ensemble tahmin oluştur (model ortalamas)
        """
        try:
            forecasts = []
            weights = []
            
            # ARIMA
            if 'arima' in results and 'forecast' in results['arima']:
                forecasts.append(np.array(results['arima']['forecast']))
                weights.append(1.0 / (results['arima']['rmse'] + 1e-6))
            
            # LSTM
            if 'lstm' in results and 'forecast' in results['lstm']:
                forecasts.append(np.array(results['lstm']['forecast']))
                weights.append(1.0 / (results['lstm']['rmse'] + 1e-6))
            
            # Prophet
            if 'prophet' in results and 'forecast' in results['prophet']:
                forecasts.append(np.array(results['prophet']['forecast']))
                weights.append(1.0 / (results['prophet']['rmse'] + 1e-6))
            
            if not forecasts:
                return {'error': 'No valid forecasts to ensemble'}
            
            # Weighted average
            weights = np.array(weights)
            weights = weights / weights.sum()
            
            ensemble_forecast = np.zeros(len(forecasts[0]))
            for i, forecast in enumerate(forecasts):
                ensemble_forecast += weights[i] * forecast
            
            return {
                'forecast': ensemble_forecast.tolist(),
                'model_weights': {
                    'arima': float(weights[0]) if len(weights) > 0 else 0,
                    'lstm': float(weights[1]) if len(weights) > 1 else 0,
                    'prophet': float(weights[2]) if len(weights) > 2 else 0
                },
                'forecast_dates': [(datetime.now() + timedelta(days=i+1)).isoformat() for i in range(7)]
            }
            
        except Exception as e:
            logger.error(f"Error in ensemble forecasting: {e}")
            return {'error': str(e)}
    
    def assess_price_risk(self, df: pd.DataFrame, price_col: str = 'our_price') -> Dict:
        """
        Fiyat riski değerlendirmesi
        """
        try:
            prices = df[price_col].dropna()
            
            # Volatility metrics
            returns = prices.pct_change().dropna()
            volatility = returns.std()
            
            # Value at Risk (VaR) - 95% confidence
            var_95 = np.percentile(returns, 5)
            
            # Maximum drawdown
            rolling_max = prices.expanding().max()
            drawdown = (prices - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # Price momentum
            momentum_7d = (prices.iloc[-1] - prices.iloc[-8]) / prices.iloc[-8] if len(prices) > 7 else 0
            momentum_30d = (prices.iloc[-1] - prices.iloc[-31]) / prices.iloc[-31] if len(prices) > 30 else 0
            
            # Risk level
            if volatility > 0.05:
                risk_level = 'high'
            elif volatility > 0.02:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            return {
                'volatility': float(volatility),
                'var_95': float(var_95),
                'max_drawdown': float(max_drawdown),
                'momentum_7d': float(momentum_7d),
                'momentum_30d': float(momentum_30d),
                'risk_level': risk_level,
                'current_price': float(prices.iloc[-1]),
                'price_range_30d': {
                    'min': float(prices.tail(30).min()),
                    'max': float(prices.tail(30).max()),
                    'mean': float(prices.tail(30).mean())
                }
            }
            
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            return {'error': str(e)}
    
    def save_analysis(self, product_id: int, filepath: str):
        """
        Analiz sonuçlarını kaydet
        """
        if product_id in self.results:
            with open(filepath, 'w') as f:
                json.dump(self.results[product_id], f, indent=2, default=str)
            logger.info(f"Analysis saved to {filepath}")
        else:
            logger.error(f"No analysis results found for product {product_id}")

# Test ve örnek kullanım
if __name__ == "__main__":
    from core.database.models import init_database
    from core.ml_models.data_pipeline import create_sample_data
    
    # Initialize
    init_database()
    create_sample_data()
    
    # Run analysis
    analyzer = TrendAnalyzer()
    results = analyzer.comprehensive_analysis(product_id=1, days=90)
    
    print("🚀 Trend Analysis Results:")
    print(f"✅ Data points: {results.get('data_points', 0)}")
    
    if 'arima' in results and 'forecast' in results['arima']:
        print(f"📈 ARIMA 7-day forecast: {results['arima']['forecast'][:3]}...")
    
    if 'lstm' in results and 'forecast' in results['lstm']:
        print(f"🧠 LSTM 7-day forecast: {results['lstm']['forecast'][:3]}...")
    
    if 'risk_assessment' in results:
        print(f"⚠️ Risk level: {results['risk_assessment']['risk_level']}")
    
    # Save results
    analyzer.save_analysis(1, "data/processed/trend_analysis_results.json")
    print("💾 Results saved!")