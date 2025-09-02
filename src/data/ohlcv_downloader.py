import ccxt
import pandas as pd
import time
from datetime import datetime
from typing import Optional
from loguru import logger


def fetch_ohlcv(
    exchange: str,
    symbol: str,
    timeframe: str,
    limit: int = 1000,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> pd.DataFrame:
    exchange_class = getattr(ccxt, exchange.lower())
    client = exchange_class()
    
    retries = 0
    while retries <= max_retries:
        try:
            logger.info(f"Fetching {symbol} {timeframe} data from {exchange} (limit: {limit})")
            
            ohlcv = client.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                raise ValueError(f"No data returned for {symbol} {timeframe}")
            
            df = pd.DataFrame(
                ohlcv, 
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            
            df = df.astype({
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": float
            })
            
            logger.info(f"Successfully fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")
            return df
            
        except (ccxt.DDoSProtection, ccxt.RateLimitExceeded) as e:
            retries += 1
            if retries > max_retries:
                logger.error(f"Rate limit exceeded after {max_retries} retries: {e}")
                raise
            
            wait_time = retry_delay * (2 ** retries)
            logger.warning(f"Rate limited, waiting {wait_time:.1f}s before retry {retries}/{max_retries}")
            time.sleep(wait_time)
            
        except ccxt.NetworkError as e:
            retries += 1
            if retries > max_retries:
                logger.error(f"Network error after {max_retries} retries: {e}")
                raise
            
            wait_time = retry_delay * retries
            logger.warning(f"Network error, retrying in {wait_time:.1f}s ({retries}/{max_retries})")
            time.sleep(wait_time)
            
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
    
    raise RuntimeError(f"Failed to fetch data after {max_retries} retries")


def validate_symbol_timeframe(exchange: str, symbol: str, timeframe: str) -> None:
    try:
        exchange_class = getattr(ccxt, exchange.lower())
        client = exchange_class()
        client.load_markets()
        
        if symbol not in client.markets:
            available_symbols = list(client.markets.keys())[:10]
            raise ValueError(f"Symbol {symbol} not available on {exchange}. Available: {available_symbols}...")
        
        if timeframe not in client.timeframes:
            available_timeframes = list(client.timeframes.keys())
            raise ValueError(f"Timeframe {timeframe} not available on {exchange}. Available: {available_timeframes}")
            
        logger.debug(f"Validated {symbol} {timeframe} on {exchange}")
        
    except AttributeError:
        raise ValueError(f"Exchange {exchange} not supported")
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise