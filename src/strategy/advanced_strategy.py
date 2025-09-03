import pandas as pd
import numpy as np
from loguru import logger
from src.strategy.rules import bullish_cross, bearish_cross, lower_touch, upper_touch, validate_crossover_signals
from src.utils.config import StrategyConfig


def build_advanced_signals(df: pd.DataFrame, cfg: StrategyConfig, strategy_type: str = "quality_over_quantity") -> tuple[pd.Series, pd.Series]:
    """
    Build high-quality trading signals using advanced indicators
    Focus on quality over quantity to reduce fees and improve profitability
    """
    logger.info(f"Building {strategy_type} advanced strategy signals...")
    
    # Required basic indicators
    required_cols = ["close", "BBL", "BBU", "BBM", "MACD", "MACD_SIGNAL", "RSI"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    tol = cfg.execution.touch_tolerance_pct
    
    # Basic conditions
    bb_lower_touch = lower_touch(df["close"], df["BBL"], tol)
    bb_upper_touch = upper_touch(df["close"], df["BBU"], tol)
    macd_bullish_cross = bullish_cross(df["MACD"], df["MACD_SIGNAL"])
    macd_bearish_cross = bearish_cross(df["MACD"], df["MACD_SIGNAL"])
    
    if strategy_type == "quality_over_quantity":
        buy_signals, sell_signals = _build_quality_signals(df, cfg, bb_lower_touch, bb_upper_touch, 
                                                          macd_bullish_cross, macd_bearish_cross)
    elif strategy_type == "trend_momentum":
        buy_signals, sell_signals = _build_trend_momentum_signals(df, cfg, macd_bullish_cross, macd_bearish_cross)
    elif strategy_type == "volatility_breakout":
        buy_signals, sell_signals = _build_volatility_breakout_signals(df, cfg)
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    # Apply filters
    buy_signals, sell_signals = _apply_advanced_filters(df, buy_signals, sell_signals, cfg)
    
    buy_signals = buy_signals.astype(bool)
    sell_signals = sell_signals.astype(bool)
    
    # Remove simultaneous signals (keep buy priority)
    simultaneous = buy_signals & sell_signals
    sell_signals = sell_signals & ~simultaneous
    
    validate_crossover_signals(buy_signals, sell_signals)
    
    buy_count = buy_signals.sum()
    sell_count = sell_signals.sum()
    
    logger.info(f"Generated {buy_count} buy signals and {sell_count} sell signals")
    
    return buy_signals, sell_signals


def _build_quality_signals(df: pd.DataFrame, cfg: StrategyConfig, bb_lower_touch, bb_upper_touch, 
                          macd_bullish_cross, macd_bearish_cross) -> tuple[pd.Series, pd.Series]:
    """Build high-quality signals with multiple confirmations"""
    
    # Multi-timeframe trend confirmation (use shorter EMA for more signals)
    trend_up = df["close"] > df["EMA20"] if "EMA20" in df.columns else pd.Series(True, index=df.index)
    trend_down = df["close"] < df["EMA20"] if "EMA20" in df.columns else pd.Series(True, index=df.index)
    
    # Volume confirmation (relaxed)
    volume_confirmation = df["VOLUME_RATIO"] > 1.0 if "VOLUME_RATIO" in df.columns else pd.Series(True, index=df.index)
    
    # Volatility filter (relaxed)
    high_volatility = df["ATR_PCT"] > df["ATR_PCT"].rolling(50).quantile(0.3) if "ATR_PCT" in df.columns else pd.Series(True, index=df.index)
    
    # ADX trend strength filter (relaxed)
    strong_trend = df["ADX"] > 15 if "ADX" in df.columns else pd.Series(True, index=df.index)
    
    # RSI oversold/overbought (relaxed)
    rsi_oversold = df["RSI"] < 45
    rsi_overbought = df["RSI"] > 55
    
    # Support/Resistance confirmation
    near_support = (df["close"] - df["SUPPORT"]) / df["SUPPORT"] < 0.02 if "SUPPORT" in df.columns else pd.Series(True, index=df.index)
    near_resistance = (df["RESISTANCE"] - df["close"]) / df["RESISTANCE"] < 0.02 if "RESISTANCE" in df.columns else pd.Series(True, index=df.index)
    
    # High-quality buy conditions (relaxed for more signals)
    buy_signals = (
        (bb_lower_touch | (macd_bullish_cross & rsi_oversold)) & 
        trend_up &
        (volume_confirmation | high_volatility)  # OR condition
    )
    
    # High-quality sell conditions (relaxed for more signals)
    sell_signals = (
        (bb_upper_touch | (macd_bearish_cross & rsi_overbought)) & 
        trend_down &
        (volume_confirmation | high_volatility)  # OR condition
    )
    
    return buy_signals, sell_signals


def _build_trend_momentum_signals(df: pd.DataFrame, cfg: StrategyConfig, 
                                 macd_bullish_cross, macd_bearish_cross) -> tuple[pd.Series, pd.Series]:
    """Build trend-following signals with momentum confirmation"""
    
    # Supertrend for trend direction
    supertrend_up = df["SUPERTREND_DIR"] == 1 if "SUPERTREND_DIR" in df.columns else pd.Series(True, index=df.index)
    supertrend_down = df["SUPERTREND_DIR"] == -1 if "SUPERTREND_DIR" in df.columns else pd.Series(True, index=df.index)
    
    # ADX for trend strength
    strong_trend = df["ADX"] > 20 if "ADX" in df.columns else pd.Series(True, index=df.index)
    
    # Momentum confirmation
    mom_positive = df["MOM"] > 0 if "MOM" in df.columns else pd.Series(True, index=df.index)
    mom_negative = df["MOM"] < 0 if "MOM" in df.columns else pd.Series(True, index=df.index)
    
    # Volume surge
    volume_surge = df["VOLUME_RATIO"] > 1.5 if "VOLUME_RATIO" in df.columns else pd.Series(True, index=df.index)
    
    buy_signals = (
        macd_bullish_cross &
        supertrend_up &
        strong_trend &
        mom_positive &
        volume_surge &
        (df["RSI"] > 40) & (df["RSI"] < 70)  # Not in extreme zones
    )
    
    sell_signals = (
        macd_bearish_cross &
        supertrend_down &
        strong_trend &
        mom_negative &
        volume_surge &
        (df["RSI"] > 30) & (df["RSI"] < 60)  # Not in extreme zones
    )
    
    return buy_signals, sell_signals


def _build_volatility_breakout_signals(df: pd.DataFrame, cfg: StrategyConfig) -> tuple[pd.Series, pd.Series]:
    """Build volatility breakout signals"""
    
    # Bollinger Band squeeze detection
    bb_squeeze = ((df["BBU"] - df["BBL"]) / df["BBM"]) < ((df["BBU"] - df["BBL"]) / df["BBM"]).rolling(20).quantile(0.2)
    
    # Keltner Channel breakout
    kc_breakout_up = df["close"] > df["KC_UPPER"] if "KC_UPPER" in df.columns else pd.Series(False, index=df.index)
    kc_breakout_down = df["close"] < df["KC_LOWER"] if "KC_LOWER" in df.columns else pd.Series(False, index=df.index)
    
    # Volume expansion
    volume_expansion = df["VOLUME_RATIO"] > 2.0 if "VOLUME_RATIO" in df.columns else pd.Series(True, index=df.index)
    
    # ATR expansion (volatility increasing)
    atr_expanding = df["ATR"] > df["ATR"].shift(1) if "ATR" in df.columns else pd.Series(True, index=df.index)
    
    buy_signals = (
        kc_breakout_up &
        volume_expansion &
        atr_expanding &
        ~bb_squeeze &  # After squeeze ends
        (df["RSI"] > 50)  # Some momentum
    )
    
    sell_signals = (
        kc_breakout_down &
        volume_expansion &
        atr_expanding &
        ~bb_squeeze &  # After squeeze ends
        (df["RSI"] < 50)  # Some momentum down
    )
    
    return buy_signals, sell_signals


def _apply_advanced_filters(df: pd.DataFrame, buy_signals: pd.Series, sell_signals: pd.Series, 
                           cfg: StrategyConfig) -> tuple[pd.Series, pd.Series]:
    """Apply advanced filters to reduce false signals"""
    
    # Market structure filter
    if "TREND" in df.columns:
        buy_signals = buy_signals & (df["TREND"] > 0.1)  # Uptrend
        sell_signals = sell_signals & (df["TREND"] < -0.1)  # Downtrend
    
    # Time-based filter (avoid signals too close together)
    # Keep only signals that are at least 5 periods apart
    buy_signals_filtered = pd.Series(False, index=df.index)
    sell_signals_filtered = pd.Series(False, index=df.index)
    
    last_buy_idx = -10
    last_sell_idx = -10
    
    for i in range(len(buy_signals)):
        if buy_signals.iloc[i] and (i - last_buy_idx) >= 5:
            buy_signals_filtered.iloc[i] = True
            last_buy_idx = i
            
        if sell_signals.iloc[i] and (i - last_sell_idx) >= 5:
            sell_signals_filtered.iloc[i] = True
            last_sell_idx = i
    
    # EMA trend filter if enabled
    if cfg.filters.ema_trend.use and "EMA200" in df.columns:
        if cfg.filters.ema_trend.mode == "long_only_above":
            buy_signals_filtered = buy_signals_filtered & (df["close"] > df["EMA200"])
    
    return buy_signals_filtered, sell_signals_filtered


def calculate_position_size(df: pd.DataFrame, current_idx: int, cfg: StrategyConfig) -> float:
    """Calculate dynamic position size based on volatility"""
    
    if "ATR" not in df.columns:
        return cfg.backtest.size_pct
    
    # Risk-based position sizing
    current_price = df["close"].iloc[current_idx]
    atr = df["ATR"].iloc[current_idx]
    
    # Risk 1% of portfolio per trade
    risk_pct = 0.01
    stop_distance = atr * 2  # 2 ATR stop
    
    if stop_distance > 0:
        position_size = risk_pct / (stop_distance / current_price)
        # Cap at 95% of portfolio
        return min(position_size, 0.95)
    
    return cfg.backtest.size_pct