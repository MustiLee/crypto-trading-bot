# Trading Bot with Live Dashboard

A production-ready cryptocurrency trading bot with real-time dashboard, PostgreSQL integration, and Docker deployment.

## Features

🚀 **Real-time Trading Dashboard** - Live web interface with WebSocket updates  
📊 **Technical Analysis** - RSI, MACD, Bollinger Bands, ATR indicators  
🐘 **PostgreSQL Integration** - Persistent data storage and analytics  
🐳 **Docker Deployment** - Production-ready containerized setup  
⚡ **Live Data Streaming** - Real-time Binance WebSocket integration  
🎯 **Multiple Strategies** - Configurable trading algorithms  

## Quick Start

### Using Docker (Recommended)

```bash
cd deployment
docker-compose up -d
```

Access the dashboard at: http://localhost:8000  
Database: localhost:5433 (user: trader, password: trader_password)

### Manual Installation

```bash
pip install -r requirements-prod.txt
python scripts/run_live_dashboard.py
```

## Project Structure

```
├── src/                    # Core application code
│   ├── cli/               # Command-line interface
│   ├── config/            # Configuration management
│   ├── data/              # Data fetching and processing
│   ├── database/          # PostgreSQL integration
│   ├── indicators/        # Technical indicators
│   ├── realtime/          # Live data streaming
│   ├── signals/           # Trading signals
│   ├── strategies/        # Trading strategies
│   └── utils/             # Utilities
├── config/                # Strategy configurations
├── deployment/            # Docker and deployment files
├── scripts/               # Executable scripts
├── tests/                 # Test suite
├── docs/                  # Documentation
├── data/                  # Data storage (empty - using PostgreSQL)
└── reports/               # Analysis reports
```

## Documentation

- [Live Dashboard Guide](docs/LIVE_DASHBOARD_GUIDE.md)
- [Docker Setup](docs/DOCKER.md)
- [Backtest Analysis](docs/FINAL_BACKTEST_ANALYSIS_REPORT.md)

## Configuration

Edit `config/strategy.realistic1.yaml` to customize trading parameters:

```yaml
name: "Realistic1"
risk_management:
  max_risk_per_trade: 0.02
  atr_multiplier: 2.0
indicators:
  rsi_period: 14
  bb_period: 20
  macd_fast: 12
  macd_slow: 26
```

## License

MIT License