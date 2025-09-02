# Deployment

## Docker Setup

Start the trading bot with PostgreSQL:

```bash
docker-compose up -d
```

## Services

- **trader-postgres**: PostgreSQL database on port 5433
- **trader-dashboard**: Web dashboard on port 8000

## Environment Variables

Set in `docker-compose.yml`:

- `DATABASE_URL`: PostgreSQL connection string
- `SYMBOL`: Trading symbol (default: BTCUSDT)
- `TIMEFRAME`: Data timeframe (default: 5m)
- `STRATEGY`: Strategy name (default: Realistic1)

## Development

For CLI operations:

```bash
docker-compose --profile cli up bot
```