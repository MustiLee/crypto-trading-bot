# Trading Bot - Bollinger Bands + MACD Strategy

A minimal yet comprehensive Python trading bot that implements a Bollinger Bands + MACD crossover strategy with RSI filtering. Built for research and educational purposes.

**⚠️ Disclaimer: This is for research and educational purposes only. Not financial advice. Past performance does not guarantee future results.**

## Features

- **Data Fetching**: Pull OHLCV data from any CCXT-supported exchange
- **Technical Indicators**: Bollinger Bands, MACD, RSI using pandas_ta  
- **Signal Generation**: Buy on BB lower touch + MACD bullish crossover, Sell on BB upper touch + MACD bearish crossover
- **Backtesting**: Comprehensive backtesting with vectorbt
- **CLI Interface**: Simple commands to run the full pipeline
- **Configurable**: All parameters adjustable via YAML config
- **Visualization**: Charts and plots for analysis
- **Testing**: Full test suite included

## Strategy Rules

### Buy Signal (Long Entry)
- **Condition 1**: Close price touches or goes below Bollinger Band lower line
- **Condition 2**: MACD line crosses ABOVE signal line on the same candle (bullish crossover)
- **Optional RSI Filter**: RSI <= `rsi_buy_max` (default: 40, disabled by default)

### Sell Signal (Exit/Short Entry)  
- **Condition 1**: Close price touches or goes above Bollinger Band upper line
- **Condition 2**: MACD line crosses BELOW signal line on the same candle (bearish crossover)
- **Optional RSI Filter**: RSI >= `rsi_sell_min` (default: 60, disabled by default)

### No Look-Ahead Bias
All crossover detection uses `shift(1)` to ensure signals are based on completed candles only.

## Quick Start

### 1. Setup Environment

```bash
# Clone or create the project directory
cd trader-bot

# Create virtual environment  
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env if needed (default settings work for demo)
```

### 2. Run the Complete Pipeline

```bash
# Fetch data, compute indicators, and run backtest in one command
python -m src.cli pipeline --symbol BTC/USDT --timeframe 5m --limit 1000

# Or run steps individually:
python -m src.cli fetch --symbol BTC/USDT --timeframe 5m --limit 1000
python -m src.cli indicators
python -m src.cli backtest
```

### 3. View Results

Results are saved in `reports/backtest_YYYYMMDD_HHMMSS/`:
- `equity_curve.png` - Portfolio performance chart
- `signals_chart.png` - Price action with buy/sell signals  
- `trades.csv` - Detailed trade records
- `report.json` - Complete metrics

## Project Structure

```
trader-bot/
├── README.md
├── requirements.txt
├── .env.example
├── config/
│   └── strategy.yaml          # Strategy parameters
├── src/
│   ├── cli.py                 # Main CLI interface
│   ├── utils/
│   │   ├── config.py          # Configuration loading
│   │   └── logging.py         # Logging setup
│   ├── data/
│   │   ├── ohlcv_downloader.py # CCXT data fetching
│   │   └── cache.py           # File-based caching
│   ├── indicators/
│   │   └── factory.py         # Technical indicators
│   ├── strategy/
│   │   ├── rules.py           # Signal rules (crossovers, touches)
│   │   └── bb_macd_strategy.py # Main strategy logic
│   ├── backtest/
│   │   ├── engine.py          # Backtest execution
│   │   └── metrics.py         # Performance metrics
│   └── live/
│       └── trader.py          # Live trading placeholder
├── notebooks/
│   └── quick_checks.ipynb     # Jupyter analysis notebook
├── tests/
│   ├── test_crossovers.py     # Crossover logic tests
│   ├── test_signals.py        # Signal generation tests  
│   └── test_backtest_smoke.py # Integration tests
├── data/                      # CSV data files (auto-created)
└── reports/                   # Backtest results (auto-created)
```

## CLI Commands

### Data Fetching
```bash
# Fetch with default settings from .env
python -m src.cli fetch

# Fetch specific symbol/timeframe
python -m src.cli fetch --symbol ETH/USDT --timeframe 1h --limit 500

# Force refresh (ignore cache)
python -m src.cli fetch --force
```

### Technical Indicators  
```bash
# Compute indicators for cached data
python -m src.cli indicators

# Specify input/output files
python -m src.cli indicators --input data/BTCUSDT_5m.csv --output data/BTCUSDT_5m_with_indicators.csv
```

