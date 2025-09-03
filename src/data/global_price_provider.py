import pandas as pd
from datetime import datetime
from typing import List, Optional
from loguru import logger


class GlobalPriceProvider:
    """Abstract provider interface for daily OHLC price data."""

    def fetch_daily(self, ticker: str, start: Optional[datetime] = None, end: Optional[datetime] = None) -> pd.DataFrame:
        raise NotImplementedError


class YahooFinanceProvider(GlobalPriceProvider):
    """Yahoo Finance daily OHLC provider (via yfinance)."""

    def __init__(self):
        try:
            import yfinance as yf  # type: ignore
            self._yf = yf
        except Exception as e:
            logger.error("yfinance is not installed. Please add it to requirements.")
            raise

    def fetch_daily(self, ticker: str, start: Optional[datetime] = None, end: Optional[datetime] = None) -> pd.DataFrame:
        logger.info(f"Fetching daily OHLC for {ticker} from Yahoo Finance")
        data = self._yf.download(tickers=ticker, start=start, end=end, interval="1d", auto_adjust=False, progress=False)
        if data is None or data.empty:
            return pd.DataFrame()

        # Ensure standard columns and UTC index
        df = data.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Adj Close': 'adj_close',
            'Volume': 'volume',
        })
        df.index = pd.to_datetime(df.index, utc=True)
        # keep only required columns for storage compatibility
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in df.columns:
                df[col] = pd.NA
        return df[['open', 'high', 'low', 'close', 'volume']]


def get_provider(name: str) -> GlobalPriceProvider:
    name = name.lower()
    if name in ("yahoo", "yfinance", "yahoo_finance"):
        return YahooFinanceProvider()
    raise ValueError(f"Unknown provider: {name}")

