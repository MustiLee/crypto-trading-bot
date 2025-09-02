import pytest
import pandas as pd
import numpy as np
from src.strategy.rules import lower_touch, upper_touch
from src.strategy.bb_macd_strategy import build_signals
from utils.configEX import StrategyConfig, BollingerConfig, MACDConfig, RSIConfig, ExecutionConfig


class TestSignalRules:
    def test_lower_touch_basic(self):
        close = pd.Series([10.0, 9.5, 9.0, 10.5])
        lower = pd.Series([9.0, 9.0, 9.0, 9.0])
        
        expected = pd.Series([False, True, True, False])
        result = lower_touch(close, lower, tolerance=0.0)
        
        pd.testing.assert_series_equal(result, expected)
    
    def test_upper_touch_basic(self):
        close = pd.Series([10.0, 10.5, 11.0, 9.5])
        upper = pd.Series([10.5, 10.5, 10.5, 10.5])
        
        expected = pd.Series([False, True, True, False])
        result = upper_touch(close, upper, tolerance=0.0)
        
        pd.testing.assert_series_equal(result, expected)
    
    def test_touch_with_tolerance(self):
        close = pd.Series([10.1, 9.9])
        lower = pd.Series([10.0, 10.0])
        upper = pd.Series([10.0, 10.0])
        
        result_lower = lower_touch(close, lower, tolerance=0.01)
        result_upper = upper_touch(close, upper, tolerance=0.01)
        
        expected_lower = pd.Series([True, True])  
        expected_upper = pd.Series([True, True])  
        
        pd.testing.assert_series_equal(result_lower, expected_lower)
        pd.testing.assert_series_equal(result_upper, expected_upper)
    
    def test_negative_tolerance_raises_error(self):
        close = pd.Series([10.0])
        band = pd.Series([9.0])
        
        with pytest.raises(ValueError, match="Tolerance must be non-negative"):
            lower_touch(close, band, tolerance=-0.01)
        
        with pytest.raises(ValueError, match="Tolerance must be non-negative"):
            upper_touch(close, band, tolerance=-0.01)


class TestBBMACDStrategy:
    def create_test_data(self) -> pd.DataFrame:
        dates = pd.date_range('2023-01-01', periods=10, freq='1H')
        
        data = {
            'close': [100, 99, 98, 101, 102, 97, 103, 104, 96, 105],
            'BBL': [95, 95, 95, 96, 96, 94, 97, 97, 93, 98],
            'BBM': [100, 100, 100, 101, 101, 99, 102, 102, 98, 103],
            'BBU': [105, 105, 105, 106, 106, 104, 107, 107, 103, 108],
            'MACD': [0.5, -0.5, 0.8, 1.2, -0.2, 1.1, -0.1, 0.6, 1.5, -0.3],
            'MACD_SIGNAL': [0.0, 0.0, 0.5, 1.0, 0.0, 1.0, 0.0, 0.5, 1.0, 0.0],
            'RSI': [45, 30, 25, 65, 70, 35, 75, 80, 20, 85]
        }
        
        return pd.DataFrame(data, index=dates)
    
    def create_basic_config(self) -> StrategyConfig:
        return StrategyConfig(
            bollinger=BollingerConfig(length=20, std=2.0),
            macd=MACDConfig(fast=12, slow=26, signal=9),
            rsi=RSIConfig(length=14, use_filter=False),
            execution=ExecutionConfig(touch_tolerance_pct=0.0)
        )
    
    def test_build_signals_basic(self):
        df = self.create_test_data()
        config = self.create_basic_config()
        
        buy_signals, sell_signals = build_signals(df, config)
        
        assert isinstance(buy_signals, pd.Series)
        assert isinstance(sell_signals, pd.Series)
        assert len(buy_signals) == len(df)
        assert len(sell_signals) == len(df)
        assert buy_signals.dtype == bool
        assert sell_signals.dtype == bool
    
    def test_build_signals_with_rsi_filter(self):
        df = self.create_test_data()
        config = self.create_basic_config()
        config.rsi.use_filter = True
        config.rsi.rsi_buy_max = 40.0
        config.rsi.rsi_sell_min = 60.0
        
        buy_signals, sell_signals = build_signals(df, config)
        
        assert isinstance(buy_signals, pd.Series)
        assert isinstance(sell_signals, pd.Series)
        assert buy_signals.dtype == bool
        assert sell_signals.dtype == bool
    
    def test_known_signal_pattern(self):
        dates = pd.date_range('2023-01-01', periods=5, freq='1H')
        
        df = pd.DataFrame({
            'close': [95.0, 94.0, 106.0, 107.0, 100.0],       
            'BBL': [95.0, 95.0, 95.0, 95.0, 95.0],            
            'BBU': [105.0, 105.0, 105.0, 105.0, 105.0],       
            'MACD': [-1.0, 1.0, 1.0, -1.0, 0.0],              
            'MACD_SIGNAL': [0.0, 0.0, 0.0, 0.0, 0.0],         
            'RSI': [30, 35, 70, 75, 50]
        }, index=dates)
        
        config = self.create_basic_config()
        buy_signals, sell_signals = build_signals(df, config)
        
        expected_buy = pd.Series([False, True, False, False, False], index=dates)
        expected_sell = pd.Series([False, False, False, True, False], index=dates)
        
        pd.testing.assert_series_equal(buy_signals, expected_buy, check_names=False)
        pd.testing.assert_series_equal(sell_signals, expected_sell, check_names=False)
    
    def test_missing_columns_raises_error(self):
        df = pd.DataFrame({'close': [100, 101, 102]})
        config = self.create_basic_config()
        
        with pytest.raises(ValueError, match="Missing required columns"):
            build_signals(df, config)
    
    def test_missing_rsi_with_filter_raises_error(self):
        df = pd.DataFrame({
            'close': [100, 101, 102],
            'BBL': [95, 95, 95],
            'BBU': [105, 105, 105],
            'MACD': [0.5, 1.0, -0.5],
            'MACD_SIGNAL': [0.0, 0.0, 0.0]
        })
        
        config = self.create_basic_config()
        config.rsi.use_filter = True
        
        with pytest.raises(ValueError, match="RSI filter enabled but RSI column not found"):
            build_signals(df, config)
    
    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=['close', 'BBL', 'BBU', 'MACD', 'MACD_SIGNAL'])
        config = self.create_basic_config()
        
        buy_signals, sell_signals = build_signals(df, config)
        
        assert len(buy_signals) == 0
        assert len(sell_signals) == 0
        assert buy_signals.dtype == bool
        assert sell_signals.dtype == bool
    
    def test_tolerance_effect(self):
        dates = pd.date_range('2023-01-01', periods=3, freq='1H')
        
        df = pd.DataFrame({
            'close': [95.5, 104.5, 100.0],      
            'BBL': [95.0, 95.0, 95.0],          
            'BBU': [105.0, 105.0, 105.0],       
            'MACD': [-1.0, 1.0, 0.0],           
            'MACD_SIGNAL': [0.0, 0.0, 0.0],     
        }, index=dates)
        
        config_no_tol = self.create_basic_config()
        config_no_tol.execution.touch_tolerance_pct = 0.0
        
        config_with_tol = self.create_basic_config()
        config_with_tol.execution.touch_tolerance_pct = 0.01  # 1%
        
        buy_no_tol, sell_no_tol = build_signals(df, config_no_tol)
        buy_with_tol, sell_with_tol = build_signals(df, config_with_tol)
        
        assert buy_no_tol.sum() <= buy_with_tol.sum()
        assert sell_no_tol.sum() <= sell_with_tol.sum()