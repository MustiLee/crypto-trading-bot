import pandas as pd
import numpy as np
from loguru import logger
from src.utils.config import StrategyConfig
# Temporarily disabled due to pandas_ta dependency
# from src.indicators.advanced_indicators import add_all_advanced_indicators


def _calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI manually"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0):
    """Calculate Bollinger Bands manually"""
    sma = prices.rolling(window=period).mean()
    rolling_std = prices.rolling(window=period).std()
    
    bb_upper = sma + (rolling_std * std_dev)
    bb_middle = sma
    bb_lower = sma - (rolling_std * std_dev)
    
    return pd.DataFrame({
        f'BBL_{period}_{std_dev}': bb_lower,
        f'BBM_{period}_{std_dev}': bb_middle,
        f'BBU_{period}_{std_dev}': bb_upper
    }, index=prices.index)


def _calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Calculate MACD manually"""
    # Calculate exponential moving averages
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    
    # MACD line
    macd_line = ema_fast - ema_slow
    
    # Signal line
    macd_signal = macd_line.ewm(span=signal).mean()
    
    # Histogram
    macd_histogram = macd_line - macd_signal
    
    return pd.DataFrame({
        f'MACD_{fast}_{slow}_{signal}': macd_line,
        f'MACDs_{fast}_{slow}_{signal}': macd_signal,
        f'MACDh_{fast}_{slow}_{signal}': macd_histogram
    }, index=prices.index)


def _calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Calculate EMA manually"""
    return prices.ewm(span=period).mean()


def _calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate ATR manually"""
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr


def add_indicators(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """
    Zorunlu: BB, MACD, RSI
    Opsiyonel: EMA{length} (filters.ema_trend.use == True),
               ATR (risk.use_atr == True)
    """
    logger.info("Computing technical indicators...")

    if df.empty:
        raise ValueError("Cannot compute indicators on empty DataFrame")
    for col in ("open", "high", "low", "close"):
        if col not in df.columns:
            raise ValueError(f"DataFrame must contain '{col}' column")

    original_len = len(df)
    result = df.copy()

    # --- Bollinger Bands ---
    logger.debug(f"Computing Bollinger Bands (length={cfg.bollinger.length}, std={cfg.bollinger.std})")
    bb = _calculate_bollinger_bands(df["close"], cfg.bollinger.length, cfg.bollinger.std)
    result = result.join(bb)

    # --- MACD ---
    logger.debug(f"Computing MACD (fast={cfg.macd.fast}, slow={cfg.macd.slow}, signal={cfg.macd.signal})")
    macd = _calculate_macd(df["close"], cfg.macd.fast, cfg.macd.slow, cfg.macd.signal)
    result = result.join(macd)

    # --- RSI ---
    logger.debug(f"Computing RSI (length={cfg.rsi.length})")
    rsi = _calculate_rsi(df["close"], cfg.rsi.length)
    result["RSI"] = rsi

    # --- İsimleri normalize et ---
    bb_lower_col = f"BBL_{cfg.bollinger.length}_{cfg.bollinger.std}"
    bb_mid_col   = f"BBM_{cfg.bollinger.length}_{cfg.bollinger.std}"
    bb_upper_col = f"BBU_{cfg.bollinger.length}_{cfg.bollinger.std}"
    macd_col        = f"MACD_{cfg.macd.fast}_{cfg.macd.slow}_{cfg.macd.signal}"
    macd_signal_col = f"MACDs_{cfg.macd.fast}_{cfg.macd.slow}_{cfg.macd.signal}"
    macd_hist_col   = f"MACDh_{cfg.macd.fast}_{cfg.macd.slow}_{cfg.macd.signal}"

    rename_map = {}
    if bb_lower_col in result.columns:  rename_map[bb_lower_col] = "BBL"
    if bb_mid_col   in result.columns:  rename_map[bb_mid_col]   = "BBM"
    if bb_upper_col in result.columns:  rename_map[bb_upper_col] = "BBU"
    if macd_col in result.columns:         rename_map[macd_col]        = "MACD"
    if macd_signal_col in result.columns:  rename_map[macd_signal_col] = "MACD_SIGNAL"
    if macd_hist_col in result.columns:    rename_map[macd_hist_col]   = "MACD_HIST"

    result = result.rename(columns=rename_map)

    # --- EMA Trend (opsiyonel) ---
    if getattr(cfg, "filters", None) and getattr(cfg.filters, "ema_trend", None) and cfg.filters.ema_trend.use:
        ema_len = cfg.filters.ema_trend.length
        logger.debug(f"Computing EMA trend filter (length={ema_len})")
        ema_series = _calculate_ema(result["close"], ema_len)
        result[f"EMA{ema_len}"] = ema_series

    # --- ATR (opsiyonel) ---
    if getattr(cfg, "risk", None) and cfg.risk.use_atr:
        atr_len = cfg.risk.atr_length
        logger.debug(f"Computing ATR (length={atr_len})")
        atr = _calculate_atr(result["high"], result["low"], result["close"], atr_len)
        result["ATR"] = atr
    
    # --- Gelişmiş indikatörler (geçici olarak devre dışı) ---
    logger.debug("Advanced indicators temporarily disabled due to pandas_ta dependency")
    # try:
    #     result = add_all_advanced_indicators(result)
    #     logger.debug("Successfully added advanced indicators")
    # except Exception as e:
    #     logger.warning(f"Failed to add some advanced indicators: {e}")
    #     # Continue without advanced indicators if they fail

    # --- Zorunlu göstergeler mevcut mu? ---
    required = ["BBL", "BBM", "BBU", "MACD", "MACD_SIGNAL", "MACD_HIST", "RSI"]
    missing = [c for c in required if c not in result.columns]
    if missing:
        raise ValueError(f"Failed to compute indicators: {missing}")

    # --- NaN temizliği ---
    result_clean = result.dropna()
    dropped = original_len - len(result_clean)
    if dropped > 0:
        logger.info(f"Dropped {dropped} rows with NaN values after indicator computation")

    if result_clean.empty:
        raise ValueError("All rows contain NaN after indicator computation. Check data quality or indicator parameters.")

    logger.info(f"Successfully computed indicators. Final dataset: {len(result_clean)} rows")
    return result_clean


def validate_indicators(df: pd.DataFrame, cfg: StrategyConfig | None = None) -> None:
    required_cols = ["BBL", "BBM", "BBU", "MACD", "MACD_SIGNAL", "MACD_HIST", "RSI"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required indicator column: {col}")
        if df[col].isna().any():
            raise ValueError(f"Indicator column {col} contains NaN values")

    if not (df["BBL"] <= df["BBM"]).all():
        raise ValueError("Bollinger lower band should be <= middle band")
    if not (df["BBM"] <= df["BBU"]).all():
        raise ValueError("Bollinger middle band should be <= upper band")

    if not ((df["RSI"] >= 0) & (df["RSI"] <= 100)).all():
        raise ValueError("RSI values should be between 0 and 100")

    if cfg and getattr(cfg, "filters", None) and getattr(cfg.filters, "ema_trend", None) and cfg.filters.ema_trend.use:
        ema_col = f"EMA{cfg.filters.ema_trend.length}"
        if ema_col not in df.columns or df[ema_col].isna().any():
            raise ValueError(f"EMA column {ema_col} missing or contains NaN values")

    if cfg and getattr(cfg, "risk", None) and cfg.risk.use_atr:
        if "ATR" not in df.columns or df["ATR"].isna().any() or not (df["ATR"] > 0).all():
            raise ValueError("ATR column missing/NaN or non-positive")

    logger.debug("Indicator validation passed")
