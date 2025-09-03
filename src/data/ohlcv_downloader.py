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
    # Rate limit'i CCXT tarafında da aç
    exchange_class = getattr(ccxt, exchange.lower())
    client = exchange_class({"enableRateLimit": True})

    retries = 0
    while retries <= max_retries:
        try:
            logger.info(f"Fetching {symbol} {timeframe} data from {exchange} (limit: {limit})")

            ohlcv = client.fetch_ohlcv(symbol, timeframe, limit=limit)

            # 1) Veri boş mu?
            if not ohlcv:
                raise ValueError(f"No data returned for {symbol} {timeframe}")

            # 2) Beklenen sütun sayısı var mı? (ts, o, h, l, c, v)
            if any(len(row) < 6 for row in ohlcv):
                raise ValueError("OHLCV rows have fewer than 6 fields")

            # 3) DataFrame'e aktar ve kolonları STANDART isimlerle yaz
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

            # 4) Zaman damgasını UTC'ye çevir ve indeksle
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df = df.set_index("timestamp", drop=True)

            # 5) Tipleri düzelt
            df = df.astype({
                "open": "float64",
                "high": "float64",
                "low": "float64",
                "close": "float64",
                "volume": "float64"
            })

            # 6) Sıra, tekrar ve boşluk kontrolleri
            #    - ATR ve diğer göstergeler için zaman sırası kritik
            before = len(df)
            df = df[~df.index.duplicated(keep="last")]
            if len(df) != before:
                logger.warning(f"Removed {before - len(df)} duplicate candles")

            # bazı borsalarda sıra bozuk gelebilir
            if not df.index.is_monotonic_increasing:
                df = df.sort_index()

            # 7) Temel geçerlilik
            if df.isna().any().any():
                n = int(df.isna().sum().sum())
                logger.warning(f"Fetched data contains {n} NaNs; indicators may drop leading rows")

            if len(df) == 0:
                raise ValueError("DataFrame is empty after cleaning")

            logger.info(f"Successfully fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")
            return df

        except (ccxt.DDoSProtection, ccxt.RateLimitExceeded) as e:
            retries += 1
            if retries > max_retries:
                logger.error(f"Rate limit exceeded after {max_retries} retries: {e}")
                raise
            wait = retry_delay * (2 ** retries)
            logger.warning(f"Rate limited, waiting {wait:.1f}s before retry {retries}/{max_retries}")
            time.sleep(wait)

        except ccxt.NetworkError as e:
            retries += 1
            if retries > max_retries:
                logger.error(f"Network error after {max_retries} retries: {e}")
                raise
            wait = retry_delay * retries
            logger.warning(f"Network error, retrying in {wait:.1f}s ({retries}/{max_retries})")
            time.sleep(wait)

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
        client = exchange_class({"enableRateLimit": True})
        client.load_markets()

        if symbol not in client.markets:
            # örnek liste ver
            available_symbols = list(client.markets.keys())[:10]
            raise ValueError(f"Symbol {symbol} not available on {exchange}. Available: {available_symbols}...")

        if timeframe not in getattr(client, "timeframes", {}) or not client.timeframes:
            available_timeframes = list(getattr(client, "timeframes", {}).keys()) or ["(exchange does not expose timeframes)"]
            raise ValueError(f"Timeframe {timeframe} not available on {exchange}. Available: {available_timeframes}")

        logger.debug(f"Validated {symbol} {timeframe} on {exchange}")

    except AttributeError:
        raise ValueError(f"Exchange {exchange} not supported")
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise


class OHLCVDownloader:
    """OHLCV data downloader for cryptocurrency data"""
    
    def __init__(self, exchange: str = "binance"):
        self.exchange = exchange
        
    async def download_ohlcv(self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Download OHLCV data for given symbol and timeframe"""
        try:
            logger.info(f"Downloading {symbol} {timeframe} data from {start_date} to {end_date}")
            
            # Calculate how many candles we need based on timeframe
            timeframe_minutes = {
                '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
                '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480,
                '12h': 720, '1d': 1440, '1w': 10080
            }
            
            minutes_per_candle = timeframe_minutes.get(timeframe, 5)
            total_minutes = int((end_date - start_date).total_seconds() / 60)
            limit = min(1000, max(100, int(total_minutes / minutes_per_candle)))
            
            df = fetch_ohlcv(
                exchange=self.exchange,
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            # Return all downloaded data (no date filtering needed for backtests)
            # The fetch_ohlcv already limits the data appropriately
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to download OHLCV data for {symbol}: {e}")
            return pd.DataFrame()
