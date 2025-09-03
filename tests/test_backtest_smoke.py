import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.backtest.engine import run_backtest
from src.utils.config import StrategyConfig
from src.strategy.bb_macd_strategy import build_signals


class TestBacktestSmoke:
    def create_sample_data(self, n_periods: int = 200) -> pd.DataFrame:
        np.random.seed(42)
        
        start_date = datetime(2023, 1, 1)
        dates = [start_date + timedelta(hours=i) for i in range(n_periods)]
        
        base_price = 100
        price_changes = np.random.normal(0, 0.01, n_periods)
        prices = [base_price]
        
        for change in price_changes[1:]:
            prices.append(prices[-1] * (1 + change))
        
        high_prices = [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices]
        low_prices = [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices]
        volumes = np.random.uniform(1000, 10000, n_periods)
        
        df = pd.DataFrame({
            'open': prices,
            'high': high_prices,
            'low': low_prices,
            'close': prices,
            'volume': volumes
        }, index=pd.DatetimeIndex(dates))
        
        return df
    
    def add_mock_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df['close']
        
        df['BBL'] = close * 0.98
        df['BBM'] = close
        df['BBU'] = close * 1.02
        
        macd_line = np.random.uniform(-0.5, 0.5, len(df))
        signal_line = np.random.uniform(-0.5, 0.5, len(df))
        
        df['MACD'] = macd_line
        df['MACD_SIGNAL'] = signal_line
        df['MACD_HIST'] = macd_line - signal_line
        
        df['RSI'] = np.random.uniform(20, 80, len(df))
        
        return df
    
    def test_backtest_completes_successfully(self):
        df = self.create_sample_data(200)
        df = self.add_mock_indicators(df)
        
        config = StrategyConfig()
        
        buy_signals, sell_signals = build_signals(df, config)
        
        pf = run_backtest(df, buy_signals, sell_signals, config)
        
        assert pf is not None
        
        stats = pf.stats()
        assert 'Start Value' in stats
        assert 'End Value' in stats
        assert 'Total Trades' in stats
        
        assert stats['Start Value'] == config.backtest.initial_cash
        assert stats['End Value'] > 0
        assert stats['Total Trades'] >= 0
    
    def test_backtest_with_no_signals(self):
        df = self.create_sample_data(100)
        df = self.add_mock_indicators(df)
        
        config = StrategyConfig()
        
        buy_signals = pd.Series([False] * len(df), index=df.index)
        sell_signals = pd.Series([False] * len(df), index=df.index)
        
        pf = run_backtest(df, buy_signals, sell_signals, config)
        
        stats = pf.stats()
        assert stats['Total Trades'] == 0
        assert abs(stats['End Value'] - stats['Start Value']) < 1.0  # Should be approximately equal (minus small fees)
    
    def test_backtest_with_guaranteed_signals(self):
        df = self.create_sample_data(50)
        df = self.add_mock_indicators(df)
        
        config = StrategyConfig()
        
        buy_signals = pd.Series([False] * len(df), index=df.index)
        sell_signals = pd.Series([False] * len(df), index=df.index)
        
        buy_signals.iloc[10] = True
        sell_signals.iloc[20] = True
        buy_signals.iloc[30] = True
        sell_signals.iloc[40] = True
        
        pf = run_backtest(df, buy_signals, sell_signals, config)
        
        stats = pf.stats()
        assert stats['Total Trades'] > 0
        assert stats['Total Trades'] <= 4  # Should not exceed our signal count
    
    def test_backtest_handles_empty_dataframe(self):
        columns = ['open', 'high', 'low', 'close', 'volume', 'BBL', 'BBM', 'BBU', 'MACD', 'MACD_SIGNAL', 'RSI']
        df = pd.DataFrame(columns=columns)
        df.index = pd.DatetimeIndex([])
        
        config = StrategyConfig()
        
        buy_signals = pd.Series(dtype=bool, index=df.index)
        sell_signals = pd.Series(dtype=bool, index=df.index)
        
        with pytest.raises(ValueError, match="Cannot run backtest on empty DataFrame"):
            run_backtest(df, buy_signals, sell_signals, config)
    
    def test_backtest_with_mismatched_signal_length(self):
        df = self.create_sample_data(100)
        df = self.add_mock_indicators(df)
        
        config = StrategyConfig()
        
        buy_signals = pd.Series([True, False], index=df.index[:2])
        sell_signals = pd.Series([False, True], index=df.index[:2])
        
        with pytest.raises(ValueError, match="must have same length"):
            run_backtest(df, buy_signals, sell_signals, config)
    
    def test_backtest_metrics_are_reasonable(self):
        df = self.create_sample_data(300)
        df = self.add_mock_indicators(df)
        
        config = StrategyConfig()
        config.backtest.initial_cash = 10000.0
        
        buy_signals, sell_signals = build_signals(df, config)
        
        pf = run_backtest(df, buy_signals, sell_signals, config)
        
        stats = pf.stats()
        
        assert stats['Start Value'] == 10000.0
        assert stats['End Value'] > 0
        assert isinstance(stats['Total Trades'], (int, np.integer))
        assert stats['Total Trades'] >= 0
        
        if stats['Total Trades'] > 0:
            assert 'Win Rate [%]' in stats
            assert 0 <= stats['Win Rate [%]'] <= 100
            
            assert 'Max Drawdown [%]' in stats
            assert stats['Max Drawdown [%]'] >= 0  # Drawdown is reported as positive percentage
    
    def test_different_configuration_parameters(self):
        df = self.create_sample_data(150)
        df = self.add_mock_indicators(df)
        
        config = StrategyConfig()
        config.backtest.initial_cash = 5000.0
        config.execution.fee_pct = 0.001
        config.execution.slippage_pct = 0.0005
        
        buy_signals, sell_signals = build_signals(df, config)
        
        pf = run_backtest(df, buy_signals, sell_signals, config)
        
        stats = pf.stats()
        assert stats['Start Value'] == 5000.0
        
        if stats['Total Trades'] > 0:
            assert stats['Total Fees Paid'] > 0
    
    def test_backtest_reproducibility(self):
        np.random.seed(123)
        df1 = self.create_sample_data(100)
        df1 = self.add_mock_indicators(df1)
        
        np.random.seed(123)
        df2 = self.create_sample_data(100)
        df2 = self.add_mock_indicators(df2)
        
        config = StrategyConfig()
        
        buy1, sell1 = build_signals(df1, config)
        buy2, sell2 = build_signals(df2, config)
        
        pd.testing.assert_frame_equal(df1, df2)
        pd.testing.assert_series_equal(buy1, buy2)
        pd.testing.assert_series_equal(sell1, sell2)
        
        pf1 = run_backtest(df1, buy1, sell1, config)
        pf2 = run_backtest(df2, buy2, sell2, config)
        
        stats1 = pf1.stats()
        stats2 = pf2.stats()
        
        assert abs(stats1['End Value'] - stats2['End Value']) < 0.01
        assert stats1['Total Trades'] == stats2['Total Trades']