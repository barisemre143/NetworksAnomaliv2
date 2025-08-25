"""
E-Ticaret Fiyat Analiz Sistemi - Flask Web Dashboard
Modern, responsive web arayüzü ile fiyat takibi ve analiz
"""

from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_cors import CORS
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.utils
import json
from datetime import datetime, timedelta
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database.models import get_db_session, Product, PriceHistory, MarketPrice, PriceAnomaly
from analysis.trend_analysis.trend_analyzer import TrendAnalyzer
from scrapers.akakce_scraper import AkakceScraper
from core.sync_networks_api import NetworksAPISyncer

# Flask app setup
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
CORS(app)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global objects
trend_analyzer = TrendAnalyzer()
akakce_scraper = AkakceScraper()

# Helper functions
def get_all_products():
    """Tüm aktif ürünleri getir"""
    session = get_db_session()
    products = session.query(Product).filter(Product.is_active == True).all()
    session.close()
    return products

def get_product_price_history(product_id, days=30):
    """Ürün fiyat geçmişini getir"""
    session = get_db_session()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    history = session.query(PriceHistory).filter(
        PriceHistory.product_id == product_id,
        PriceHistory.date >= start_date
    ).order_by(PriceHistory.date).all()
    
    session.close()
    return history

def get_recent_anomalies(limit=10):
    """Son anomalileri getir"""
    session = get_db_session()
    
    anomalies = session.query(
        PriceAnomaly,
        Product.name.label('product_name')
    ).join(Product, PriceAnomaly.product_id == Product.id).filter(
        PriceAnomaly.is_resolved == False
    ).order_by(PriceAnomaly.detected_at.desc()).limit(limit).all()
    
    session.close()
    return anomalies

