import pandas as pd
import pandas_ta as ta
from loguru import logger
from src.utils.config import StrategyConfig


def add_indicators(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    logger.info("Computing technical indicators...")
    
    if len(df) == 0:
        raise ValueError("Cannot compute indicators on empty DataFrame")
    
    if "close" not in df.columns:
        raise ValueError("DataFrame must contain 'close' column")
    
    original_len = len(df)
    
    logger.debug(f"Computing Bollinger Bands (length={cfg.bollinger.length}, std={cfg.bollinger.std})")
    bb = df.ta.bbands(length=cfg.bollinger.length, std=cfg.bollinger.std)
    
    logger.debug(f"Computing MACD (fast={cfg.macd.fast}, slow={cfg.macd.slow}, signal={cfg.macd.signal})")
    macd = df.ta.macd(fast=cfg.macd.fast, slow=cfg.macd.slow, signal=cfg.macd.signal)
    
    logger.debug(f"Computing RSI (length={cfg.rsi.length})")
    rsi = df.ta.rsi(length=cfg.rsi.length)
    
    result = df.join([bb, macd, rsi.rename("RSI")])
    
    bb_lower_col = f"BBL_{cfg.bollinger.length}_{cfg.bollinger.std}"
    bb_mid_col = f"BBM_{cfg.bollinger.length}_{cfg.bollinger.std}"
    bb_upper_col = f"BBU_{cfg.bollinger.length}_{cfg.bollinger.std}"
    macd_col = f"MACD_{cfg.macd.fast}_{cfg.macd.slow}_{cfg.macd.signal}"
    macd_signal_col = f"MACDs_{cfg.macd.fast}_{cfg.macd.slow}_{cfg.macd.signal}"
    macd_hist_col = f"MACDh_{cfg.macd.fast}_{cfg.macd.slow}_{cfg.macd.signal}"
    
    rename_map = {}
    if bb_lower_col in result.columns:
        rename_map[bb_lower_col] = "BBL"
    if bb_mid_col in result.columns:
        rename_map[bb_mid_col] = "BBM"
    if bb_upper_col in result.columns:
        rename_map[bb_upper_col] = "BBU"
    if macd_col in result.columns:
        rename_map[macd_col] = "MACD"
    if macd_signal_col in result.columns:
        rename_map[macd_signal_col] = "MACD_SIGNAL"
    if macd_hist_col in result.columns:
        rename_map[macd_hist_col] = "MACD_HIST"
    
    result = result.rename(columns=rename_map)
    
    required_indicators = ["BBL", "BBM", "BBU", "MACD", "MACD_SIGNAL", "MACD_HIST", "RSI"]
    missing_indicators = [ind for ind in required_indicators if ind not in result.columns]
    
    if missing_indicators:
        raise ValueError(f"Failed to compute indicators: {missing_indicators}")
    
    result_clean = result.dropna()
    final_len = len(result_clean)
    dropped_rows = original_len - final_len
    
    if dropped_rows > 0:
        logger.info(f"Dropped {dropped_rows} rows with NaN values after indicator computation")
    
    if final_len == 0:
        raise ValueError("All rows contain NaN after indicator computation. Check data quality or indicator parameters.")
    
    logger.info(f"Successfully computed indicators. Final dataset: {final_len} rows")
    
    return result_clean


def validate_indicators(df: pd.DataFrame) -> None:
    required_cols = ["BBL", "BBM", "BBU", "MACD", "MACD_SIGNAL", "MACD_HIST", "RSI"]
    
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required indicator column: {col}")
        
        if df[col].isna().sum() > 0:
            raise ValueError(f"Indicator column {col} contains NaN values")
    
    if not (df["BBL"] <= df["BBM"]).all():
        raise ValueError("Bollinger lower band should be <= middle band")
    
    if not (df["BBM"] <= df["BBU"]).all():
        raise ValueError("Bollinger middle band should be <= upper band")
    
    if not ((df["RSI"] >= 0) & (df["RSI"] <= 100)).all():
        raise ValueError("RSI values should be between 0 and 100")
    
    logger.debug("Indicator validation passed")