import pandas as pd
import numpy as np
import pandas_ta as ta
from loguru import logger


def add_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add volume-based indicators"""
    if 'volume' not in df.columns:
        logger.warning("Volume data not available, skipping volume indicators")
        return df
    
    # Volume Profile / OBV
    df['OBV'] = ta.obv(df['close'], df['volume'])
    
    # Volume Weighted Average Price
    df['VWAP'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
    
    # Accumulation/Distribution Line
    df['AD'] = ta.ad(df['high'], df['low'], df['close'], df['volume'])
    
    # Chaikin Money Flow
    df['CMF'] = ta.cmf(df['high'], df['low'], df['close'], df['volume'])
    
    return df


def add_volatility_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add volatility-based indicators"""
    
    # Average True Range
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['ATR_PCT'] = (df['ATR'] / df['close']) * 100
    
    # Keltner Channels
    keltner = ta.kc(df['high'], df['low'], df['close'])
    if isinstance(keltner, pd.DataFrame):
        df['KC_UPPER'] = keltner.iloc[:, 0]
        df['KC_MIDDLE'] = keltner.iloc[:, 1] 
        df['KC_LOWER'] = keltner.iloc[:, 2]
    
    # Volatility Index
    df['VI'] = df['high'].rolling(14).std() / df['close'].rolling(14).mean()
    
    return df


def add_momentum_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add momentum-based indicators"""
    
    # Williams %R
    df['WILLR'] = ta.willr(df['high'], df['low'], df['close'])
    
    # Stochastic Oscillator
    stoch = ta.stoch(df['high'], df['low'], df['close'])
    if isinstance(stoch, pd.DataFrame):
        df['STOCH_K'] = stoch.iloc[:, 0]
        df['STOCH_D'] = stoch.iloc[:, 1]
    
    # Commodity Channel Index
    df['CCI'] = ta.cci(df['high'], df['low'], df['close'])
    
    # Rate of Change
    df['ROC'] = ta.roc(df['close'], length=10)
    
    # Momentum
    df['MOM'] = ta.mom(df['close'], length=10)
    
    return df


def add_trend_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add trend-based indicators"""
    
    # Parabolic SAR
    df['PSAR'] = ta.psar(df['high'], df['low'])
    
    # Average Directional Index
    adx_data = ta.adx(df['high'], df['low'], df['close'])
    if isinstance(adx_data, pd.DataFrame):
        df['ADX'] = adx_data.iloc[:, 0]
        df['DMP'] = adx_data.iloc[:, 1]  # DI+
        df['DMN'] = adx_data.iloc[:, 2]  # DI-
    
    # Aroon
    aroon = ta.aroon(df['high'], df['low'])
    if isinstance(aroon, pd.DataFrame):
        df['AROON_UP'] = aroon.iloc[:, 0]
        df['AROON_DOWN'] = aroon.iloc[:, 1]
    
    # Supertrend
    supertrend = ta.supertrend(df['high'], df['low'], df['close'])
    if isinstance(supertrend, pd.DataFrame):
        df['SUPERTREND'] = supertrend.iloc[:, 0]
        df['SUPERTREND_DIR'] = supertrend.iloc[:, 1]
    
    return df


def add_support_resistance(df: pd.DataFrame, lookback=20) -> pd.DataFrame:
    """Add dynamic support and resistance levels"""
    
    # Rolling highs and lows
    df['RESISTANCE'] = df['high'].rolling(lookback).max()
    df['SUPPORT'] = df['low'].rolling(lookback).min()
    
    # Pivot points (simplified)
    df['PIVOT'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
    df['R1'] = 2 * df['PIVOT'] - df['low'].shift(1)
    df['S1'] = 2 * df['PIVOT'] - df['high'].shift(1)
    
    return df


def add_market_structure(df: pd.DataFrame) -> pd.DataFrame:
    """Add market structure analysis"""
    
    # Higher highs, higher lows detection
    df['HH'] = (df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(2))
    df['HL'] = (df['low'] > df['low'].shift(1)) & (df['low'] > df['low'].shift(2))
    df['LH'] = (df['high'] < df['high'].shift(1)) & (df['high'] < df['high'].shift(2))
    df['LL'] = (df['low'] < df['low'].shift(1)) & (df['low'] < df['low'].shift(2))
    
    # Trend direction (1=uptrend, -1=downtrend, 0=sideways)
    df['TREND'] = 0
    df.loc[df['HH'] | df['HL'], 'TREND'] = 1
    df.loc[df['LH'] | df['LL'], 'TREND'] = -1
    df['TREND'] = df['TREND'].rolling(5).mean()  # Smooth the signal
    
    return df


def add_custom_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Add custom filtering indicators"""
    
    # Price position relative to moving averages
    df['PRICE_VS_EMA20'] = (df['close'] - df['EMA20']) / df['EMA20'] * 100
    df['PRICE_VS_EMA50'] = (df['close'] - df['EMA50']) / df['EMA50'] * 100
    
    if 'EMA200' in df.columns:
        df['PRICE_VS_EMA200'] = (df['close'] - df['EMA200']) / df['EMA200'] * 100
    
    # Bollinger Band position (0=bottom, 1=top)
    if all(col in df.columns for col in ['BBL', 'BBU']):
        df['BB_POSITION'] = (df['close'] - df['BBL']) / (df['BBU'] - df['BBL'])
    
    # Volume relative to average
    if 'volume' in df.columns:
        df['VOLUME_RATIO'] = df['volume'] / df['volume'].rolling(20).mean()
    
    return df


def add_all_advanced_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all advanced indicators to the dataframe"""
    
    logger.info("Adding advanced indicators...")
    
    df = add_volume_indicators(df)
    df = add_volatility_indicators(df)
    df = add_momentum_indicators(df)
    df = add_trend_indicators(df)
    df = add_support_resistance(df)
    df = add_market_structure(df)
    df = add_custom_filters(df)
    
    logger.info(f"Added advanced indicators. DataFrame shape: {df.shape}")
    
    return df