def create_price_chart(product_id, days=30):
    """Fiyat grafiği oluştur"""
    history = get_product_price_history(product_id, days)
    
    if not history:
        return json.dumps({})
    
    dates = [h.date for h in history]
    our_prices = [h.our_price for h in history]
    market_avg_prices = [h.market_avg_price for h in history]
    market_min_prices = [h.market_min_price for h in history]
    market_max_prices = [h.market_max_price for h in history]
    
    # Create Plotly chart
    fig = go.Figure()
    
    # Our price line
    fig.add_trace(go.Scatter(
        x=dates,
        y=our_prices,
        name='Bizim Fiyat',
        line=dict(color='#2E86AB', width=3),
        mode='lines+markers'
    ))
    
    # Market average
    fig.add_trace(go.Scatter(
        x=dates,
        y=market_avg_prices,
        name='Piyasa Ortalaması',
        line=dict(color='#A23B72', width=2),
        mode='lines'
    ))
    
    # Market range (fill between min and max)
    fig.add_trace(go.Scatter(
        x=dates + dates[::-1],
        y=market_max_prices + market_min_prices[::-1],
        fill='toself',
        fillcolor='rgba(162, 59, 114, 0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        name='Piyasa Aralığı'
    ))
    
    # Layout
    fig.update_layout(
        title='Fiyat Trendi',
        xaxis_title='Tarih',
        yaxis_title='Fiyat (₺)',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# Routes
@app.route('/')
def dashboard():
    """Ana dashboard sayfası"""
    try:
        logger.info("Dashboard function started")
        
        # Get basic stats
        session = get_db_session()
        logger.info("Database session obtained")
        
        total_products = session.query(Product).filter(Product.is_active == True).count()
        logger.info(f"Total products: {total_products}")
        
        total_anomalies = session.query(PriceAnomaly).filter(PriceAnomaly.is_resolved == False).count()
        logger.info(f"Total anomalies: {total_anomalies}")
        
        # Recent activity
        recent_updates = session.query(PriceHistory).order_by(PriceHistory.date.desc()).limit(5).all()
        logger.info(f"Recent updates count: {len(recent_updates)}")
        
        session.close()
        logger.info("Database session closed")
        
        # Get products for dropdown
        products = get_all_products()
        logger.info(f"Products for dropdown: {len(products)}")
        
        # Get recent anomalies
        anomalies = get_recent_anomalies(5)
        logger.info(f"Recent anomalies count: {len(anomalies)}")
        
        logger.info("About to render template")
        # Use debug template to isolate the issue
        return render_template('dashboard.html',
                             total_products=total_products,
                             total_anomalies=total_anomalies,
                             products=products,
                             recent_updates=recent_updates,
                             anomalies=anomalies)
    
    except Exception as e:
        import traceback
        logger.error(f"Dashboard error: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return render_template('error.html', error=str(e))

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Ürün detay sayfası"""
    try:
        session = get_db_session()
        product = session.query(Product).get(product_id)
        session.close()
        
        if not product:
            flash('Ürün bulunamadı!', 'error')
            return redirect(url_for('dashboard'))
        
        # Get price history
        history = get_product_price_history(product_id, 30)
        
        # Create chart
        chart_json = create_price_chart(product_id, 30)
        
        # Get anomalies for this product
        session = get_db_session()
        anomalies = session.query(PriceAnomaly).filter(
            PriceAnomaly.product_id == product_id
        ).order_by(PriceAnomaly.detected_at.desc()).limit(10).all()
        session.close()
        
        return render_template('product_detail.html',
                             product=product,
                             history=history,
                             chart_json=chart_json,
                             anomalies=anomalies)
    
    except Exception as e:
        logger.error(f"Product detail error: {e}")
        flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/analytics')
def analytics():
    """Analitik sayfası"""
    try:
        products = get_all_products()
        return render_template('analytics.html', products=products)
    
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return render_template('error.html', error=str(e))

@app.route('/anomalies')
def anomalies():
    """Anomali sayfası"""
    try:
        # Get all anomalies
        session = get_db_session()
        
        anomalies = session.query(
            PriceAnomaly,
            Product.name.label('product_name')
        ).join(Product, PriceAnomaly.product_id == Product.id).order_by(
            PriceAnomaly.detected_at.desc()
        ).limit(50).all()
        
        session.close()
        
        return render_template('anomalies.html', anomalies=anomalies)
    
    except Exception as e:
        logger.error(f"Anomalies error: {e}")
        return render_template('error.html', error=str(e))

# API Routes
@app.route('/api/products')
def api_products():
    """Ürün listesi API"""
    try:
        products = get_all_products()
        return jsonify([{
            'id': p.id,
            'name': p.name,
            'brand': p.brand,
            'category': p.category,
            'our_price': p.our_price,
            'our_stock': p.our_stock
        } for p in products])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/product/<int:product_id>/chart')
def api_product_chart(product_id):
    """Ürün fiyat grafiği API"""
    try:
        days = request.args.get('days', 30, type=int)
        chart_json = create_price_chart(product_id, days)
        return chart_json
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/product/<int:product_id>/trend-analysis')
def api_trend_analysis(product_id):
    """Trend analizi API"""
    try:
        days = request.args.get('days', 90, type=int)
        
        # Run comprehensive analysis
        results = trend_analyzer.comprehensive_analysis(product_id, days)
        
        # Convert any Timestamp objects to strings for JSON serialization
        def convert_timestamps(obj):
            if isinstance(obj, dict):
                # Handle both keys and values that might be Timestamps
                new_dict = {}
                for k, v in obj.items():
                    # Convert key if it's a Timestamp
                    if hasattr(k, 'isoformat'):
                        new_key = k.isoformat()
                    else:
                        new_key = k
                    # Convert value recursively
                    new_dict[new_key] = convert_timestamps(v)
                return new_dict
            elif isinstance(obj, list):
                return [convert_timestamps(item) for item in obj]
            elif hasattr(obj, 'isoformat'):  # datetime/Timestamp objects
                return obj.isoformat()
            elif hasattr(obj, 'item'):  # numpy scalars
                return obj.item()
            elif isinstance(obj, (np.integer, np.floating)):  # numpy types
                return obj.item()
            else:
                return obj
        
        # Clean results for JSON serialization
        clean_results = convert_timestamps(results)
        
        return jsonify(clean_results)
    
    except Exception as e:
        logger.error(f"Trend analysis API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    """Dashboard istatistikleri API"""
    try:
        session = get_db_session()
        
        # Basic counts
        total_products = session.query(Product).filter(Product.is_active == True).count()
        total_anomalies = session.query(PriceAnomaly).filter(PriceAnomaly.is_resolved == False).count()
        
        # Today's activity
        today = datetime.now().date()
        today_updates = session.query(PriceHistory).filter(
            PriceHistory.date >= today
        ).count()
        
        # Price distribution
        avg_our_price = session.query(Product.our_price).filter(
            Product.is_active == True,
            Product.our_price > 0
        ).all()
        
        session.close()
        
        # Calculate price stats
        prices = [p[0] for p in avg_our_price if p[0]]
        price_stats = {
            'min': min(prices) if prices else 0,
            'max': max(prices) if prices else 0,
            'avg': sum(prices) / len(prices) if prices else 0
        }
        
        return jsonify({
            'total_products': total_products,
            'total_anomalies': total_anomalies,
            'today_updates': today_updates,
            'price_stats': price_stats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/anomalies/resolve/<int:anomaly_id>', methods=['POST'])
def api_resolve_anomaly(anomaly_id):
    """Anomali çözümleme API"""
    try:
        session = get_db_session()
        
        anomaly = session.query(PriceAnomaly).get(anomaly_id)
        if not anomaly:
            return jsonify({'error': 'Anomaly not found'}), 404
        
        anomaly.is_resolved = True
        anomaly.resolved_at = datetime.now()
        anomaly.notes = request.json.get('notes', '')
        
        session.commit()
        session.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraping/akakce/single/<int:product_id>', methods=['POST'])
def api_scrape_single_product(product_id):
    """Tek ürün için Akakçe scraping"""
    try:
        session = get_db_session()
        product = session.query(Product).get(product_id)
        session.close()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        logger.info(f"Tek ürün scraping başlatıldı: {product.name}")
        
        # Akakçe'den veri çek
        scraped_data = akakce_scraper.scrape_product_data(product.name)
        
        if not scraped_data:
            return jsonify({
                'success': False,
                'message': 'Ürün Akakçe\'de bulunamadı'
            })
        
        # Veritabanına kaydet
        saved = akakce_scraper.save_to_database(product_id, scraped_data)
        
        if not saved:
            return jsonify({
                'success': False,
                'message': 'Veritabanı kayıt hatası'
            })
        
        # Anomali tespiti
        anomalies = akakce_scraper.detect_price_anomalies(
            product_id, 
            product.our_price, 
            scraped_data
        )
        
        return jsonify({
            'success': True,
            'message': f'{scraped_data["price_count"]} fiyat çekildi',
            'data': {
                'product_name': scraped_data['product_name'],
                'min_price': scraped_data['min_price'],
                'max_price': scraped_data['max_price'],
                'avg_price': scraped_data['avg_price'],
                'price_count': scraped_data['price_count'],
                'our_price': product.our_price,
                'anomalies_detected': len(anomalies)
            }
        })
    
    except Exception as e:
        logger.error(f"Single scraping error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraping/akakce/all', methods=['POST'])
def api_scrape_all_products():
    """Tüm ürünler için Akakçe scraping"""
    try:
        logger.info("Toplu Akakçe scraping başlatıldı")
        
        # Arka planda çalışsın diye thread kullanmadan basit çözüm
        result = akakce_scraper.scrape_all_products()
        
        if not result:
            return jsonify({
                'success': False,
                'message': 'Scraping başarısız'
            })
        
        return jsonify({
            'success': True,
            'message': f'{result["scraped_products"]}/{result["total_products"]} ürün işlendi',
            'data': result
        })
    
    except Exception as e:
        logger.error(f"Bulk scraping error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraping/status')
def api_scraping_status():
    """Scraping durumu API"""
    try:
        session = get_db_session()
        
        # Son scraping zamanları
        latest_scraping = session.query(MarketPrice).filter(
            MarketPrice.source == 'akakce'
        ).order_by(MarketPrice.scraped_at.desc()).first()
        
        # Toplam Akakçe verileri
        total_akakce_data = session.query(MarketPrice).filter(
            MarketPrice.source == 'akakce'
        ).count()
        
        # Bugünkü scraping sayısı
        today = datetime.now().date()
        today_scraping = session.query(MarketPrice).filter(
            MarketPrice.source == 'akakce',
            MarketPrice.scraped_at >= today
        ).count()
        
        session.close()
        
        return jsonify({
            'total_akakce_data': total_akakce_data,
            'today_scraping': today_scraping,
            'last_scraping': latest_scraping.scraped_at.isoformat() if latest_scraping else None,
            'scraper_active': True
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.route('/api/sync-networks', methods=['POST'])
def sync_networks_api():
    """Networks API ile veritabanını senkronize et"""
    try:
        logger.info("Networks API sync başlatıldı...")
        
        syncer = NetworksAPISyncer()
        success = syncer.sync_products_to_database()
        
        if success:
            stats = syncer.get_sync_stats()
            logger.info(f"Networks API sync başarılı: {stats}")
            
            return jsonify({
                'success': True,
                'message': 'Networks API sync tamamlandı!',
                'stats': stats
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Networks API sync başarısız!'
            }), 500
            
    except Exception as e:
        logger.error(f"Networks API sync hatası: {e}")
        return jsonify({
            'success': False,
            'message': f'Sync hatası: {str(e)}'
        }), 500

@app.route('/api/networks-stats')
def networks_stats():
    """Networks API sync istatistiklerini al"""
    try:
        syncer = NetworksAPISyncer()
        stats = syncer.get_sync_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Stats hatası: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error="Sayfa bulunamadı"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error="Sunucu hatası"), 500

# Development server
if __name__ == '__main__':
    # Initialize database if needed
    try:
        from core.database.models import init_database
        init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
    
    # Run development server
    app.run(debug=True, host='0.0.0.0', port=5000)