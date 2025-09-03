"""
Real-time strategy testing service for user-defined strategies
"""

import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from loguru import logger

from ..data.ohlcv_downloader import OHLCVDownloader
from ..indicators.factory import add_indicators
from ..strategy.advanced_strategy import build_advanced_signals
from ..strategy.flexible_strategy import build_flexible_signals
from ..backtest.engine import run_backtest, create_backtest_report
from ..utils.config import StrategyConfig
from .models import User


class StrategyTester:
    """Service for testing user-defined strategies in real-time"""
    
    def __init__(self):
        self.downloader = OHLCVDownloader()
    
    async def test_strategy(self, user_id: uuid.UUID, strategy_config: Dict[str, Any], 
                           symbol: str = "BTCUSDT", timeframe: str = "1h",
                           test_days: int = 90) -> Dict[str, Any]:
        """
        Test a user-defined strategy with real market data
        
        Args:
            user_id: User UUID for logging
            strategy_config: Strategy configuration dictionary
            symbol: Trading symbol to test
            timeframe: Timeframe for testing
            test_days: Number of days of historical data to use
            
        Returns:
            Dictionary containing test results and performance metrics
        """
        try:
            logger.info(f"Starting strategy test for user {user_id}, symbol {symbol}")
            
            # Download historical data
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=test_days)
            
            df = await self.downloader.download_ohlcv(symbol, timeframe, start_date, end_date)
            
            if df.empty:
                return {
                    "success": False,
                    "error": f"No historical data available for {symbol}",
                    "data_points": 0
                }
            
            logger.info(f"Downloaded {len(df)} data points for {symbol}")
            
            # Create temporary strategy config
            temp_config = self._create_strategy_config(strategy_config)
            
            # Add indicators
            df_with_indicators = add_indicators(df.copy(), temp_config)
            
            # Generate signals based on strategy type
            strategy_type = strategy_config.get('strategy_type', 'quality_over_quantity')
            
            if strategy_type in ['quality_over_quantity', 'trend_momentum', 'volatility_breakout']:
                buy_signals, sell_signals = build_advanced_signals(
                    df_with_indicators, temp_config, strategy_type
                )
            else:
                buy_signals, sell_signals = build_flexible_signals(
                    df_with_indicators, temp_config, strategy_type
                )
            
            # Run backtest
            portfolio = run_backtest(df_with_indicators, buy_signals, sell_signals, temp_config)
            
            # Calculate detailed metrics
            metrics = self._calculate_detailed_metrics(
                portfolio, df_with_indicators, buy_signals, sell_signals, temp_config
            )
            
            # Generate signal analysis
            signal_analysis = self._analyze_signals(
                df_with_indicators, buy_signals, sell_signals, symbol
            )
            
            # Create performance summary
            performance_summary = self._create_performance_summary(metrics, signal_analysis)
            
            result = {
                "success": True,
                "symbol": symbol,
                "timeframe": timeframe,
                "test_period": f"{test_days} days",
                "data_points": len(df),
                "strategy_type": strategy_type,
                "metrics": metrics,
                "signal_analysis": signal_analysis,
                "performance_summary": performance_summary,
                "chart_data": self._prepare_chart_data(df_with_indicators, buy_signals, sell_signals),
                "recommendations": self._generate_recommendations(metrics, signal_analysis)
            }
            
            logger.info(f"Strategy test completed for user {user_id}: {metrics.get('total_return_pct', 0):.2f}% return")
            return result
            
        except Exception as e:
            logger.error(f"Strategy test failed for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "data_points": 0
            }
    
    async def quick_test_strategy(self, strategy_config: Dict[str, Any], 
                                 symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """
        Quick strategy test for immediate feedback (last 30 days)
        
        Args:
            strategy_config: Strategy configuration
            symbol: Trading symbol
            
        Returns:
            Quick test results
        """
        return await self.test_strategy(
            user_id=uuid.uuid4(),  # Temporary ID for anonymous testing
            strategy_config=strategy_config,
            symbol=symbol,
            timeframe="4h",  # Faster timeframe for quick results
            test_days=30     # Shorter period for speed
        )
    
    def _create_strategy_config(self, user_config: Dict[str, Any]) -> StrategyConfig:
        """Convert user configuration to StrategyConfig object"""
        config = StrategyConfig()
        
        # Set backtest parameters
        risk_mgmt = user_config.get('risk_management', {})
        config.backtest.size_pct = risk_mgmt.get('position_size_pct', 0.05)
        config.backtest.initial_cash = 10000.0
        config.backtest.allow_short = False
        
        # Set execution parameters
        config.execution.fee_pct = 0.001
        config.execution.slippage_pct = 0.0005
        config.execution.touch_tolerance_pct = user_config.get('touch_tolerance', 0.02)
        
        return config
    
    def _calculate_detailed_metrics(self, portfolio, df, buy_signals, sell_signals, config) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        try:
            stats = portfolio.stats()
            returns = portfolio.returns()
            
            # Basic metrics
            final_value = float(stats.get('End Value', 10000.0))
            initial_value = float(stats.get('Start Value', 10000.0))
            total_return_pct = (final_value / initial_value - 1) * 100
            
            # Risk metrics
            max_drawdown_pct = float(stats.get('Max Drawdown [%]', 0.0))
            win_rate_pct = float(stats.get('Win Rate [%]', 0.0))
            
            # Trading metrics
            total_trades = int(stats.get('Total Trades', 0))
            avg_trade_pct = float(stats.get('Avg Trade [%]', 0.0))
            best_trade_pct = float(stats.get('Best Trade [%]', 0.0))
            worst_trade_pct = float(stats.get('Worst Trade [%]', 0.0))
            
            # Calculate additional metrics
            profit_factor = float(stats.get('Profit Factor', 0.0))
            sharpe_ratio = 0.0
            if len(returns) > 1:
                try:
                    sharpe_ratio = float(returns.sharpe_ratio())
                except:
                    sharpe_ratio = 0.0
            
            # Signal metrics
            total_buy_signals = int(buy_signals.sum())
            total_sell_signals = int(sell_signals.sum())
            signal_efficiency = (total_trades / max(total_buy_signals + total_sell_signals, 1)) * 100
            
            # Risk-adjusted return
            risk_adjusted_return = total_return_pct / max(max_drawdown_pct, 1.0)
            
            return {
                "final_value": final_value,
                "initial_value": initial_value,
                "total_return_pct": total_return_pct,
                "max_drawdown_pct": max_drawdown_pct,
                "sharpe_ratio": sharpe_ratio,
                "win_rate_pct": win_rate_pct,
                "profit_factor": profit_factor,
                "total_trades": total_trades,
                "avg_trade_pct": avg_trade_pct,
                "best_trade_pct": best_trade_pct,
                "worst_trade_pct": worst_trade_pct,
                "total_buy_signals": total_buy_signals,
                "total_sell_signals": total_sell_signals,
                "signal_efficiency": signal_efficiency,
                "risk_adjusted_return": risk_adjusted_return,
                "total_fees": float(stats.get('Total Fees Paid', 0.0))
            }
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {
                "final_value": 10000.0,
                "initial_value": 10000.0,
                "total_return_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe_ratio": 0.0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "total_trades": 0,
                "avg_trade_pct": 0.0,
                "best_trade_pct": 0.0,
                "worst_trade_pct": 0.0,
                "total_buy_signals": 0,
                "total_sell_signals": 0,
                "signal_efficiency": 0.0,
                "risk_adjusted_return": 0.0,
                "total_fees": 0.0
            }
    
    def _analyze_signals(self, df, buy_signals, sell_signals, symbol) -> Dict[str, Any]:
        """Analyze trading signals quality"""
        try:
            total_periods = len(df)
            buy_count = int(buy_signals.sum())
            sell_count = int(sell_signals.sum())
            
            # Signal frequency
            buy_frequency = (buy_count / total_periods) * 100
            sell_frequency = (sell_count / total_periods) * 100
            
            # Signal distribution over time
            signal_dates = []
            if buy_count > 0:
                buy_dates = df[buy_signals].index.tolist()
                signal_dates.extend([{"type": "BUY", "date": date.isoformat(), "price": float(df.loc[date, 'close'])} 
                                   for date in buy_dates[-10:]])  # Last 10 signals
            
            if sell_count > 0:
                sell_dates = df[sell_signals].index.tolist()
                signal_dates.extend([{"type": "SELL", "date": date.isoformat(), "price": float(df.loc[date, 'close'])} 
                                   for date in sell_dates[-10:]])  # Last 10 signals
            
            # Sort by date
            signal_dates.sort(key=lambda x: x['date'])
            
            # Signal strength analysis
            rsi_at_buy = []
            rsi_at_sell = []
            
            if 'RSI' in df.columns:
                if buy_count > 0:
                    rsi_at_buy = df[buy_signals]['RSI'].dropna().tolist()
                if sell_count > 0:
                    rsi_at_sell = df[sell_signals]['RSI'].dropna().tolist()
            
            return {
                "total_buy_signals": buy_count,
                "total_sell_signals": sell_count,
                "buy_frequency_pct": buy_frequency,
                "sell_frequency_pct": sell_frequency,
                "recent_signals": signal_dates,
                "avg_rsi_at_buy": float(np.mean(rsi_at_buy)) if rsi_at_buy else None,
                "avg_rsi_at_sell": float(np.mean(rsi_at_sell)) if rsi_at_sell else None,
                "signal_balance": abs(buy_count - sell_count),
                "signal_quality_score": self._calculate_signal_quality_score(
                    buy_frequency, sell_frequency, buy_count, sell_count
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing signals: {e}")
            return {
                "total_buy_signals": 0,
                "total_sell_signals": 0,
                "buy_frequency_pct": 0.0,
                "sell_frequency_pct": 0.0,
                "recent_signals": [],
                "avg_rsi_at_buy": None,
                "avg_rsi_at_sell": None,
                "signal_balance": 0,
                "signal_quality_score": 0.0
            }
    
    def _calculate_signal_quality_score(self, buy_freq, sell_freq, buy_count, sell_count) -> float:
        """Calculate a quality score for signal generation"""
        try:
            # Ideal frequency is 1-5% (not too rare, not too frequent)
            freq_score = 100 - abs(2.5 - (buy_freq + sell_freq) / 2) * 10
            freq_score = max(0, min(100, freq_score))
            
            # Balance score (buy and sell signals should be relatively balanced)
            if buy_count + sell_count > 0:
                balance_ratio = min(buy_count, sell_count) / max(buy_count, sell_count)
                balance_score = balance_ratio * 100
            else:
                balance_score = 0
            
            # Minimum signal count score
            min_signals = min(buy_count, sell_count)
            count_score = min(100, min_signals * 10)  # 10 points per signal up to 100
            
            # Weighted average
            quality_score = (freq_score * 0.4 + balance_score * 0.3 + count_score * 0.3)
            return round(quality_score, 2)
            
        except:
            return 0.0
    
    def _create_performance_summary(self, metrics, signal_analysis) -> Dict[str, Any]:
        """Create human-readable performance summary"""
        total_return = metrics['total_return_pct']
        max_drawdown = metrics['max_drawdown_pct']
        win_rate = metrics['win_rate_pct']
        total_trades = metrics['total_trades']
        
        # Performance grade
        grade = "F"
        if total_return > 20 and max_drawdown < 10 and win_rate > 60:
            grade = "A"
        elif total_return > 10 and max_drawdown < 15 and win_rate > 50:
            grade = "B"
        elif total_return > 5 and max_drawdown < 20 and win_rate > 40:
            grade = "C"
        elif total_return > 0 and max_drawdown < 25:
            grade = "D"
        
        # Risk level
        risk_level = "Low"
        if max_drawdown > 20:
            risk_level = "High"
        elif max_drawdown > 10:
            risk_level = "Medium"
        
        # Trading frequency
        trading_freq = "Low"
        if total_trades > 50:
            trading_freq = "High"
        elif total_trades > 20:
            trading_freq = "Medium"
        
        # Overall recommendation
        recommendation = "Not Recommended"
        if grade in ["A", "B"]:
            recommendation = "Recommended"
        elif grade == "C":
            recommendation = "Consider with Caution"
        
        return {
            "performance_grade": grade,
            "risk_level": risk_level,
            "trading_frequency": trading_freq,
            "recommendation": recommendation,
            "summary_text": f"This strategy achieved a {total_return:.1f}% return with {max_drawdown:.1f}% maximum drawdown over the test period. "
                           f"It generated {total_trades} trades with a {win_rate:.1f}% win rate. "
                           f"Risk level is {risk_level.lower()} and trading frequency is {trading_freq.lower()}."
        }
    
    def _prepare_chart_data(self, df, buy_signals, sell_signals) -> Dict[str, Any]:
        """Prepare data for frontend charts"""
        try:
            # Limit data points for performance (last 200 points)
            chart_df = df.tail(200).copy()
            chart_buy = buy_signals.tail(200)
            chart_sell = sell_signals.tail(200)
            
            # Price data
            price_data = []
            for idx, row in chart_df.iterrows():
                price_data.append({
                    "timestamp": idx.isoformat(),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": float(row['volume'])
                })
            
            # Signal data
            signal_data = []
            buy_indices = chart_df[chart_buy].index
            sell_indices = chart_df[chart_sell].index
            
            for idx in buy_indices:
                signal_data.append({
                    "timestamp": idx.isoformat(),
                    "type": "BUY",
                    "price": float(chart_df.loc[idx, 'close'])
                })
            
            for idx in sell_indices:
                signal_data.append({
                    "timestamp": idx.isoformat(),
                    "type": "SELL",
                    "price": float(chart_df.loc[idx, 'close'])
                })
            
            # Indicator data
            indicator_data = {}
            if 'BBU' in chart_df.columns:
                indicator_data['bollinger_bands'] = {
                    "upper": chart_df['BBU'].fillna(0).tolist(),
                    "middle": chart_df['BBM'].fillna(0).tolist(),
                    "lower": chart_df['BBL'].fillna(0).tolist()
                }
            
            if 'RSI' in chart_df.columns:
                indicator_data['rsi'] = chart_df['RSI'].fillna(50).tolist()
            
            if 'MACD' in chart_df.columns:
                indicator_data['macd'] = {
                    "macd": chart_df['MACD'].fillna(0).tolist(),
                    "signal": chart_df['MACD_SIGNAL'].fillna(0).tolist(),
                    "histogram": chart_df['MACD_HIST'].fillna(0).tolist()
                }
            
            return {
                "price_data": price_data,
                "signals": signal_data,
                "indicators": indicator_data,
                "timestamps": [idx.isoformat() for idx in chart_df.index]
            }
            
        except Exception as e:
            logger.error(f"Error preparing chart data: {e}")
            return {
                "price_data": [],
                "signals": [],
                "indicators": {},
                "timestamps": []
            }
    
    def _generate_recommendations(self, metrics, signal_analysis) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        total_return = metrics['total_return_pct']
        max_drawdown = metrics['max_drawdown_pct']
        win_rate = metrics['win_rate_pct']
        total_trades = metrics['total_trades']
        signal_quality = signal_analysis['signal_quality_score']
        
        if total_return < 0:
            recommendations.append("❌ Strategy is losing money. Consider adjusting parameters or using a different approach.")
        
        if max_drawdown > 20:
            recommendations.append("⚠️ High risk detected. Consider tighter stop-losses or smaller position sizes.")
        
        if win_rate < 40:
            recommendations.append("📉 Low win rate. Try adjusting entry/exit conditions for better signal quality.")
        
        if total_trades < 10:
            recommendations.append("📊 Too few trades for reliable results. Consider relaxing signal conditions or extending test period.")
        
        if signal_quality < 50:
            recommendations.append("🔧 Signal quality can be improved. Consider fine-tuning indicator parameters.")
        
        if total_return > 10 and max_drawdown < 10:
            recommendations.append("✅ Good performance! This strategy shows promise for live trading.")
        
        if win_rate > 60:
            recommendations.append("🎯 Excellent win rate! Your signal timing is working well.")
        
        if len(recommendations) == 0:
            recommendations.append("📈 Strategy shows moderate performance. Consider minor adjustments for optimization.")
        
        return recommendations[:5]  # Limit to top 5 recommendations