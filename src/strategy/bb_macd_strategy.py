import pandas as pd
from loguru import logger
from src.strategy.rules import bullish_cross, bearish_cross, lower_touch, upper_touch, validate_crossover_signals
from src.utils.config import StrategyConfig


def build_signals(df: pd.DataFrame, cfg: StrategyConfig) -> tuple[pd.Series, pd.Series]:
    logger.info("Building BB-MACD strategy signals...")
    
    required_cols = ["close", "BBL", "BBU", "MACD", "MACD_SIGNAL"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    if cfg.rsi.use_filter and "RSI" not in df.columns:
        raise ValueError("RSI filter enabled but RSI column not found")
    
    tol = cfg.execution.touch_tolerance_pct
    
    logger.debug(f"Computing Bollinger Band touches (tolerance: {tol:.4f})")
    bb_lower_touch = lower_touch(df["close"], df["BBL"], tol)
    bb_upper_touch = upper_touch(df["close"], df["BBU"], tol)
    
    logger.debug("Computing MACD crossovers")
    macd_bullish_cross = bullish_cross(df["MACD"], df["MACD_SIGNAL"])
    macd_bearish_cross = bearish_cross(df["MACD"], df["MACD_SIGNAL"])
    
    logger.debug("Combining conditions for buy/sell signals")
    buy_signals = bb_lower_touch & macd_bullish_cross
    sell_signals = bb_upper_touch & macd_bearish_cross
    
    if cfg.rsi.use_filter:
        logger.debug(f"Applying RSI filter (buy_max: {cfg.rsi.rsi_buy_max}, sell_min: {cfg.rsi.rsi_sell_min})")
        buy_signals = buy_signals & (df["RSI"] <= cfg.rsi.rsi_buy_max)
        sell_signals = sell_signals & (df["RSI"] >= cfg.rsi.rsi_sell_min)
    
    # EMA trend filter - only allow long entries when price is above EMA
    if cfg.filters.ema_trend.use:
        if "EMA_TREND" not in df.columns:
            raise ValueError("EMA trend filter enabled but EMA_TREND column not found")
        
        logger.debug(f"Applying EMA trend filter (length: {cfg.filters.ema_trend.length}, mode: {cfg.filters.ema_trend.mode})")
        if cfg.filters.ema_trend.mode == "long_only_above":
            # Only allow buy signals when close > EMA200
            buy_signals = buy_signals & (df["close"] > df["EMA_TREND"])
    
    buy_signals = buy_signals.astype(bool)
    sell_signals = sell_signals.astype(bool)
    
    validate_crossover_signals(buy_signals, sell_signals)
    
    buy_count = buy_signals.sum()
    sell_count = sell_signals.sum()
    
    logger.info(f"Generated {buy_count} buy signals and {sell_count} sell signals")
    
    if buy_count == 0:
        logger.warning("No buy signals generated!")
    if sell_count == 0:
        logger.warning("No sell signals generated!")
    
    return buy_signals, sell_signals


def analyze_signal_timing(df: pd.DataFrame, buy_signals: pd.Series, sell_signals: pd.Series) -> dict:
    analysis = {
        "total_periods": len(df),
        "buy_signals": buy_signals.sum(),
        "sell_signals": sell_signals.sum(),
        "signal_rate": (buy_signals.sum() + sell_signals.sum()) / len(df),
        "first_buy_index": None,
        "first_sell_index": None,
        "last_buy_index": None,
        "last_sell_index": None,
    }
    
    if buy_signals.any():
        buy_indices = buy_signals[buy_signals].index
        analysis["first_buy_index"] = buy_indices[0]
        analysis["last_buy_index"] = buy_indices[-1]
    
    if sell_signals.any():
        sell_indices = sell_signals[sell_signals].index
        analysis["first_sell_index"] = sell_indices[0]
        analysis["last_sell_index"] = sell_indices[-1]
    
    return analysis


def debug_signal_conditions(df: pd.DataFrame, cfg: StrategyConfig, index: int = None) -> dict:
    if index is None:
        index = len(df) - 1
    
    if index < 0 or index >= len(df):
        raise ValueError(f"Index {index} out of bounds for DataFrame of length {len(df)}")
    
    row = df.iloc[index]
    
    debug_info = {
        "timestamp": df.index[index],
        "close": row["close"],
        "bb_lower": row["BBL"],
        "bb_upper": row["BBU"],
        "macd": row["MACD"],
        "macd_signal": row["MACD_SIGNAL"],
        "rsi": row.get("RSI", None),
        "conditions": {}
    }
    
    tol = cfg.execution.touch_tolerance_pct
    
    debug_info["conditions"]["bb_lower_touch"] = row["close"] <= row["BBL"] * (1 + tol)
    debug_info["conditions"]["bb_upper_touch"] = row["close"] >= row["BBU"] * (1 - tol)
    
    if index > 0:
        prev_row = df.iloc[index - 1]
        debug_info["conditions"]["macd_bullish_cross"] = (
            prev_row["MACD"] <= prev_row["MACD_SIGNAL"] and row["MACD"] > row["MACD_SIGNAL"]
        )
        debug_info["conditions"]["macd_bearish_cross"] = (
            prev_row["MACD"] >= prev_row["MACD_SIGNAL"] and row["MACD"] < row["MACD_SIGNAL"]
        )
    else:
        debug_info["conditions"]["macd_bullish_cross"] = False
        debug_info["conditions"]["macd_bearish_cross"] = False
    
    if cfg.rsi.use_filter and "RSI" in df.columns:
        debug_info["conditions"]["rsi_buy_filter"] = row["RSI"] <= cfg.rsi.rsi_buy_max
        debug_info["conditions"]["rsi_sell_filter"] = row["RSI"] >= cfg.rsi.rsi_sell_min
    
    debug_info["conditions"]["buy_signal"] = (
        debug_info["conditions"]["bb_lower_touch"] and 
        debug_info["conditions"]["macd_bullish_cross"]
    )
    debug_info["conditions"]["sell_signal"] = (
        debug_info["conditions"]["bb_upper_touch"] and 
        debug_info["conditions"]["macd_bearish_cross"]
    )
    
    if cfg.rsi.use_filter and "RSI" in df.columns:
        debug_info["conditions"]["buy_signal"] = (
            debug_info["conditions"]["buy_signal"] and 
            debug_info["conditions"]["rsi_buy_filter"]
        )
        debug_info["conditions"]["sell_signal"] = (
            debug_info["conditions"]["sell_signal"] and 
            debug_info["conditions"]["rsi_sell_filter"]
        )
    
    return debug_info