### Backtesting
```bash
# Run backtest with default settings
python -m src.cli backtest

# Specify custom output directory
python -m src.cli backtest --output-dir reports/my_test

# Enable debug logging
python -m src.cli backtest --debug
```

### Configuration
```bash
# View current configuration
python -m src.cli config --show
```

## Configuration

### Environment Variables (.env)
```bash
EXCHANGE=binance
SYMBOL=BTC/USDT  
TIMEFRAME=5m
CANDLE_LIMIT=1000
```

### Strategy Parameters (config/strategy.yaml)
```yaml
bollinger:
  length: 20        # Bollinger Band period
  std: 2.0         # Standard deviation multiplier

macd:
  fast: 12         # Fast EMA period
  slow: 26         # Slow EMA period  
  signal: 9        # Signal line EMA period

rsi:
  length: 14       # RSI calculation period
  use_filter: false # Enable RSI filtering
  rsi_buy_max: 40  # Max RSI for buy signals
  rsi_sell_min: 60 # Min RSI for sell signals

execution:
  touch_tolerance_pct: 0.0  # Band touch tolerance (0 = exact)
  slippage_pct: 0.0005     # Slippage assumption
  fee_pct: 0.0004          # Trading fee assumption

backtest:
  initial_cash: 10000      # Starting capital
  size_pct: 0.99           # Position size (99% of capital)
  allow_short: false       # Enable short selling
  plot: true               # Generate charts
```

## Example Output

```
2023-12-01 10:30:15 | INFO | Fetching BTC/USDT 5m data from binance (limit: 1000)
2023-12-01 10:30:18 | INFO | Successfully fetched 1000 candles from 2023-11-28 to 2023-12-01
2023-12-01 10:30:19 | INFO | Computing technical indicators...
2023-12-01 10:30:20 | INFO | Generated 12 buy signals and 8 sell signals
2023-12-01 10:30:21 | INFO | Running backtest with vectorbt...

============================================================
BACKTEST RESULTS SUMMARY  
============================================================
Final Portfolio Value: $11,247.83
Initial Portfolio Value: $10,000.00
Total Return: 12.48%
CAGR: 15.23%
Max Drawdown: -4.21%
Sharpe Ratio: 1.847
Win Rate: 62.5%
Profit Factor: 2.14
Total Trades: 8
Average Trade: 1.46%
Best Trade: 5.23%
Worst Trade: -1.87%
Total Fees Paid: $12.34
============================================================
```

## Testing

Run the test suite:
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_crossovers.py

# Run with coverage
pytest --cov=src
```

## Code Quality

Format and lint the code:
```bash
# Format code
black .

# Lint code  
ruff .
```

## Jupyter Analysis

Open the analysis notebook:
```bash
jupyter notebook notebooks/quick_checks.ipynb
```

The notebook includes:
- Interactive charts of price action and indicators
- Signal visualization
- Strategy performance analysis
- Parameter experimentation

## Supported Exchanges

Any exchange supported by CCXT can be used by changing the `EXCHANGE` environment variable:
- `binance` (default)
- `coinbase` 
- `kraken`
- `ftx`
- `huobi`
- And 100+ others

## Supported Timeframes

Common timeframes (exchange-dependent):
- `1m`, `3m`, `5m`, `15m`, `30m`
- `1h`, `2h`, `4h`, `6h`, `8h`, `12h`  
- `1d`, `3d`, `1w`, `1M`

## Advanced Usage

### Custom Strategy Parameters

Edit `config/strategy.yaml` to experiment with different settings:

```yaml
# More sensitive BB strategy  
bollinger:
  length: 10
  std: 1.5

# Faster MACD
macd:
  fast: 8
  slow: 17
  signal: 5

# Enable RSI filtering
rsi:
  use_filter: true
  rsi_buy_max: 35
  rsi_sell_min: 65
```

### Running Multiple Backtests

```bash
# Test different symbols
python -m src.cli pipeline --symbol ETH/USDT
python -m src.cli pipeline --symbol ADA/USDT  
python -m src.cli pipeline --symbol SOL/USDT

