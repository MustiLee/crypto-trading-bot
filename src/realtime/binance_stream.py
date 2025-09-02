import asyncio
import json
import websockets
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Callable, Optional
from loguru import logger
import numpy as np
from collections import deque


class BinanceKlineStream:
    """
    Real-time Binance WebSocket kline (candlestick) data stream
    """
    
    def __init__(self, symbol: str = "btcusdt", interval: str = "5m", buffer_size: int = 1000):
        self.symbol = symbol.lower()
        self.interval = interval
        self.buffer_size = buffer_size
        
        # Data buffer - stores recent klines
        self.klines_buffer = deque(maxlen=buffer_size)
        
        # WebSocket connection
        self.websocket = None
        self.is_running = False
        
        # Callbacks for real-time updates
        self.callbacks: List[Callable] = []
        
        # WebSocket URL
        self.ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@kline_{self.interval}"
        
        logger.info(f"Initialized Binance stream: {self.symbol.upper()} {self.interval}")
    
    def add_callback(self, callback: Callable[[Dict], None]):
        """Add callback function to be called on new kline data"""
        self.callbacks.append(callback)
        
    def remove_callback(self, callback: Callable):
        """Remove callback function"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def connect(self):
        """Connect to Binance WebSocket stream with auto-reconnection"""
        max_retries = 10
        retry_delay = 5  # seconds
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"🔌 Connecting to Binance WebSocket: {self.ws_url} (attempt {retry_count + 1})")
                self.websocket = await websockets.connect(self.ws_url)
                self.is_running = True
                logger.info("✅ Connected to Binance WebSocket successfully")
                
                # Reset retry count on successful connection
                retry_count = 0
                
                # Start listening for messages
                await self._listen()
                
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"🔌 WebSocket connection closed: {e}")
                retry_count += 1
                self.is_running = False
                self.websocket = None
                
                if retry_count < max_retries:
                    logger.info(f"🔄 Reconnecting in {retry_delay} seconds... (attempt {retry_count + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("❌ Max reconnection attempts exceeded")
                    raise
                    
            except Exception as e:
                logger.error(f"❌ WebSocket connection error: {e}")
                retry_count += 1
                self.is_running = False
                self.websocket = None
                
                if retry_count < max_retries:
                    logger.info(f"🔄 Retrying connection in {retry_delay} seconds... (attempt {retry_count + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("❌ Max connection attempts exceeded")
                    raise
    
    async def _listen(self):
        """Listen for incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                if not self.is_running:
                    break
                    
                try:
                    data = json.loads(message)
                    await self._handle_kline_data(data)
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    continue
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("🔌 WebSocket connection closed in listener")
            self.is_running = False
            # This will cause the connect() method to retry
            raise
        except Exception as e:
            logger.error(f"❌ Error in WebSocket listener: {e}")
            self.is_running = False
            # This will cause the connect() method to retry
            raise
    
    async def _handle_kline_data(self, data: Dict):
        """Process incoming kline data"""
        if 'k' not in data:
            return
            
        kline = data['k']
        
        # Extract kline information
        kline_data = {
            'timestamp': pd.to_datetime(kline['t'], unit='ms', utc=True),
            'open': float(kline['o']),
            'high': float(kline['h']),
            'low': float(kline['l']),
            'close': float(kline['c']),
            'volume': float(kline['v']),
            'is_closed': kline['x']  # Whether this kline is closed
        }
        
        # Always log live data for debugging
        if kline_data['is_closed']:
            logger.info(f"🔔 Closed kline: {kline_data['timestamp']} | Close: ${kline_data['close']:.2f}")
        else:
            logger.debug(f"📈 Live price: ${kline_data['close']:.2f}")
        
        # Process closed klines for signals
        if kline_data['is_closed']:
            # Add to buffer
            self.klines_buffer.append(kline_data)
            
            logger.debug(f"New kline: {kline_data['timestamp']} | "
                        f"OHLC: {kline_data['open']:.2f}/{kline_data['high']:.2f}/"
                        f"{kline_data['low']:.2f}/{kline_data['close']:.2f} | "
                        f"Vol: {kline_data['volume']:.2f}")
        
        # Notify callbacks for all data (live and closed)
        for callback in self.callbacks:
            try:
                await callback(kline_data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    def get_recent_klines_df(self, count: Optional[int] = None) -> pd.DataFrame:
        """Get recent klines as pandas DataFrame"""
        if not self.klines_buffer:
            return pd.DataFrame()
            
        # Get specified number of recent klines or all available
        recent_data = list(self.klines_buffer)
        if count:
            recent_data = recent_data[-count:]
            
        df = pd.DataFrame(recent_data)
        if not df.empty:
            df = df.set_index('timestamp')
            df = df.drop('is_closed', axis=1)  # Remove helper column
            
        return df
    
    def get_current_price(self) -> Optional[float]:
        """Get the most recent close price"""
        if not self.klines_buffer:
            return None
        return self.klines_buffer[-1]['close']
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        logger.info("Disconnecting from Binance WebSocket...")
        self.is_running = False
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            
        logger.info("Disconnected from Binance WebSocket")
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected and running"""
        return self.is_running and self.websocket is not None


class HistoricalDataInitializer:
    """
    Fetch initial historical data to populate the buffer before starting real-time stream
    """
    
    def __init__(self, symbol: str = "BTCUSDT", interval: str = "5m"):
        self.symbol = symbol
        self.interval = interval
    
    async def fetch_initial_data(self, limit: int = 500) -> pd.DataFrame:
        """Fetch initial historical klines from Binance REST API"""
        try:
            import aiohttp
            
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': self.symbol,
                'interval': self.interval,
                'limit': limit
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Convert to DataFrame
                        df = pd.DataFrame(data, columns=[
                            'timestamp', 'open', 'high', 'low', 'close', 'volume',
                            'close_time', 'quote_asset_volume', 'number_of_trades',
                            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                        ])
                        
                        # Keep only OHLCV columns
                        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                        
                        # Convert types
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                        for col in ['open', 'high', 'low', 'close', 'volume']:
                            df[col] = df[col].astype(float)
                        
                        df = df.set_index('timestamp')
                        
                        logger.info(f"Fetched {len(df)} historical klines for initialization")
                        return df
                    else:
                        logger.error(f"Failed to fetch historical data: {response.status}")
                        return pd.DataFrame()
                        
        except Exception as e:
            logger.error(f"Error fetching initial historical data: {e}")
            return pd.DataFrame()


# Example usage and testing
async def example_usage():
    """Example of how to use the BinanceKlineStream"""
    
    # Initialize stream
    stream = BinanceKlineStream(symbol="btcusdt", interval="5m")
    
    # Add callback to print new data
    async def on_new_kline(kline_data):
        print(f"New kline: {kline_data['timestamp']} | Close: {kline_data['close']:.2f}")
    
    stream.add_callback(on_new_kline)
    
    try:
        # Connect and start streaming
        await stream.connect()
    except KeyboardInterrupt:
        print("Stopping stream...")
    finally:
        await stream.disconnect()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())