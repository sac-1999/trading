import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor
from typing import List, Dict, Optional
import os
from dbpool import get_conn, release_conn
from psycopg2 import sql


class DBController:
    def __init__(self):
        self.conn = get_conn()
        self.cursor = self.conn.cursor()
        self.dict_cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        print("✓ Connected to PostgreSQL")

    def insert_candles(self, candles: List[List]):
        if not candles:
            print("No candles to insert")
            return
        
        insert_query = """
            INSERT INTO stock_ohlcv (
                timestamp, symbol, timeframe, open, high, low, close, volume
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (symbol, timeframe, timestamp) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume;
            """

        data = []
        for candle in candles:
            timestamp = candle['timestamp']
            data.append((
                timestamp,  # time
                str(candle['symbol']),
                str(candle['timeframe']),
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
    
    def close(self):
        """Clean up database connections"""
        self.cursor.close()
        release_conn(self.conn)
        print("\n✓ Database connection closed")

    
    def get_candles(self, symbol: str, timeframe: str) -> List[Dict]:
        """
        For '1m' -> read from base table stock_ohlcv filtered by timeframe.
        For other allowed TFs (e.g., '5m','15m','1h','1d') -> read from stock_ohlcv_<tf>.
        """
        if timeframe == '1m':
            query = """
                SELECT *
                FROM stock_ohlcv
                WHERE symbol = %s AND timeframe = %s
                ORDER BY timestamp ASC;
            """
            params = (symbol, timeframe)
            self.dict_cursor.execute(query, params)
        else:
            # Allow-list to avoid accidental or malicious table names
            allowed = {'5m', '15m', '1h', '1d'}
            if timeframe not in allowed:
                raise ValueError(f"Unsupported timeframe: {timeframe}")

            table_ident = sql.Identifier(f"stock_ohlcv_{timeframe}")
            query = sql.SQL("""
                SELECT *
                FROM {table}
                WHERE symbol = %s
                ORDER BY timestamp ASC;
            """).format(table=table_ident)

            self.dict_cursor.execute(query, (symbol,))

        results = self.dict_cursor.fetchall()
        return [
            {
                'timestamp': (row['timestamp'].isoformat()
                            if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp'])),
                'symbol': row['symbol'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(row['volume']),
            }
            for row in results
        ]
