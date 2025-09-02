"""
Database manager for trading system using PostgreSQL
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from loguru import logger
import psycopg2
from psycopg2.extras import RealDictCursor


class TradingDBManager:
    """
    Database manager for trading data using PostgreSQL
    """
    
    def __init__(self, db_url: str = None):
        # Use environment variable if available, otherwise use default
        self.db_url = db_url or os.getenv('DATABASE_URL', 'postgresql://localhost/trader_db')
        self.engine = create_engine(
            self.db_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            echo=False
        )
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"Initialized TradingDBManager with {self.db_url}")
    
    def get_connection(self):
        """Get raw psycopg2 connection for async operations"""
        # Parse connection info from DATABASE_URL or use environment variables
        host = os.getenv('POSTGRES_HOST', 'localhost')
        database = os.getenv('POSTGRES_DB', 'trader_db')
        user = os.getenv('POSTGRES_USER', None)
        password = os.getenv('POSTGRES_PASSWORD', None)
        port = os.getenv('POSTGRES_PORT', '5432')
        
        # Build connection parameters
        connection_params = {
            'host': host,
            'database': database,
            'port': port,
            'cursor_factory': RealDictCursor
        }
        
        # Add user/password if provided
        if user:
            connection_params['user'] = user
        if password:
            connection_params['password'] = password
        
        return psycopg2.connect(**connection_params)
    
    def save_market_data(self, symbol: str, timeframe: str, candles: List[Dict]) -> bool:
        """
        Save market data to PostgreSQL
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '5m', '15m')
            candles: List of candle dictionaries with OHLCV data
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    for candle in candles:
                        cursor.execute("""
                            INSERT INTO market_data (symbol, timeframe, timestamp, open, high, low, close, volume)
                            VALUES (%(symbol)s, %(timeframe)s, %(timestamp)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
                            ON CONFLICT (symbol, timeframe, timestamp) 
                            DO UPDATE SET 
                                open = EXCLUDED.open,
                                high = EXCLUDED.high,
                                low = EXCLUDED.low,
                                close = EXCLUDED.close,
                                volume = EXCLUDED.volume
                            RETURNING id;
                        """, {
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'timestamp': candle['timestamp'],
                            'open': candle['open'],
                            'high': candle['high'],
                            'low': candle['low'],
                            'close': candle['close'],
                            'volume': candle['volume']
                        })
                        result = cursor.fetchone()
                        candle['market_data_id'] = result['id']
                    
                    conn.commit()
                    logger.debug(f"Saved {len(candles)} {symbol} {timeframe} candles to database")
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving market data: {e}")
            return False
    
    def save_indicators(self, market_data_id: int, indicators: Dict) -> bool:
        """
        Save technical indicators to database
        Args:
            market_data_id: Reference to market_data record
            indicators: Dictionary of indicator values
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO indicators 
                        (market_data_id, rsi, macd, macd_signal, macd_histogram, bb_upper, bb_middle, bb_lower, atr)
                        VALUES (%(market_data_id)s, %(rsi)s, %(macd)s, %(macd_signal)s, %(macd_histogram)s, 
                               %(bb_upper)s, %(bb_middle)s, %(bb_lower)s, %(atr)s)
                        ON CONFLICT (market_data_id) 
                        DO UPDATE SET 
                            rsi = EXCLUDED.rsi,
                            macd = EXCLUDED.macd,
                            macd_signal = EXCLUDED.macd_signal,
                            macd_histogram = EXCLUDED.macd_histogram,
                            bb_upper = EXCLUDED.bb_upper,
                            bb_middle = EXCLUDED.bb_middle,
                            bb_lower = EXCLUDED.bb_lower,
                            atr = EXCLUDED.atr;
                    """, {
                        'market_data_id': market_data_id,
                        'rsi': indicators.get('rsi'),
                        'macd': indicators.get('macd'),
                        'macd_signal': indicators.get('macd_signal'),
                        'macd_histogram': indicators.get('macd_histogram'),
                        'bb_upper': indicators.get('bb_upper'),
                        'bb_middle': indicators.get('bb_middle'),
                        'bb_lower': indicators.get('bb_lower'),
                        'atr': indicators.get('atr')
                    })
                    
                    conn.commit()
                    logger.debug(f"Saved indicators for market_data_id {market_data_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving indicators: {e}")
            return False
    
    def save_signal(self, market_data_id: int, signal_type: str, 
                   signal_strength: float = None, strategy_name: str = "realistic1") -> bool:
        """
        Save trading signal to database
        Args:
            market_data_id: Reference to market_data record
            signal_type: 'BUY', 'SELL', or 'NEUTRAL'
            signal_strength: Optional signal strength (0-100)
            strategy_name: Strategy that generated the signal
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO signals (market_data_id, signal_type, signal_strength, strategy_name)
                        VALUES (%(market_data_id)s, %(signal_type)s, %(signal_strength)s, %(strategy_name)s);
                    """, {
                        'market_data_id': market_data_id,
                        'signal_type': signal_type,
                        'signal_strength': signal_strength,
                        'strategy_name': strategy_name
                    })
                    
                    conn.commit()
                    logger.debug(f"Saved {signal_type} signal for market_data_id {market_data_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            return False
    
    def get_market_data(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """
        Get market data from database as DataFrame
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            limit: Number of recent records to fetch
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT md.timestamp, md.open, md.high, md.low, md.close, md.volume,
                               i.rsi, i.macd, i.macd_signal, i.macd_histogram,
                               i.bb_upper, i.bb_middle, i.bb_lower, i.atr
                        FROM market_data md
                        LEFT JOIN indicators i ON md.id = i.market_data_id
                        WHERE md.symbol = %(symbol)s AND md.timeframe = %(timeframe)s
                        ORDER BY md.timestamp DESC
                        LIMIT %(limit)s;
                    """, {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'limit': limit
                    })
                    
                    rows = cursor.fetchall()
                    if not rows:
                        return pd.DataFrame()
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(rows)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.set_index('timestamp').sort_index()
                    
                    # Convert all numeric columns from Decimal to float
                    numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'rsi', 'macd', 'macd_signal', 
                                     'macd_histogram', 'bb_upper', 'bb_middle', 'bb_lower', 'atr']
                    for col in numeric_columns:
                        if col in df.columns and df[col].dtype == 'object':
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # Rename columns to match existing code
                    df = df.rename(columns={
                        'rsi': 'RSI',
                        'macd': 'MACD',
                        'macd_signal': 'MACD_SIGNAL',
                        'macd_histogram': 'MACD_HIST',
                        'bb_upper': 'BBU',
                        'bb_middle': 'BBM',
                        'bb_lower': 'BBL',
                        'atr': 'ATR'
                    })
                    
                    logger.debug(f"Retrieved {len(df)} rows of {symbol} {timeframe} data from database")
                    return df
                    
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return pd.DataFrame()
    
    def get_recent_signals(self, limit: int = 10) -> List[Dict]:
        """
        Get recent trading signals
        Args:
            limit: Number of recent signals to fetch
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT s.signal_type, s.signal_strength, s.strategy_name, s.created_at,
                               md.symbol, md.timeframe, md.timestamp, md.close,
                               i.rsi, i.macd
                        FROM signals s
                        JOIN market_data md ON s.market_data_id = md.id
                        LEFT JOIN indicators i ON md.id = i.market_data_id
                        ORDER BY s.created_at DESC
                        LIMIT %(limit)s;
                    """, {
                        'limit': limit
                    })
                    
                    rows = cursor.fetchall()
                    
                    signals = []
                    for row in rows:
                        signals.append({
                            'timestamp': row['created_at'].isoformat() if row['created_at'] else None,
                            'signal': row['signal_type'],
                            'price': float(row['close']) if row['close'] else None,
                            'symbol': row['symbol'],
                            'timeframe': row['timeframe'],
                            'rsi': float(row['rsi']) if row['rsi'] else None,
                            'macd': float(row['macd']) if row['macd'] else None,
                            'strategy': row['strategy_name']
                        })
                    
                    logger.debug(f"Retrieved {len(signals)} recent signals from database")
                    return signals
                    
        except Exception as e:
            logger.error(f"Error getting recent signals: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Clean up old data to keep database size manageable
        Args:
            days_to_keep: Number of days of data to keep
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM market_data 
                        WHERE timestamp < NOW() - INTERVAL '%s days';
                    """, (days_to_keep,))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    logger.info(f"Cleaned up {deleted_count} old market data records")
                    return True
                    
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1;")
                    result = cursor.fetchone()
                    logger.info("Database connection test successful")
                    return True
                    
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False