import pandas as pd
from loguru import logger


def bullish_cross(macd: pd.Series, signal: pd.Series) -> pd.Series:
    if len(macd) != len(signal):
        raise ValueError("MACD and signal series must have same length")
    
    cross = (macd.shift(1) <= signal.shift(1)) & (macd > signal)
    return cross.fillna(False)


def bearish_cross(macd: pd.Series, signal: pd.Series) -> pd.Series:
    if len(macd) != len(signal):
        raise ValueError("MACD and signal series must have same length")
    
    cross = (macd.shift(1) >= signal.shift(1)) & (macd < signal)
    return cross.fillna(False)


def lower_touch(close: pd.Series, lower: pd.Series, tolerance: float = 0.0) -> pd.Series:
    if tolerance < 0:
        raise ValueError("Tolerance must be non-negative")
    
    threshold = lower * (1 + tolerance)
    touch = close <= threshold
    return touch.fillna(False)


def upper_touch(close: pd.Series, upper: pd.Series, tolerance: float = 0.0) -> pd.Series:
    if tolerance < 0:
        raise ValueError("Tolerance must be non-negative")
    
    threshold = upper * (1 - tolerance)
    touch = close >= threshold
    return touch.fillna(False)


def validate_crossover_signals(buy_signals: pd.Series, sell_signals: pd.Series) -> None:
    if len(buy_signals) != len(sell_signals):
        raise ValueError("Buy and sell signal series must have same length")
    
    if buy_signals.dtype != bool and str(buy_signals.dtype) != 'boolean':
        logger.warning("Buy signals are not boolean type, converting...")
    
    if sell_signals.dtype != bool and str(sell_signals.dtype) != 'boolean':
        logger.warning("Sell signals are not boolean type, converting...")
    
    simultaneous_signals = (buy_signals & sell_signals).sum()
    if simultaneous_signals > 0:
        logger.warning(f"Found {simultaneous_signals} simultaneous buy/sell signals")
    
    total_buy = buy_signals.sum()
    total_sell = sell_signals.sum()
    
    logger.debug(f"Signal validation: {total_buy} buy signals, {total_sell} sell signals")