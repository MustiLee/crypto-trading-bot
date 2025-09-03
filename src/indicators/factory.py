import pandas as pd
import pandas_ta as ta
from loguru import logger
from src.utils.config import StrategyConfig
from src.indicators.advanced_indicators import add_all_advanced_indicators


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

    # --- Bollinger Bands ---
    logger.debug(f"Computing Bollinger Bands (length={cfg.bollinger.length}, std={cfg.bollinger.std})")
    bb = ta.bbands(close=df["close"], length=cfg.bollinger.length, std=cfg.bollinger.std)

    # --- MACD ---
    logger.debug(f"Computing MACD (fast={cfg.macd.fast}, slow={cfg.macd.slow}, signal={cfg.macd.signal})")
    macd = ta.macd(close=df["close"], fast=cfg.macd.fast, slow=cfg.macd.slow, signal=cfg.macd.signal)

    # --- RSI ---
    logger.debug(f"Computing RSI (length={cfg.rsi.length})")
    rsi = ta.rsi(close=df["close"], length=cfg.rsi.length)

    result = df.join([bb, macd, rsi.rename("RSI")])

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
        ema_series = ta.ema(close=result["close"], length=ema_len)
        result[f"EMA{ema_len}"] = ema_series

    # --- ATR (opsiyonel) ---
    if getattr(cfg, "risk", None) and cfg.risk.use_atr:
        atr_len = cfg.risk.atr_length
        logger.debug(f"Computing ATR (length={atr_len})")
        atr = ta.atr(high=result["high"], low=result["low"], close=result["close"], length=atr_len)
        result["ATR"] = atr if isinstance(atr, pd.Series) else atr.iloc[:, 0]
    
    # --- Gelişmiş indikatörler ---
    logger.debug("Adding advanced indicators for better signal quality...")
    try:
        result = add_all_advanced_indicators(result)
        logger.debug("Successfully added advanced indicators")
    except Exception as e:
        logger.warning(f"Failed to add some advanced indicators: {e}")
        # Continue without advanced indicators if they fail

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
