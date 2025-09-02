import os
import pandas as pd
from pathlib import Path
from typing import Optional
from loguru import logger


class DataCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_cache_path(self, symbol: str, timeframe: str) -> Path:
        filename = f"{symbol.replace('/', '')}{timeframe}.csv"
        return self.cache_dir / filename
    
    def exists(self, symbol: str, timeframe: str) -> bool:
        cache_path = self.get_cache_path(symbol, timeframe)
        return cache_path.exists()
    
    def is_fresh(self, symbol: str, timeframe: str, max_age_hours: int = 24) -> bool:
        if not self.exists(symbol, timeframe):
            return False
        
        cache_path = self.get_cache_path(symbol, timeframe)
        import time
        file_age = time.time() - cache_path.stat().st_mtime
        return file_age < (max_age_hours * 3600)
    
    def load(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        cache_path = self.get_cache_path(symbol, timeframe)
        
        if not cache_path.exists():
            return None
        
        try:
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            logger.info(f"Loaded cached data: {len(df)} candles from {cache_path}")
            return df
        except Exception as e:
            logger.error(f"Failed to load cache {cache_path}: {e}")
            return None
    
    def save(self, df: pd.DataFrame, symbol: str, timeframe: str) -> None:
        cache_path = self.get_cache_path(symbol, timeframe)
        
        try:
            df.to_csv(cache_path)
            logger.info(f"Saved {len(df)} candles to cache: {cache_path}")
        except Exception as e:
            logger.error(f"Failed to save cache {cache_path}: {e}")
    
    def clear(self, symbol: str, timeframe: str) -> None:
        cache_path = self.get_cache_path(symbol, timeframe)
        
        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"Cleared cache: {cache_path}")
    
    def clear_all(self) -> None:
        for file in self.cache_dir.glob("*.csv"):
            file.unlink()
        logger.info(f"Cleared all cache files from {self.cache_dir}")