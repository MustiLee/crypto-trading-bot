import typer
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional
from loguru import logger

# Hepsini mutlak yap:
from src.utils.config import AppConfig
from src.utils.logging import setup_logging
from src.data.ohlcv_downloader import fetch_ohlcv, validate_symbol_timeframe
from src.data.cache import DataCache
from src.indicators.factory import add_indicators, validate_indicators
from src.strategy.bb_macd_strategy import build_signals, analyze_signal_timing
from src.backtest.engine import run_backtest, create_backtest_report, print_backtest_summary




app = typer.Typer(help="Trading Bot CLI - Bollinger Bands + MACD Strategy")


@app.command()
def fetch(
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Trading pair symbol (e.g., BTC/USDT)"),
    timeframe: Optional[str] = typer.Option(None, "--timeframe", "-t", help="Timeframe (e.g., 5m, 1h, 1d)"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Number of candles to fetch"),
    force: bool = typer.Option(False, "--force", "-f", help="Force refresh, ignore cache"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
):
    setup_logging(debug)
    
    try:
        config = AppConfig()
        
        symbol = symbol or config.symbol
        timeframe = timeframe or config.timeframe
        limit = limit or config.candle_limit
        
        logger.info(f"Fetching {symbol} {timeframe} data (limit: {limit})")
        
        cache = DataCache(config.data_dir)
        
        if not force and cache.is_fresh(symbol, timeframe, max_age_hours=1):
            logger.info("Using cached data (use --force to refresh)")
            df = cache.load(symbol, timeframe)
        else:
            validate_symbol_timeframe(config.exchange, symbol, timeframe)
            df = fetch_ohlcv(config.exchange, symbol, timeframe, limit)
            cache.save(df, symbol, timeframe)
        
        if df is not None and not df.empty:
            logger.info(f"Successfully fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")
            logger.info(f"Data saved to: {cache.get_cache_path(symbol, timeframe)}")
        else:
            logger.error("Failed to fetch data")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        raise typer.Exit(1)


@app.command()
def indicators(
    input_file: Optional[str] = typer.Option(None, "--input", "-i", help="Input CSV file path"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output CSV file path"),
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Symbol for auto file naming"),
    timeframe: Optional[str] = typer.Option(None, "--timeframe", "-t", help="Timeframe for auto file naming"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to strategy config YAML file"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
):
    setup_logging(debug)
    
    try:
        app_config = AppConfig()
        
        # Load custom strategy config if provided
        if config_path:
            app_config.reload_strategy(config_path)
        
        if input_file is None:
            symbol = symbol or app_config.symbol
            timeframe = timeframe or app_config.timeframe
            cache = DataCache(app_config.data_dir)
            input_file = str(cache.get_cache_path(symbol, timeframe))
        
        if output_file is None:
            input_path = Path(input_file)
            output_file = str(input_path.parent / f"{input_path.stem}_ind.csv")
        
        logger.info(f"Loading data from: {input_file}")
        
        if not Path(input_file).exists():
            logger.error(f"Input file not found: {input_file}")
            logger.info("Try running: python -m src.cli fetch first")
            raise typer.Exit(1)
        
        df = pd.read_csv(input_file, index_col=0, parse_dates=True)
        
        if df.empty:
            logger.error("Input file is empty")
            raise typer.Exit(1)
        
        logger.info(f"Loaded {len(df)} rows")
        
        df_with_indicators = add_indicators(df, app_config.strategy)
        
        validate_indicators(df_with_indicators)
        
        df_with_indicators.to_csv(output_file)
        
        logger.info(f"Saved {len(df_with_indicators)} rows with indicators to: {output_file}")
        logger.info(f"Added columns: BBL, BBM, BBU, MACD, MACD_SIGNAL, MACD_HIST, RSI")
        
    except Exception as e:
        logger.error(f"Indicators computation failed: {e}")
        raise typer.Exit(1)


@app.command()
def backtest(
    input_file: Optional[str] = typer.Option(None, "--input", "-i", help="Input CSV with indicators"),
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Symbol for auto file naming"),
    timeframe: Optional[str] = typer.Option(None, "--timeframe", "-t", help="Timeframe for auto file naming"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", "-o", help="Output directory for reports"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to strategy config YAML file"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
):
    setup_logging(debug)
    
    try:
        app_config = AppConfig()
        
        # Load custom strategy config if provided
        if config_path:
            app_config.reload_strategy(config_path)
        
        if input_file is None:
            symbol = symbol or app_config.symbol
            timeframe = timeframe or app_config.timeframe
            cache = DataCache(app_config.data_dir)
            base_path = cache.get_cache_path(symbol, timeframe)
            input_file = str(base_path.parent / f"{base_path.stem}_ind.csv")
        
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = app_config.reports_dir / f"backtest_{timestamp}"
        else:
            output_dir = Path(output_dir)
        
        logger.info(f"Loading data with indicators from: {input_file}")
        
        if not Path(input_file).exists():
            logger.error(f"Input file not found: {input_file}")
            logger.info("Try running: python -m src.cli indicators first")
            raise typer.Exit(1)
        
        df = pd.read_csv(input_file, index_col=0, parse_dates=True)
        
        if df.empty:
            logger.error("Input file is empty")
            raise typer.Exit(1)
        
        validate_indicators(df)
        
        logger.info(f"Loaded {len(df)} rows with indicators")
        
        buy_signals, sell_signals = build_signals(df, app_config.strategy)
        
        signal_analysis = analyze_signal_timing(df, buy_signals, sell_signals)
        logger.info(f"Signal analysis: {signal_analysis}")
        
        pf = run_backtest(df, buy_signals, sell_signals, app_config.strategy)
        
        report = create_backtest_report(pf, df, buy_signals, sell_signals, app_config.strategy, output_dir)
        
        print_backtest_summary(report)
        
        logger.info(f"Backtest results saved to: {output_dir}")
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise typer.Exit(1)


@app.command()
def pipeline(
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Trading pair symbol"),
    timeframe: Optional[str] = typer.Option(None, "--timeframe", "-t", help="Timeframe"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Number of candles"),
    force: bool = typer.Option(False, "--force", "-f", help="Force refresh data"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to strategy config YAML file"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
):
    setup_logging(debug)
    
    logger.info("Running full pipeline: fetch → indicators → backtest")
    
    try:
        logger.info("Step 1: Fetching data...")
        fetch(symbol, timeframe, limit, force, debug)
        
        logger.info("Step 2: Computing indicators...")
        indicators(None, None, symbol, timeframe, config_path, debug)
        
        logger.info("Step 3: Running backtest...")
        backtest(None, symbol, timeframe, None, config_path, debug)
        
        logger.info("Pipeline completed successfully!")
        
    except typer.Exit:
        raise
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise typer.Exit(1)


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
):
    config = AppConfig()
    
    if show:
        typer.echo("Current Configuration:")
        typer.echo(f"Exchange: {config.exchange}")
        typer.echo(f"Symbol: {config.symbol}")
        typer.echo(f"Timeframe: {config.timeframe}")
        typer.echo(f"Candle Limit: {config.candle_limit}")
        typer.echo(f"Data Dir: {config.data_dir}")
        typer.echo(f"Reports Dir: {config.reports_dir}")
        typer.echo("\nStrategy Parameters:")
        typer.echo(f"  Bollinger Bands: length={config.strategy.bollinger.length}, std={config.strategy.bollinger.std}")
        typer.echo(f"  MACD: fast={config.strategy.macd.fast}, slow={config.strategy.macd.slow}, signal={config.strategy.macd.signal}")
        typer.echo(f"  RSI: length={config.strategy.rsi.length}, use_filter={config.strategy.rsi.use_filter}")
        if config.strategy.rsi.use_filter:
            typer.echo(f"    RSI buy_max={config.strategy.rsi.rsi_buy_max}, sell_min={config.strategy.rsi.rsi_sell_min}")
        typer.echo(f"  Execution: fee={config.strategy.execution.fee_pct:.4%}, slippage={config.strategy.execution.slippage_pct:.4%}")
        typer.echo(f"  Backtest: initial_cash=${config.strategy.backtest.initial_cash:,.2f}, size_pct={config.strategy.backtest.size_pct:.1%}")


if __name__ == "__main__":
    app()