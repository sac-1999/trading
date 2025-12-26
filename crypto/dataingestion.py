import requests
import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor
from datetime import datetime, timedelta
import time
from typing import List, Dict, Optional

# ============================================
# CONFIGURATION
# ============================================

DB_CONFIG = {
    'host': 'localhost',
    'database': 'crypto_db',
    'user': 'postgres',
    'password': 'ADMIN@123',
    'port': 5431
}

# Binance API Configuration
BINANCE_BASE_URL = "https://api.binance.com/api/v3"
SYMBOL = "BTCUSDT"
TIMEFRAMES = {
    '1m': '1m',
    '5m': '5m', 
    '15m': '15m',
    '1h': '1h',
    '4h': '4h',
    '1d': '1d'
}



class BTCDataLoader:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()
        self.dict_cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        print("✓ Connected to PostgreSQL")

    def insert_candles(self, candles: List[List]):
        """
        Bulk insert candles into database
        
        Binance kline format:
        [
            [
                1499040000000,      // Open time
                "0.01634000",       // Open
                "0.80000000",       // High
                "0.01575800",       // Low
                "0.01577100",       // Close
                "148976.11427815",  // Volume
                1499644799999,      // Close time
                "2434.19055334",    // Quote asset volume
                308,                // Number of trades
                "1756.87402397",    // Taker buy base asset volume
                "28.46694368",      // Taker buy quote asset volume
                "17928899.62484339" // Ignore
            ]
        ]
        """
        if not candles:
            print("No candles to insert")
            return
        
        insert_query = """
        INSERT INTO btc_ohlcv (
            time, open, high, low, close, volume
        ) VALUES (
            %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (time) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume
        """
        
        # Prepare data
        data = []
        for candle in candles:
            # timestamp = datetime.fromtimestamp(candle['time'] / 1000)
            timestamp = candle['time']
            data.append((
                timestamp,  # time
                float(candle['open']),  # open
                float(candle['high']),  # high
                float(candle['low']),  # low
                float(candle['close']),  # close
                float(candle['volume']),  # volume
            ))
        
        try:
            execute_batch(self.cursor, insert_query, data, page_size=1000)
            self.conn.commit()
            print(f"✓ Inserted {len(data)} candles into database")
        except Exception as e:
            self.conn.rollback()
            print(f"✗ Insert failed: {e}")
    
    def load_all_historical_data(self, years: int = 5):
        """
        Main method to load all historical data
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)
        
        print(f"\n{'='*70}")
        print(f"BTC HISTORICAL DATA LOADER")
        print(f"{'='*70}")
        print(f"Symbol: {SYMBOL}")
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print(f"Duration: {years} years")
        print(f"Timeframes: {list(TIMEFRAMES.keys())}")
        print(f"{'='*70}\n")
        
        total_candles = 0
        
        for tf_name, tf_code in TIMEFRAMES.items():
            try:
                # Download data
                candles = self.download_timeframe_data(
                    SYMBOL, 
                    tf_code, 
                    start_date, 
                    end_date
                )
                
                # Insert into database
                self.insert_candles(SYMBOL, tf_name, candles)
                
                total_candles += len(candles)
                
                # Small delay between timeframes
                time.sleep(1)
                
            except Exception as e:
                print(f"✗ Error processing {tf_name}: {e}")
                continue
        
        print(f"\n{'='*70}")
        print(f"✓ COMPLETED!")
        print(f"Total candles loaded: {total_candles:,}")
        print(f"{'='*70}\n")
    
    def close(self):
        """Clean up database connections"""
        self.cursor.close()
        self.conn.close()
        print("\n✓ Database connection closed")



    def get_candles(
        self,
        ) -> List[Dict]:
        """
        Get candles from database
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            timeframe: Candle timeframe (e.g., '1h')
            limit: Number of candles to return
            start_time: Optional start datetime
            end_time: Optional end datetime
        
        Returns:
            List of candle dictionaries
        """
        query = """
        SELECT 
            *
        FROM btc_ohlcv
        """
        params = []
        self.dict_cursor.execute(query, params)
        results = self.dict_cursor.fetchall()
        # return results
        # Convert to JSON-serializable format
        return [
            {
                'time': row['time'].isoformat(),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            }
            for row in results
        ]