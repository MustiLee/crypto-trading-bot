import pytest
import pandas as pd
import numpy as np
from src.strategy.rules import bullish_cross, bearish_cross


class TestCrossovers:
    def test_bullish_cross_basic(self):
        macd = pd.Series([1.0, 0.5, 1.5, 2.0])
        signal = pd.Series([1.5, 1.0, 1.0, 1.5])
        
        expected = pd.Series([False, False, True, False])
        result = bullish_cross(macd, signal)
        
        pd.testing.assert_series_equal(result, expected)
    
    def test_bearish_cross_basic(self):
        macd = pd.Series([2.0, 1.5, 0.5, 1.0])
        signal = pd.Series([1.5, 1.0, 1.0, 1.5])
        
        expected = pd.Series([False, False, True, False])
        result = bearish_cross(macd, signal)
        
        pd.testing.assert_series_equal(result, expected)
    
    def test_no_crossover(self):
        macd = pd.Series([1.0, 1.5, 2.0, 2.5])
        signal = pd.Series([0.5, 1.0, 1.5, 2.0])
        
        expected_bullish = pd.Series([False, False, False, False])
        expected_bearish = pd.Series([False, False, False, False])
        
        pd.testing.assert_series_equal(bullish_cross(macd, signal), expected_bullish)
        pd.testing.assert_series_equal(bearish_cross(macd, signal), expected_bearish)
    
    def test_multiple_crossovers(self):
        macd = pd.Series([0.5, 1.5, 0.5, 1.5, 0.5])
        signal = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0])
        
        expected_bullish = pd.Series([False, True, False, True, False])
        expected_bearish = pd.Series([False, False, True, False, True])
        
        pd.testing.assert_series_equal(bullish_cross(macd, signal), expected_bullish)
        pd.testing.assert_series_equal(bearish_cross(macd, signal), expected_bearish)
    
    def test_equal_values_no_cross(self):
        macd = pd.Series([1.0, 1.0, 1.0, 1.0])
        signal = pd.Series([1.0, 1.0, 1.0, 1.0])
        
        expected = pd.Series([False, False, False, False])
        
        pd.testing.assert_series_equal(bullish_cross(macd, signal), expected)
        pd.testing.assert_series_equal(bearish_cross(macd, signal), expected)
    
    def test_single_value_series(self):
        macd = pd.Series([1.0])
        signal = pd.Series([0.5])
        
        expected = pd.Series([False])
        
        pd.testing.assert_series_equal(bullish_cross(macd, signal), expected)
        pd.testing.assert_series_equal(bearish_cross(macd, signal), expected)
    
    def test_empty_series(self):
        macd = pd.Series(dtype=float)
        signal = pd.Series(dtype=float)
        
        expected = pd.Series(dtype=bool)
        
        result_bullish = bullish_cross(macd, signal)
        result_bearish = bearish_cross(macd, signal)
        
        assert len(result_bullish) == 0
        assert len(result_bearish) == 0
        assert result_bullish.dtype == bool
        assert result_bearish.dtype == bool
    
    def test_mismatched_lengths(self):
        macd = pd.Series([1.0, 2.0])
        signal = pd.Series([0.5])
        
        with pytest.raises(ValueError, match="must have same length"):
            bullish_cross(macd, signal)
        
        with pytest.raises(ValueError, match="must have same length"):
            bearish_cross(macd, signal)
    
    def test_with_nan_values(self):
        macd = pd.Series([np.nan, 1.5, 2.0, 1.0])
        signal = pd.Series([1.0, 1.0, 1.5, 1.5])
        
        result_bullish = bullish_cross(macd, signal)
        result_bearish = bearish_cross(macd, signal)
        
        expected_bullish = pd.Series([False, False, False, False])
        expected_bearish = pd.Series([False, False, True, False])
        
        pd.testing.assert_series_equal(result_bullish, expected_bullish)
        pd.testing.assert_series_equal(result_bearish, expected_bearish)
    
    def test_crossover_detection_precision(self):
        macd = pd.Series([0.999999, 1.000001])
        signal = pd.Series([1.000001, 0.999999])
        
        expected_bullish = pd.Series([False, True])
        expected_bearish = pd.Series([False, False])
        
        pd.testing.assert_series_equal(bullish_cross(macd, signal), expected_bullish)
        pd.testing.assert_series_equal(bearish_cross(macd, signal), expected_bearish)
    
    def test_crossover_at_zero(self):
        macd = pd.Series([-0.5, 0.5, -0.5])
        signal = pd.Series([0.0, 0.0, 0.0])
        
        expected_bullish = pd.Series([False, True, False])
        expected_bearish = pd.Series([False, False, True])
        
        pd.testing.assert_series_equal(bullish_cross(macd, signal), expected_bullish)
        pd.testing.assert_series_equal(bearish_cross(macd, signal), expected_bearish)