# Test different timeframes
python -m src.cli pipeline --timeframe 15m
python -m src.cli pipeline --timeframe 1h
python -m src.cli pipeline --timeframe 4h
```

### Debugging Signals

Enable debug logging to see detailed signal analysis:
```bash
python -m src.cli backtest --debug
```

This will show:
- Individual signal conditions
- MACD crossover detection
- Bollinger Band touch analysis
- RSI filter application

## Performance Optimization

For better performance with large datasets:

1. **Reduce Data Size**: Use smaller `--limit` values for initial testing
2. **Cache Management**: Data is automatically cached, use `--force` only when needed  
3. **Timeframe Selection**: Higher timeframes (1h, 4h) process faster than lower (1m, 5m)
4. **Indicator Periods**: Shorter periods reduce the warm-up data needed

## Troubleshooting

### Common Issues

**1. "Symbol not found" error**
```bash
# Check available symbols for your exchange
python -c "import ccxt; print(list(ccxt.binance().load_markets().keys())[:20])"
```

**2. "Rate limited" error**  
The downloader has built-in retry logic. If it persists:
- Wait a few minutes between requests
- Use a different exchange
- Reduce the candle limit

**3. "No signals generated"**
- Try different timeframes or symbols
- Adjust strategy parameters in `config/strategy.yaml`
- Check if RSI filtering is too restrictive

**4. Import errors**
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Debug Mode

Enable detailed logging:
```bash
python -m src.cli pipeline --debug
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run tests: `pytest`
4. Format code: `black . && ruff .`
5. Commit changes: `git commit -m "Add feature"`
6. Push and create a Pull Request

## Docker Deployment

The bot includes production-ready Docker support for easy deployment and scaling.

### 🐳 **Quick Start with Docker**

```bash
# Build the image
docker build -t trader-bot .

# Run a quick backtest
docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/reports:/app/reports trader-bot pipeline --symbol BTC/USDT --timeframe 5m --limit 1000

# Run with docker-compose (recommended)
docker-compose up bot
```

### **Docker Commands**

```bash
# Fetch data
docker run --rm -v $(pwd)/data:/app/data trader-bot fetch --symbol ETH/USDT --timeframe 1h

# Compute indicators
docker run --rm -v $(pwd)/data:/app/data trader-bot indicators

# Run backtest
docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/reports:/app/reports trader-bot backtest

# Complete pipeline
docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/reports:/app/reports trader-bot pipeline
```

### **Docker Compose Features**

The `docker-compose.yml` provides:

- **Main service**: Interactive bot runs
- **Scheduler service**: Automated periodic backtests
- **Volume mounts**: Persistent data and reports
- **Environment configuration**: Easy parameter changes

```bash
# Basic usage
docker-compose up bot

# Run with scheduler (every 6 hours)
docker-compose --profile scheduler up -d

# Override command
docker-compose run --rm bot config --show
```

### **Production Deployment**

For production environments:

```bash
# Build optimized image
docker build -t trader-bot:prod --target base .

# Deploy with resource limits
docker run -d \
  --name trader-bot-prod \
  --memory=2g \
  --cpus=1.0 \
  --restart=unless-stopped \
  -v /opt/trader/data:/app/data \
  -v /opt/trader/reports:/app/reports \
  -v /opt/trader/config:/app/config:ro \
  -e TZ=UTC \
  trader-bot:prod pipeline --symbol BTC/USDT --timeframe 1h
```

### **Docker Environment Variables**

```yaml
environment:
  - EXCHANGE=binance
  - SYMBOL=BTC/USDT  
  - TIMEFRAME=5m
  - CANDLE_LIMIT=1000
  - TZ=UTC
  - PYTHONUNBUFFERED=1
```

### **Multi-Stage Build Benefits**

- **Optimized size**: Production image excludes dev tools
- **Security**: Runs as non-root user (UID 10001)
- **Caching**: Efficient layer caching for faster rebuilds
- **Dependencies**: Pinned versions for reproducibility

## Roadmap

- [ ] Additional technical indicators (Stochastic, Williams %R)
- [ ] Multiple timeframe analysis
- [ ] Portfolio optimization  
- [ ] Risk management features
- [ ] Web dashboard
- [ ] Paper trading mode
- [ ] Live trading implementation (currently placeholder)
- [ ] Kubernetes deployment manifests
- [ ] Monitoring and alerting integration

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- **pandas_ta**: Technical analysis library
- **vectorbt**: Backtesting framework  
- **CCXT**: Cryptocurrency exchange integration
- **typer**: CLI framework

---

**Remember**: This tool is for educational and research purposes. Always validate strategies thoroughly before considering real trading. Markets are unpredictable, and past performance does not guarantee future results.