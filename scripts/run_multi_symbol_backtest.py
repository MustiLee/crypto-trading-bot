#!/usr/bin/env python3
"""
Multi-Symbol Backtest Runner
Run backtests for BTC, ETH, XRP with their optimized strategies
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import yaml

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.backtest.engine import BacktestEngine
from src.data.ohlcv_downloader import OHLCVDownloader
from src.utils.logging import setup_logging
from loguru import logger


class MultiSymbolBacktester:
    """Run backtests for multiple symbols with their specific strategies"""
    
    def __init__(self):
        self.setup_logging()
        self.load_symbols()
        self.downloader = OHLCVDownloader()
        self.results = {}
        
    def setup_logging(self):
        """Setup logging"""
        setup_logging(debug=False)
        
    def load_symbols(self):
        """Load symbol configurations"""
        config_path = Path(__file__).parent.parent / "config" / "symbols.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        self.symbols = config['symbols']
        self.timeframes = config['timeframes']
        
        logger.info(f"Loaded symbols: {list(self.symbols.keys())}")
        logger.info(f"Timeframes: {self.timeframes}")
        
    async def download_data_for_symbol(self, symbol_key: str, symbol_config: dict, timeframe: str):
        """Download data for a specific symbol and timeframe"""
        try:
            logger.info(f"📥 Downloading {symbol_key} {timeframe} data...")
            
            # Download last 30 days of data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            df = await self.downloader.download_ohlcv(
                symbol=symbol_config['symbol'],
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                logger.error(f"No data downloaded for {symbol_key} {timeframe}")
                return None
                
            logger.success(f"✅ Downloaded {len(df)} candles for {symbol_key} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error downloading data for {symbol_key} {timeframe}: {e}")
            return None
    
    async def run_backtest_for_symbol(self, symbol_key: str, symbol_config: dict, 
                                    df: pd.DataFrame, timeframe: str):
        """Run backtest for a specific symbol"""
        try:
            logger.info(f"🔬 Running backtest for {symbol_key} {timeframe}...")
            
            # Load strategy config
            strategy_config_path = f"config/strategy.{symbol_config['strategy']}.yaml"
            
            # Initialize backtest engine
            strategy_type = symbol_config.get('strategy_type', 'flexible')
            engine = BacktestEngine(
                strategy_config_path=strategy_config_path,
                symbol=symbol_config['symbol'],
                strategy_type=strategy_type
            )
            
            # Run backtest
            results = engine.run_backtest(df)
            
            if results:
                logger.success(f"✅ Backtest completed for {symbol_key} {timeframe}")
                
                # Log key metrics
                metrics = results.get('metrics', {})
                logger.info(f"📊 {symbol_key} {timeframe} Results:")
                logger.info(f"   • Total Return: {metrics.get('total_return_pct', 0):.2f}%")
                logger.info(f"   • Win Rate: {metrics.get('win_rate', 0):.1f}%")
                logger.info(f"   • Total Trades: {metrics.get('total_trades', 0)}")
                logger.info(f"   • Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.3f}")
                
                return results
            else:
                logger.error(f"Backtest failed for {symbol_key} {timeframe}")
                return None
                
        except Exception as e:
            logger.error(f"Error running backtest for {symbol_key} {timeframe}: {e}")
            return None
    
    async def run_all_backtests(self):
        """Run backtests for all symbols and timeframes"""
        logger.info("🚀 Starting multi-symbol backtests...")
        logger.info("=" * 60)
        
        all_results = {}
        
        for symbol_key, symbol_config in self.symbols.items():
            logger.info(f"Processing {symbol_key} ({symbol_config['display_name']})...")
            
            symbol_results = {}
            
            for timeframe in self.timeframes:
                logger.info(f"Timeframe: {timeframe}")
                
                # Download data
                df = await self.download_data_for_symbol(symbol_key, symbol_config, timeframe)
                if df is None:
                    continue
                
                # Run backtest
                results = await self.run_backtest_for_symbol(symbol_key, symbol_config, df, timeframe)
                if results:
                    symbol_results[timeframe] = results
            
            all_results[symbol_key] = symbol_results
            logger.info("-" * 40)
        
        self.results = all_results
        return all_results
    
    def generate_comparison_report(self):
        """Generate comparison report across all symbols and timeframes"""
        logger.info("📋 Generating comparison report...")
        
        comparison = []
        
        for symbol_key, symbol_results in self.results.items():
            symbol_config = self.symbols[symbol_key]
            
            for timeframe, results in symbol_results.items():
                metrics = results.get('metrics', {})
                
                comparison.append({
                    'Symbol': symbol_key,
                    'Display Name': symbol_config['display_name'],
                    'Strategy': symbol_config['strategy'],
                    'Timeframe': timeframe,
                    'Total Return %': round(metrics.get('total_return_pct', 0), 2),
                    'Win Rate %': round(metrics.get('win_rate', 0), 1),
                    'Total Trades': metrics.get('total_trades', 0),
                    'Sharpe Ratio': round(metrics.get('sharpe_ratio', 0), 3),
                    'Max Drawdown %': round(metrics.get('max_drawdown_pct', 0), 2),
                    'Avg Trade Return %': round(metrics.get('avg_trade_return_pct', 0), 2)
                })
        
        # Convert to DataFrame for easy viewing
        df_comparison = pd.DataFrame(comparison)
        
        if not df_comparison.empty:
            # Sort by total return
            df_comparison = df_comparison.sort_values('Total Return %', ascending=False)
            
            logger.info("🏆 BACKTEST COMPARISON RESULTS:")
            logger.info("=" * 80)
            print(df_comparison.to_string(index=False))
            logger.info("=" * 80)
            
            # Find best performing strategy for each symbol
            logger.info("🎯 BEST STRATEGIES BY SYMBOL:")
            for symbol_key in self.symbols.keys():
                symbol_data = df_comparison[df_comparison['Symbol'] == symbol_key]
                if not symbol_data.empty:
                    best = symbol_data.iloc[0]
                    logger.info(f"{symbol_key}: {best['Timeframe']} - {best['Total Return %']}% return, {best['Win Rate %']}% win rate")
        
        # Save detailed results
        report_path = Path(__file__).parent.parent / "reports" / f"multi_symbol_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"💾 Detailed results saved to: {report_path}")
        
        return df_comparison


async def main():
    """Main function"""
    logger.info("🚀 Multi-Symbol Backtest Suite")
    logger.info("Testing BTC, ETH, XRP with optimized strategies")
    
    backtester = MultiSymbolBacktester()
    
    try:
        # Run all backtests
        results = await backtester.run_all_backtests()
        
        if results:
            # Generate comparison report
            comparison_df = backtester.generate_comparison_report()
            
            logger.success("✅ Multi-symbol backtests completed successfully!")
        else:
            logger.error("❌ No backtest results generated")
            
    except Exception as e:
        logger.error(f"❌ Error in multi-symbol backtest: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())