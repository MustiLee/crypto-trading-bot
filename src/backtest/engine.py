import pandas as pd
import vectorbt as vbt
from datetime import datetime
from pathlib import Path
from loguru import logger
from src.utils.config import StrategyConfig


def run_backtest(
    df: pd.DataFrame, 
    buy_signals: pd.Series, 
    sell_signals: pd.Series, 
    cfg: StrategyConfig
) -> vbt.Portfolio:
    logger.info("Running backtest with vectorbt...")
    
    if len(df) != len(buy_signals) or len(df) != len(sell_signals):
        raise ValueError("DataFrame and signal series must have same length")
    
    if df.empty:
        raise ValueError("Cannot run backtest on empty DataFrame")
    
    if not buy_signals.any() and not sell_signals.any():
        logger.warning("No signals found, backtest will have no trades")
    
    entries = buy_signals
    exits = sell_signals
    
    # Apply advanced exit conditions
    if hasattr(cfg, 'exits'):
        exits = apply_advanced_exits(df, buy_signals, sell_signals, cfg, entries)
    
    if not cfg.backtest.allow_short:
        logger.debug("Long-only mode: exits on sell signals or opposite entry signals")
        exits = exits | (buy_signals.shift(1).fillna(False) & sell_signals)
    
    logger.debug(f"Backtest parameters:")
    logger.debug(f"  Initial cash: ${cfg.backtest.initial_cash:,.2f}")
    logger.debug(f"  Position size: {cfg.backtest.size_pct:.1%}")
    logger.debug(f"  Fees: {cfg.execution.fee_pct:.4%}")
    logger.debug(f"  Slippage: {cfg.execution.slippage_pct:.4%}")
    
    try:
        pf = vbt.Portfolio.from_signals(
            close=df["close"],
            entries=entries,
            exits=exits,
            init_cash=cfg.backtest.initial_cash,
            fees=cfg.execution.fee_pct,
            slippage=cfg.execution.slippage_pct,
            freq='T' if 'm' in str(df.index.freq) else 'D',
            direction='longonly' if not cfg.backtest.allow_short else 'both'
        )
        
        logger.info("Backtest completed successfully")
        return pf
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise


