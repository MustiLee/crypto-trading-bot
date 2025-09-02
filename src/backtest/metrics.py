import pandas as pd
import numpy as np
from typing import Dict, Optional
from loguru import logger


def calculate_returns_metrics(returns: pd.Series, risk_free_rate: float = 0.0) -> Dict[str, float]:
    if returns.empty:
        return {
            'total_return': 0.0,
            'cagr': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'calmar_ratio': 0.0
        }
    
    total_return = (1 + returns).prod() - 1
    
    periods_per_year = 252 if returns.index.freq == 'D' else 252 * 24 * 60 / 5 
    n_periods = len(returns)
    
    if n_periods > 1:
        cagr = (1 + total_return) ** (periods_per_year / n_periods) - 1
        volatility = returns.std() * np.sqrt(periods_per_year)
        
        excess_returns = returns - risk_free_rate / periods_per_year
        sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(periods_per_year) if returns.std() > 0 else 0.0
        
        downside_returns = returns[returns < 0]
        downside_volatility = downside_returns.std() * np.sqrt(periods_per_year) if len(downside_returns) > 0 else 0.0
        sortino_ratio = excess_returns.mean() / downside_volatility * np.sqrt(periods_per_year) if downside_volatility > 0 else 0.0
        
    else:
        cagr = 0.0
        volatility = 0.0
        sharpe_ratio = 0.0
        sortino_ratio = 0.0
    
    cumulative_returns = (1 + returns).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    calmar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0.0
    
    return {
        'total_return': total_return,
        'cagr': cagr,
        'volatility': volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'calmar_ratio': calmar_ratio
    }


def calculate_trade_metrics(trades_df: pd.DataFrame) -> Dict[str, float]:
    if trades_df.empty:
        return {
            'total_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_trade_return': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'avg_trade_duration': 0.0,
            'expectancy': 0.0
        }
    
    total_trades = len(trades_df)
    
    if 'Return' in trades_df.columns:
        returns = trades_df['Return']
    elif 'PnL' in trades_df.columns:
        returns = trades_df['PnL']
    else:
        logger.warning("No return column found in trades DataFrame")
        returns = pd.Series(dtype=float)
    
    if returns.empty:
        return {
            'total_trades': total_trades,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_trade_return': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'avg_trade_duration': 0.0,
            'expectancy': 0.0
        }
    
    winning_trades = returns[returns > 0]
    losing_trades = returns[returns < 0]
    
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
    
    total_wins = winning_trades.sum() if len(winning_trades) > 0 else 0.0
    total_losses = abs(losing_trades.sum()) if len(losing_trades) > 0 else 0.0
    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0.0
    
    avg_trade_return = returns.mean()
    avg_win = winning_trades.mean() if len(winning_trades) > 0 else 0.0
    avg_loss = losing_trades.mean() if len(losing_trades) > 0 else 0.0
    
    largest_win = winning_trades.max() if len(winning_trades) > 0 else 0.0
    largest_loss = losing_trades.min() if len(losing_trades) > 0 else 0.0
    
    if 'Exit Timestamp' in trades_df.columns and 'Entry Timestamp' in trades_df.columns:
        durations = pd.to_datetime(trades_df['Exit Timestamp']) - pd.to_datetime(trades_df['Entry Timestamp'])
        avg_trade_duration = durations.mean().total_seconds() / 3600  # in hours
    else:
        avg_trade_duration = 0.0
    
    expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss
    
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor if profit_factor != float('inf') else 999.0,
        'avg_trade_return': avg_trade_return,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'avg_trade_duration': avg_trade_duration,
        'expectancy': expectancy
    }


def calculate_drawdown_metrics(portfolio_values: pd.Series) -> Dict[str, float]:
    if portfolio_values.empty or len(portfolio_values) < 2:
        return {
            'max_drawdown': 0.0,
            'max_drawdown_duration': 0.0,
            'avg_drawdown': 0.0,
            'drawdown_periods': 0
        }
    
    running_max = portfolio_values.expanding().max()
    drawdown = (portfolio_values - running_max) / running_max
    
    max_drawdown = drawdown.min()
    
    in_drawdown = drawdown < 0
    drawdown_periods = 0
    current_dd_length = 0
    max_dd_length = 0
    
    for is_dd in in_drawdown:
        if is_dd:
            current_dd_length += 1
            max_dd_length = max(max_dd_length, current_dd_length)
        else:
            if current_dd_length > 0:
                drawdown_periods += 1
                current_dd_length = 0
    
    if current_dd_length > 0:
        drawdown_periods += 1
    
    avg_drawdown = drawdown[drawdown < 0].mean() if (drawdown < 0).any() else 0.0
    
    return {
        'max_drawdown': max_drawdown,
        'max_drawdown_duration': float(max_dd_length),
        'avg_drawdown': avg_drawdown,
        'drawdown_periods': drawdown_periods
    }


def format_metrics_report(metrics: Dict[str, float]) -> str:
    report_lines = [
        "=" * 50,
        "DETAILED METRICS REPORT",
        "=" * 50,
    ]
    
    if 'total_return' in metrics:
        report_lines.extend([
            "RETURN METRICS:",
            f"  Total Return: {metrics.get('total_return', 0) * 100:.2f}%",
            f"  CAGR: {metrics.get('cagr', 0) * 100:.2f}%",
            f"  Volatility (annualized): {metrics.get('volatility', 0) * 100:.2f}%",
            ""
        ])
    
    if 'sharpe_ratio' in metrics:
        report_lines.extend([
            "RISK METRICS:",
            f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.3f}",
            f"  Sortino Ratio: {metrics.get('sortino_ratio', 0):.3f}",
            f"  Calmar Ratio: {metrics.get('calmar_ratio', 0):.3f}",
            f"  Max Drawdown: {metrics.get('max_drawdown', 0) * 100:.2f}%",
            ""
        ])
    
    if 'total_trades' in metrics:
        report_lines.extend([
            "TRADE METRICS:",
            f"  Total Trades: {metrics.get('total_trades', 0)}",
            f"  Win Rate: {metrics.get('win_rate', 0) * 100:.1f}%",
            f"  Profit Factor: {metrics.get('profit_factor', 0):.2f}",
            f"  Expectancy: {metrics.get('expectancy', 0):.4f}",
            ""
        ])
        
        if metrics.get('total_trades', 0) > 0:
            report_lines.extend([
                "TRADE DETAILS:",
                f"  Average Trade: {metrics.get('avg_trade_return', 0):.4f}",
                f"  Average Win: {metrics.get('avg_win', 0):.4f}",
                f"  Average Loss: {metrics.get('avg_loss', 0):.4f}",
                f"  Largest Win: {metrics.get('largest_win', 0):.4f}",
                f"  Largest Loss: {metrics.get('largest_loss', 0):.4f}",
                f"  Avg Trade Duration: {metrics.get('avg_trade_duration', 0):.1f} hours",
                ""
            ])
    
    report_lines.append("=" * 50)
    
    return "\n".join(report_lines)