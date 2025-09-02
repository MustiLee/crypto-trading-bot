import os
from pathlib import Path
from typing import Optional, Literal
import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv


# -----------------------------
# Indicator / Strategy Sections
# -----------------------------
class BollingerConfig(BaseModel):
    length: int = 20
    std: float = 2.0

    class Config:
        extra = "ignore"


class MACDConfig(BaseModel):
    fast: int = 12
    slow: int = 26
    signal: int = 9

    class Config:
        extra = "ignore"


class RSIConfig(BaseModel):
    length: int = 14
    use_filter: bool = False
    rsi_buy_max: float = 40.0
    rsi_sell_min: float = 60.0

    class Config:
        extra = "ignore"


# --- NEW: Trend filter (EMA) ---
class EMATrendConfig(BaseModel):
    use: bool = False
    length: int = 200
    mode: Literal["long_only_above"] = "long_only_above"  # genişletilebilir

    class Config:
        extra = "ignore"


class FiltersConfig(BaseModel):
    ema_trend: EMATrendConfig = EMATrendConfig()

    class Config:
        extra = "ignore"


class ExecutionConfig(BaseModel):
    touch_tolerance_pct: float = 0.0
    slippage_pct: float = 0.0005
    fee_pct: float = 0.0004

    class Config:
        extra = "ignore"


# --- NEW: Risk (ATR) & Exits ---
class RiskConfig(BaseModel):
    use_atr: bool = False
    atr_length: int = 14
    stop_mult: float = 1.5
    trail_mult: float = 2.0

    class Config:
        extra = "ignore"


class TimeBasedExit(BaseModel):
    use: bool = False
    max_bars_in_trade: int = 60

    class Config:
        extra = "ignore"


class MidbandExit(BaseModel):
    use: bool = False

    class Config:
        extra = "ignore"


class ExitsConfig(BaseModel):
    time_based: TimeBasedExit = TimeBasedExit()
    midband_exit: MidbandExit = MidbandExit()

    class Config:
        extra = "ignore"


class BacktestConfig(BaseModel):
    initial_cash: float = 10000.0
    size_pct: float = 0.99
    allow_short: bool = False
    plot: bool = True

    class Config:
        extra = "ignore"


class StrategyConfig(BaseModel):
    bollinger: BollingerConfig = BollingerConfig()
    macd: MACDConfig = MACDConfig()
    rsi: RSIConfig = RSIConfig()
    filters: FiltersConfig = FiltersConfig()        # NEW
    execution: ExecutionConfig = ExecutionConfig()
    risk: RiskConfig = RiskConfig()                 # NEW
    exits: ExitsConfig = ExitsConfig()             # NEW
    backtest: BacktestConfig = BacktestConfig()

    class Config:
        extra = "ignore"


# -----------------------------
# App / Loader
# -----------------------------
class AppConfig:
    """
    .env + YAML strateji konfigürasyonunu yükler.
    - env vars: EXCHANGE, SYMBOL, TIMEFRAME, CANDLE_LIMIT
    - YAML: StrategyConfig (profil dosyalarıyla uyumlu)
    """

    def __init__(self, env_path: Optional[str] = None, config_path: Optional[str] = None):
        self.project_root = Path(__file__).parent.parent.parent

        # .env yolu
        if env_path is None:
            env_path = self.project_root / ".env"

        # YAML strateji yolu
        if config_path is None:
            config_path = self.project_root / "config" / "strategy.yaml"

        load_dotenv(env_path)

        # ENV (override edilebilir)
        self.exchange = os.getenv("EXCHANGE", "binance")
        self.symbol = os.getenv("SYMBOL", "BTC/USDT")
        self.timeframe = os.getenv("TIMEFRAME", "5m")
        self.candle_limit = int(os.getenv("CANDLE_LIMIT", "1000"))

        # YAML strateji
        self.strategy_path = Path(config_path)
        if self.strategy_path.exists():
            with open(self.strategy_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
                # pydantic extra="ignore" -> eski YAML'larla da uyumlu
                self.strategy = StrategyConfig(**config_data)
        else:
            self.strategy = StrategyConfig()

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def reports_dir(self) -> Path:
        return self.project_root / "reports"

    # --- convenience: dışarıdan farklı profil yüklemek için ---
    def reload_strategy(self, config_path: str) -> None:
        """
        Farklı bir YAML profili yükle (ör. --config ile).
        """
        new_path = Path(config_path)
        if not new_path.exists():
            raise FileNotFoundError(f"Strategy config not found: {new_path}")
        with new_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
            self.strategy = StrategyConfig(**raw)
        self.strategy_path = new_path


# --- opsiyonel: bağımsız yükleyici (CLI'da kullanışlı) ---
def load_strategy_config(config_path: Optional[str] = None) -> StrategyConfig:
    """
    Verilen YAML dosyasından StrategyConfig döner; None ise default path.
    CLI komutlarında doğrudan kullanılabilir.
    """
    project_root = Path(__file__).parent.parent.parent
    cfg_path = Path(config_path) if config_path else project_root / "config" / "strategy.yaml"
    if not cfg_path.exists():
        # Varsayılan StrategyConfig
        return StrategyConfig()
    with cfg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
        return StrategyConfig(**raw)