def create_backtest_report(
    pf: vbt.Portfolio, 
    df: pd.DataFrame, 
    buy_signals: pd.Series, 
    sell_signals: pd.Series,
    cfg: StrategyConfig,
    output_dir: Path
) -> dict:
    logger.info("Creating backtest report...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    stats = pf.stats()
    
    try:
        returns = pf.returns()
        if len(returns) > 1:
            sharpe = returns.sharpe_ratio()
        else:
            sharpe = 0.0
            
        cagr = returns.vbt.returns.cagr() if len(returns) > 252 else 0.0
        
    except Exception as e:
        logger.warning(f"Could not calculate some metrics: {e}")
        sharpe = 0.0
        cagr = 0.0
    
    # Extract metrics safely with fallbacks
    def safe_get(key, default=0.0):
        try:
            val = stats.get(key, default)
            if pd.isna(val) or val == float('inf') or val == float('-inf'):
                return default
            return float(val)
        except:
            return default

    report = {
        'final_value': safe_get('End Value', 10000.0),
        'initial_value': safe_get('Start Value', 10000.0),
        'total_return_pct': (safe_get('End Value', 10000.0) / safe_get('Start Value', 10000.0) - 1) * 100,
        'cagr_pct': float(cagr * 100) if cagr and not pd.isna(cagr) else 0.0,
        'max_drawdown_pct': safe_get('Max Drawdown [%]', 0.0),
        'sharpe_ratio': float(sharpe) if sharpe and not pd.isna(sharpe) else 0.0,
        'win_rate_pct': safe_get('Win Rate [%]', 0.0),
        'profit_factor': safe_get('Profit Factor', 0.0) if safe_get('Profit Factor', 0.0) != float('inf') else 0.0,
        'total_trades': int(safe_get('Total Trades', 0)),
        'avg_trade_pct': safe_get('Avg Trade [%]', 0.0),
        'best_trade_pct': safe_get('Best Trade [%]', 0.0),
        'worst_trade_pct': safe_get('Worst Trade [%]', 0.0),
        'max_dd_duration': str(stats.get('Max Drawdown Duration', '0 days')),
        'total_fees': safe_get('Total Fees Paid', 0.0),
    }
    
    try:
        trades_df = pf.trades.records_readable
        if not trades_df.empty:
            trades_path = output_dir / "trades.csv"
            trades_df.to_csv(trades_path, index=False)
            logger.info(f"Saved trades to {trades_path}")
            
            report['trades_saved'] = str(trades_path)
        else:
            logger.warning("No trades to save")
            
    except Exception as e:
        logger.warning(f"Could not save trades: {e}")
    
    if cfg.backtest.plot:
        try:
            save_backtest_plots(pf, df, buy_signals, sell_signals, output_dir)
            report['plots_saved'] = True
        except Exception as e:
            logger.error(f"Failed to save plots: {e}")
            report['plots_saved'] = False
    
    report_path = output_dir / "report.json"
    import json
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Backtest report saved to {report_path}")
    
    return report


def save_backtest_plots(
    pf: vbt.Portfolio, 
    df: pd.DataFrame, 
    buy_signals: pd.Series, 
    sell_signals: pd.Series, 
    output_dir: Path
) -> None:
    import matplotlib.pyplot as plt
    
    logger.info("Creating backtest plots...")
    
    plt.style.use('default')
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    portfolio_value = pf.value()
    axes[0].plot(portfolio_value.index, portfolio_value.values, linewidth=1.5, color='blue', label='Portfolio Value')
    axes[0].set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Portfolio Value ($)', fontsize=12)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    
    drawdown = pf.drawdowns.drawdown
    axes[1].fill_between(drawdown.index, drawdown.values * 100, 0, 
                        color='red', alpha=0.3, label='Drawdown')
    axes[1].set_title('Drawdown (%)', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('Drawdown (%)', fontsize=12)
    axes[1].set_xlabel('Date', fontsize=12)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    
    plt.tight_layout()
    
    equity_path = output_dir / "equity_curve.png"
    plt.savefig(equity_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved equity curve to {equity_path}")
    plt.close()
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 12))
    
    axes[0].plot(df.index, df['close'], linewidth=1, color='black', label='Close Price')
    axes[0].plot(df.index, df['BBU'], linewidth=1, color='red', alpha=0.7, label='BB Upper')
    axes[0].plot(df.index, df['BBM'], linewidth=1, color='orange', alpha=0.7, label='BB Middle')
    axes[0].plot(df.index, df['BBL'], linewidth=1, color='green', alpha=0.7, label='BB Lower')
    
    buy_points = df[buy_signals]['close']
    sell_points = df[sell_signals]['close']
    
    if not buy_points.empty:
        axes[0].scatter(buy_points.index, buy_points.values, 
                       marker='^', color='green', s=60, label=f'Buy ({len(buy_points)})', zorder=5)
    
    if not sell_points.empty:
        axes[0].scatter(sell_points.index, sell_points.values, 
                       marker='v', color='red', s=60, label=f'Sell ({len(sell_points)})', zorder=5)
    
    axes[0].set_title('Price Action with Bollinger Bands and Signals', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Price', fontsize=12)
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(df.index, df['MACD'], linewidth=1, color='blue', label='MACD')
    axes[1].plot(df.index, df['MACD_SIGNAL'], linewidth=1, color='red', label='Signal')
    axes[1].bar(df.index, df['MACD_HIST'], width=1, alpha=0.3, color='gray', label='Histogram')
    axes[1].axhline(y=0, color='black', linestyle='-', alpha=0.3)
    
    if not buy_points.empty:
        axes[1].scatter(buy_points.index, df.loc[buy_points.index, 'MACD'], 
                       marker='^', color='green', s=60, zorder=5)
    
    if not sell_points.empty:
        axes[1].scatter(sell_points.index, df.loc[sell_points.index, 'MACD'], 
                       marker='v', color='red', s=60, zorder=5)
    
    axes[1].set_title('MACD with Crossover Signals', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('MACD', fontsize=12)
    axes[1].set_xlabel('Date', fontsize=12)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    signals_path = output_dir / "signals_chart.png"
    plt.savefig(signals_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved signals chart to {signals_path}")
    plt.close()


def print_backtest_summary(report: dict) -> None:
    logger.info("="*60)
    logger.info("BACKTEST RESULTS SUMMARY")
    logger.info("="*60)
    logger.info(f"Final Portfolio Value: ${report['final_value']:,.2f}")
    logger.info(f"Initial Portfolio Value: ${report['initial_value']:,.2f}")
    logger.info(f"Total Return: {report['total_return_pct']:.2f}%")
    logger.info(f"CAGR: {report['cagr_pct']:.2f}%")
    logger.info(f"Max Drawdown: {report['max_drawdown_pct']:.2f}%")
    logger.info(f"Sharpe Ratio: {report['sharpe_ratio']:.3f}")
    logger.info(f"Win Rate: {report['win_rate_pct']:.1f}%")
    logger.info(f"Profit Factor: {report['profit_factor']:.2f}")
    logger.info(f"Total Trades: {report['total_trades']}")
    
    if report['total_trades'] > 0:
        logger.info(f"Average Trade: {report['avg_trade_pct']:.2f}%")
        logger.info(f"Best Trade: {report['best_trade_pct']:.2f}%")
        logger.info(f"Worst Trade: {report['worst_trade_pct']:.2f}%")
    
    logger.info(f"Total Fees Paid: ${report['total_fees']:.2f}")
    logger.info("="*60)


def apply_advanced_exits(
    df: pd.DataFrame, 
    buy_signals: pd.Series, 
    sell_signals: pd.Series, 
    cfg: StrategyConfig,
    entries: pd.Series
) -> pd.Series:
    """Apply advanced exit conditions (ATR stops, time-based, midband exits)"""
    
    exits = sell_signals.copy()
    
    # Time-based exit
    if cfg.exits.time_based.use:
        logger.debug(f"Applying time-based exit (max bars: {cfg.exits.time_based.max_bars_in_trade})")
        time_exits = pd.Series(False, index=df.index)
        
        # Track positions and their entry times
        position = False
        entry_time = None
        
        for i, (timestamp, entry_signal) in enumerate(entries.items()):
            if entry_signal and not position:
                position = True
                entry_time = i
            elif exits[timestamp] and position:
                position = False
                entry_time = None
            elif position and entry_time is not None:
                bars_in_trade = i - entry_time
                if bars_in_trade >= cfg.exits.time_based.max_bars_in_trade:
                    time_exits[timestamp] = True
                    position = False
                    entry_time = None
        
        exits = exits | time_exits
    
    # Midband exit (exit longs at BB middle band)
    if cfg.exits.midband_exit.use:
        logger.debug("Applying midband exit (BB middle band)")
        if "BBM" not in df.columns:
            logger.warning("Midband exit enabled but BBM column not found")
        else:
            midband_exits = pd.Series(False, index=df.index)
            
            # Track positions
            position = False
            
            for i, (timestamp, entry_signal) in enumerate(entries.items()):
                if entry_signal and not position:
                    position = True
                elif exits[timestamp] and position:
                    position = False
                elif position and i > 0:
                    # Exit when price crosses above BB middle band (for longs)
                    prev_close = df["close"].iloc[i-1]
                    curr_close = df["close"].iloc[i]
                    bb_mid = df["BBM"].iloc[i]
                    
                    if prev_close < bb_mid and curr_close >= bb_mid:
                        midband_exits[timestamp] = True
                        position = False
            
            exits = exits | midband_exits
    
    # ATR-based stops and trailing stops
    if cfg.risk.use_atr:
        logger.debug(f"Applying ATR-based stops (stop_mult: {cfg.risk.stop_mult}, trail_mult: {cfg.risk.trail_mult})")
        if "ATR" not in df.columns:
            logger.warning("ATR risk management enabled but ATR column not found")
        else:
            atr_exits = pd.Series(False, index=df.index)
            
            # Track positions and stops
            position = False
            entry_price = None
            stop_loss = None
            trailing_stop = None
            highest_price = None
            
            for i, (timestamp, entry_signal) in enumerate(entries.items()):
                current_price = df["close"].iloc[i]
                atr_value = df["ATR"].iloc[i]
                
                if entry_signal and not position:
                    # Enter position
                    position = True
                    entry_price = current_price
                    stop_loss = entry_price - (cfg.risk.stop_mult * atr_value)
                    trailing_stop = None
                    highest_price = current_price
                    
                elif exits[timestamp] and position:
                    # Regular exit
                    position = False
                    entry_price = None
                    stop_loss = None
                    trailing_stop = None
                    highest_price = None
                    
                elif position:
                    # Update highest price for trailing stop
                    if current_price > highest_price:
                        highest_price = current_price
                        # Update trailing stop
                        new_trailing = highest_price - (cfg.risk.trail_mult * atr_value)
                        if trailing_stop is None or new_trailing > trailing_stop:
                            trailing_stop = new_trailing
                    
                    # Check stop conditions
                    hit_stop = current_price <= stop_loss
                    hit_trailing = trailing_stop is not None and current_price <= trailing_stop
                    
                    if hit_stop or hit_trailing:
                        atr_exits[timestamp] = True
                        position = False
                        entry_price = None
                        stop_loss = None
                        trailing_stop = None
                        highest_price = None
            
            exits = exits | atr_exits
    
    return exits