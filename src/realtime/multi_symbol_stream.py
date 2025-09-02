import asyncio
import json
import websockets
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Callable, Optional
from loguru import logger
import yaml
from pathlib import Path


class MultiSymbolBinanceStream:
    """
    Multi-symbol Binance WebSocket stream for BTC, ETH, XRP
    """
    
    def __init__(self, config_path: str = None, interval: str = "5m"):
        self.interval = interval
        self.symbols = {}
        self.websocket = None
        self.is_running = False
        
        # Load symbol configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "symbols.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Setup symbols from config
        for symbol_key, symbol_config in config['symbols'].items():
            self.symbols[symbol_key] = {
                'symbol': symbol_config['symbol'].lower(),
                'display_name': symbol_config['display_name'],
                'precision': symbol_config['precision'],
                'strategy': symbol_config['strategy']
            }
        
        # Callbacks for each symbol
        self.callbacks: Dict[str, List[Callable]] = {}
        for symbol_key in self.symbols.keys():
            self.callbacks[symbol_key] = []
        
        # Create WebSocket URL for multiple streams
        # Binance multi-stream format: wss://stream.binance.com:9443/stream?streams=stream1/stream2/stream3
        streams = [f"{self.symbols[sym]['symbol']}@kline_{self.interval}" 
                  for sym in self.symbols.keys()]
        streams_param = '/'.join(streams)
        self.ws_url = f"wss://stream.binance.com:9443/stream?streams={streams_param}"
        
        logger.info(f"Initialized multi-symbol Binance stream: {list(self.symbols.keys())} {self.interval}")
    
    def add_callback(self, symbol_key: str, callback: Callable[[str, Dict], None]):
        """Add callback function for specific symbol"""
        if symbol_key in self.callbacks:
            self.callbacks[symbol_key].append(callback)
        else:
            logger.warning(f"Unknown symbol: {symbol_key}")
    
    def remove_callback(self, symbol_key: str, callback: Callable):
        """Remove callback function for specific symbol"""
        if symbol_key in self.callbacks and callback in self.callbacks[symbol_key]:
            self.callbacks[symbol_key].remove(callback)
    
    async def connect(self):
        """Connect to Binance WebSocket stream with auto-reconnection"""
        max_retries = 10
        retry_delay = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Connecting to Binance multi-symbol WebSocket (attempt {retry_count + 1})...")
                self.websocket = await websockets.connect(self.ws_url)
                self.is_running = True
                retry_count = 0  # Reset on successful connection
                
                logger.success("✅ Connected to Binance multi-symbol WebSocket stream")
                
                async for message in self.websocket:
                    try:
                        data = json.loads(message)
                        await self._handle_kline_data(data)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, attempting to reconnect...")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, 60)  # Exponential backoff, max 60s
                else:
                    logger.error("Max reconnection attempts reached")
                    break
                    
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, 60)
                else:
                    logger.error("Max reconnection attempts reached")
                    break
        
        self.is_running = False
        logger.error("Failed to maintain WebSocket connection")
    
    async def _handle_kline_data(self, data: dict):
        """Process incoming kline data and notify callbacks"""
        try:
            if 'stream' not in data or 'data' not in data:
                return
                
            # Extract symbol from stream name
            stream_name = data['stream']
            symbol_lower = stream_name.split('@')[0]
            
            # Find symbol key
            symbol_key = None
            for key, config in self.symbols.items():
                if config['symbol'] == symbol_lower:
                    symbol_key = key
                    break
                    
            if not symbol_key:
                return
                
            kline_data = data['data']['k']
            
            # Parse kline data
            kline = {
                'symbol': kline_data['s'],
                'open_time': int(kline_data['t']),
                'close_time': int(kline_data['T']),
                'open': float(kline_data['o']),
                'high': float(kline_data['h']),
                'low': float(kline_data['l']),
                'close': float(kline_data['c']),
                'volume': float(kline_data['v']),
                'is_closed': kline_data['x'],  # Whether this kline is closed
                'timestamp': datetime.fromtimestamp(int(kline_data['t']) / 1000, tz=timezone.utc)
            }
            
            # Log price updates
            if kline['is_closed']:
                logger.info(f"🔔 Closed kline {symbol_key}: {kline['timestamp']} | Close: ${kline['close']}")
            else:
                logger.debug(f"📈 Live price {symbol_key}: ${kline['close']}")
            
            # Notify callbacks for this symbol
            for callback in self.callbacks[symbol_key]:
                try:
                    await callback(symbol_key, kline)
                except Exception as e:
                    logger.error(f"Error in callback for {symbol_key}: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling kline data: {e}")
    
    async def disconnect(self):
        """Close WebSocket connection"""
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from Binance WebSocket")
    
    def get_symbols(self) -> Dict[str, Dict]:
        """Get configured symbols"""
        return self.symbols.copy()


# Compatibility wrapper for single symbol usage
class BinanceKlineStream:
    """
    Backward compatible single symbol stream wrapper
    """
    
    def __init__(self, symbol: str = "btcusdt", interval: str = "5m", buffer_size: int = 1000):
        # Map common symbols to keys
        symbol_map = {
            'btcusdt': 'BTC',
            'ethusdt': 'ETH', 
            'xrpusdt': 'XRP'
        }
        
        self.symbol = symbol.lower()
        self.symbol_key = symbol_map.get(self.symbol, 'BTC')
        self.interval = interval
        self.multi_stream = MultiSymbolBinanceStream(interval=interval)
        self.callbacks = []
        
        logger.info(f"Initialized single-symbol stream wrapper: {symbol.upper()} -> {self.symbol_key}")
    
    def add_callback(self, callback: Callable[[Dict], None]):
        """Add callback for single symbol"""
        async def wrapper_callback(symbol_key: str, kline_data: dict):
            if symbol_key == self.symbol_key:
                await callback(kline_data)
        
        self.callbacks.append((callback, wrapper_callback))
        self.multi_stream.add_callback(self.symbol_key, wrapper_callback)
    
    def remove_callback(self, callback: Callable):
        """Remove callback"""
        for orig_callback, wrapper_callback in self.callbacks:
            if orig_callback == callback:
                self.multi_stream.remove_callback(self.symbol_key, wrapper_callback)
                self.callbacks.remove((orig_callback, wrapper_callback))
                break
    
    async def connect(self):
        """Connect to stream"""
        await self.multi_stream.connect()
    
    async def disconnect(self):
        """Disconnect from stream"""
        await self.multi_stream.disconnect()