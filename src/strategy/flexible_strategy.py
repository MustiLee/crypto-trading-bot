import pandas as pd
from loguru import logger
from src.strategy.rules import bullish_cross, bearish_cross, lower_touch, upper_touch, validate_crossover_signals
from src.utils.config import StrategyConfig


def build_flexible_signals(df: pd.DataFrame, cfg: StrategyConfig, strategy_type: str = "signal_rich") -> tuple[pd.Series, pd.Series]:
    """
    Build flexible signals based on strategy type
    
    Args:
        df: DataFrame with OHLCV and indicators
        cfg: Strategy configuration
        strategy_type: "signal_rich", "trend_following", or "mean_reversion"
    """
    logger.info(f"Building {strategy_type} strategy signals...")
    
    required_cols = ["close", "BBL", "BBU", "BBM", "MACD", "MACD_SIGNAL"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    tol = cfg.execution.touch_tolerance_pct
    
    # Basic conditions
    bb_lower_touch = lower_touch(df["close"], df["BBL"], tol)
    bb_upper_touch = upper_touch(df["close"], df["BBU"], tol)
    bb_near_lower = df["close"] <= df["BBL"] * (1 + tol * 2)  # Near lower band
    bb_near_upper = df["close"] >= df["BBU"] * (1 - tol * 2)  # Near upper band
    
    macd_bullish_cross = bullish_cross(df["MACD"], df["MACD_SIGNAL"])
    macd_bearish_cross = bearish_cross(df["MACD"], df["MACD_SIGNAL"])
    macd_above_signal = df["MACD"] > df["MACD_SIGNAL"]
    macd_below_signal = df["MACD"] < df["MACD_SIGNAL"]
    
    # Price position relative to BB middle
    above_bb_middle = df["close"] > df["BBM"]
    below_bb_middle = df["close"] < df["BBM"]
    
    if strategy_type == "signal_rich":
        # Generate more signals: BB touches OR MACD crossovers
        buy_signals = (
            bb_lower_touch |  # BB lower touch
            (bb_near_lower & macd_bullish_cross) |  # Near lower + MACD bullish
            (below_bb_middle & macd_bullish_cross)  # Below middle + MACD bullish
        )
        sell_signals = (
            bb_upper_touch |  # BB upper touch
            (bb_near_upper & macd_bearish_cross) |  # Near upper + MACD bearish
            (above_bb_middle & macd_bearish_cross)  # Above middle + MACD bearish
        )
        
    elif strategy_type == "trend_following":
        # MACD-driven with BB confirmation
        buy_signals = (
            macd_bullish_cross & 
            (below_bb_middle | bb_near_lower)  # Price not too high
        )
        sell_signals = (
            macd_bearish_cross & 
            (above_bb_middle | bb_near_upper)  # Price not too low
        )
        
    elif strategy_type == "mean_reversion":
        # BB-driven with MACD momentum confirmation
        buy_signals = (
            bb_lower_touch & macd_above_signal  # BB touch + MACD momentum
        ) | (
            bb_near_lower & macd_bullish_cross  # Near touch + fresh bullish cross
        )
        sell_signals = (
            bb_upper_touch & macd_below_signal  # BB touch + MACD momentum
        ) | (
            bb_near_upper & macd_bearish_cross  # Near touch + fresh bearish cross
        )
        
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    # Apply RSI filter if enabled
    if cfg.rsi.use_filter and "RSI" in df.columns:
        logger.debug(f"Applying RSI filter (buy_max: {cfg.rsi.rsi_buy_max}, sell_min: {cfg.rsi.rsi_sell_min})")
        buy_signals = buy_signals & (df["RSI"] <= cfg.rsi.rsi_buy_max)
        sell_signals = sell_signals & (df["RSI"] >= cfg.rsi.rsi_sell_min)
    
    # Apply EMA trend filter if enabled
    if cfg.filters.ema_trend.use and "EMA200" in df.columns:
        logger.debug(f"Applying EMA trend filter (mode: {cfg.filters.ema_trend.mode})")
        if cfg.filters.ema_trend.mode == "long_only_above":
            buy_signals = buy_signals & (df["close"] > df["EMA200"])
            # Don't filter sell signals - allow exits even below EMA
    
    buy_signals = buy_signals.astype(bool)
    sell_signals = sell_signals.astype(bool)
    
    # Validate signals
    validate_crossover_signals(buy_signals, sell_signals)
    
    buy_count = buy_signals.sum()
    sell_count = sell_signals.sum()
    
    logger.info(f"Generated {buy_count} buy signals and {sell_count} sell signals")
    
    if buy_count == 0:
        logger.warning("No buy signals generated!")
    if sell_count == 0:
        logger.warning("No sell signals generated!")
    
    return buy_signals, sell_signals


def analyze_signal_distribution(df: pd.DataFrame, buy_signals: pd.Series, sell_signals: pd.Series) -> dict:
    """Analyze signal distribution across different market conditions"""
    
    analysis = {
        "total_periods": len(df),
        "buy_signals": buy_signals.sum(),
        "sell_signals": sell_signals.sum(),
        "signal_frequency": (buy_signals.sum() + sell_signals.sum()) / len(df),
        "market_conditions": {}
    }
    
    if "BBM" in df.columns:
        # Analyze signals by price position relative to BB middle
        above_middle = df["close"] > df["BBM"]
        below_middle = df["close"] < df["BBM"]
        
        analysis["market_conditions"]["above_bb_middle"] = {
            "periods": above_middle.sum(),
            "buy_signals": (buy_signals & above_middle).sum(),
            "sell_signals": (sell_signals & above_middle).sum()
        }
        analysis["market_conditions"]["below_bb_middle"] = {
            "periods": below_middle.sum(),
            "buy_signals": (buy_signals & below_middle).sum(),
            "sell_signals": (sell_signals & below_middle).sum()
        }
    
    return analysis