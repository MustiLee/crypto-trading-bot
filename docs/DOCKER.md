# Docker Deployment Guide

This guide covers deploying the trading bot using Docker for production environments.

## 🐳 **Quick Start**

### Build and Run
```bash
# Build the image
docker build -t trader-bot .

# Run a single backtest
docker run --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/reports:/app/reports \
  trader-bot pipeline --symbol BTC/USDT --timeframe 5m --limit 1000
```

### Using Docker Compose (Recommended)
```bash
# Run interactive bot
docker-compose up bot

# Run as daemon
docker-compose up -d bot

# View logs
docker-compose logs -f bot

# Run with scheduler (automated backtests)
docker-compose --profile scheduler up -d
```

## 📋 **Available Commands**

```bash
# Configuration
docker run --rm trader-bot config --show

# Fetch data only
docker run --rm -v $(pwd)/data:/app/data \
  trader-bot fetch --symbol ETH/USDT --timeframe 1h --limit 500

# Compute indicators
docker run --rm -v $(pwd)/data:/app/data \
  trader-bot indicators

# Run backtest
docker run --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/reports:/app/reports \
  trader-bot backtest

# Complete pipeline
docker run --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/reports:/app/reports \
  trader-bot pipeline --symbol BTC/USDT --timeframe 4h --limit 1000
```

## 🔧 **Environment Configuration**

### Environment Variables
Set these in your `.env` file or docker-compose environment:

```env
EXCHANGE=binance
SYMBOL=BTC/USDT
TIMEFRAME=5m
CANDLE_LIMIT=1000
TZ=UTC
MPLBACKEND=Agg
PYTHONUNBUFFERED=1
```

### Volume Mounts
- `/app/data` - OHLCV data and indicators cache
- `/app/reports` - Backtest results and charts
- `/app/config` - Strategy configuration files (read-only)

## 🚀 **Production Deployment**

### Single Container
```bash
docker run -d \
  --name trader-bot-prod \
  --restart=unless-stopped \
  --memory=2g \
  --cpus=1.5 \
  -v /opt/trader/data:/app/data \
  -v /opt/trader/reports:/app/reports \
  -v /opt/trader/config:/app/config:ro \
  -e TZ=UTC \
  -e EXCHANGE=binance \
  -e SYMBOL=BTC/USDT \
  -e TIMEFRAME=1h \
  trader-bot pipeline --limit 500
```

### Docker Compose Production
```yaml
version: "3.9"
services:
  trader:
    image: trader-bot:latest
    container_name: trading-bot
    restart: unless-stopped
    environment:
      - TZ=UTC
      - EXCHANGE=binance  
      - SYMBOL=BTC/USDT
      - TIMEFRAME=1h
      - CANDLE_LIMIT=500
    volumes:
      - /opt/trader/data:/app/data
      - /opt/trader/reports:/app/reports
      - /opt/trader/config:/app/config:ro
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.5'
    command: ["pipeline", "--limit", "500"]
```

## 📊 **Monitoring and Logging**

### View Logs
```bash
# Real-time logs
docker logs -f trader-bot

# Last 100 lines
docker logs --tail 100 trader-bot

# With timestamps
docker logs -t trader-bot
```

### Health Checks
```bash
# Check container status
docker ps

# Inspect container
docker inspect trader-bot

# Execute commands inside container
docker exec -it trader-bot python -m src.cli config --show
```

## 🔒 **Security Features**

- **Non-root user**: Runs as `appuser` (UID 10001)
- **Read-only configs**: Configuration mounted read-only
- **Minimal base**: Python 3.11 slim image
- **No secrets in image**: Environment variables for sensitive data
- **Resource limits**: Memory and CPU constraints

## 🎯 **Best Practices**

### 1. **Data Persistence**
```bash
# Create named volumes for better management
docker volume create trader-data
docker volume create trader-reports

docker run --rm \
  -v trader-data:/app/data \
  -v trader-reports:/app/reports \
  trader-bot pipeline
```

### 2. **Automated Scheduling**
```bash
# Run every 4 hours using cron
0 */4 * * * docker run --rm -v /opt/trader/data:/app/data -v /opt/trader/reports:/app/reports trader-bot pipeline --symbol BTC/USDT --timeframe 1h
```

### 3. **Multi-Symbol Deployment**
```yaml
version: "3.9"
services:
  btc-trader:
    image: trader-bot:latest
    environment:
      - SYMBOL=BTC/USDT
    volumes:
      - ./data/btc:/app/data
      - ./reports/btc:/app/reports

  eth-trader:
    image: trader-bot:latest
    environment:
      - SYMBOL=ETH/USDT
    volumes:
      - ./data/eth:/app/data
      - ./reports/eth:/app/reports
```

## 🐛 **Troubleshooting**

### Common Issues

1. **Permission Errors**
   ```bash
   # Fix file ownership
   sudo chown -R 10001:10001 data/ reports/
   ```

2. **Memory Issues**
   ```bash
   # Increase memory limit
   docker run --memory=4g trader-bot pipeline
   ```

3. **Network Issues**
   ```bash
   # Test connectivity
   docker run --rm trader-bot python -c "import ccxt; print(ccxt.binance().fetch_ticker('BTC/USDT'))"
   ```

4. **Missing Data**
   ```bash
   # Check data directory
   docker run --rm -v $(pwd)/data:/app/data trader-bot ls -la /app/data
   ```

### Debug Mode
```bash
# Run with debug logging
docker run --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/reports:/app/reports \
  trader-bot backtest --debug
```

## 📈 **Performance Optimization**

### Image Size Optimization
- Production image: ~800MB (no dev tools)
- Development image: ~1.2GB (with jupyter, tests)
- Multi-stage builds for smaller production images

### Resource Requirements
- **Memory**: 1-2GB recommended
- **CPU**: 1-2 cores sufficient
- **Storage**: 1GB for data/reports per symbol
- **Network**: Minimal (API calls only)

### Scaling
```bash
# Horizontal scaling with different symbols
docker-compose scale btc-trader=1 eth-trader=1 ada-trader=1

# Vertical scaling with resource limits
docker run --memory=4g --cpus=2.0 trader-bot pipeline
```

## 🔄 **Updates and Maintenance**

### Update Strategy
```bash
# Pull latest image
docker pull trader-bot:latest

# Graceful restart
docker-compose stop
docker-compose up -d
```

### Backup Data
```bash
# Backup data and reports
tar -czf trader-backup-$(date +%Y%m%d).tar.gz data/ reports/
```

### Clean Up
```bash
# Remove old containers
docker container prune

# Remove unused images
docker image prune

# Clean everything
docker system prune -a
```

## 📋 **Example Workflows**

### Daily Automated Trading
```bash
#!/bin/bash
# daily-trading.sh

# Morning: 4h analysis
docker run --rm -v /opt/trader/data:/app/data -v /opt/trader/reports:/app/reports \
  trader-bot pipeline --symbol BTC/USDT --timeframe 4h --limit 168

# Evening: 1h analysis  
docker run --rm -v /opt/trader/data:/app/data -v /opt/trader/reports:/app/reports \
  trader-bot pipeline --symbol ETH/USDT --timeframe 1h --limit 720
```

### Multi-Exchange Setup
```yaml
version: "3.9"
services:
  binance-trader:
    image: trader-bot:latest
    environment:
      - EXCHANGE=binance
      - SYMBOL=BTC/USDT
      
  coinbase-trader:
    image: trader-bot:latest
    environment:
      - EXCHANGE=coinbase
      - SYMBOL=BTC-USD
```

This Docker setup provides a robust, scalable, and secure deployment option for the trading bot in production environments.