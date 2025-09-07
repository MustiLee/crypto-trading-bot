#!/usr/bin/env python3
"""
Live Trading Dashboard Runner
Starts the real-time trading dashboard with Binance WebSocket data
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path so `import src` works
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.realtime.web_server import TradingDashboardServer
from src.utils.logging import setup_logging
from loguru import logger


async def main():
    """Main entry point for live trading dashboard"""
    
    # Setup logging
    setup_logging(debug=True)
    
    logger.info("🚀 Starting Live Trading Dashboard")
    logger.info("=" * 50)
    logger.info("Strategy: Realistic1 (Winner Configuration)")  
    logger.info("Symbol: BTC/USDT")
    logger.info("Timeframe: 5m")
    logger.info("Data Source: Binance WebSocket")
    logger.info("=" * 50)
    
    # Create and start dashboard server
    server = TradingDashboardServer(
        symbol="btcusdt", 
        interval="5m", 
        port=8000
    )
    
    try:
        logger.info("🌐 Dashboard will be available at: http://localhost:8000")
        logger.info("Press Ctrl+C to stop...")
        
        await server.start()
        
    except KeyboardInterrupt:
        logger.info("👋 Received shutdown signal, stopping gracefully...")
    except Exception as e:
        logger.error(f"❌ Error running dashboard: {e}")
        raise
    finally:
        await server.stop()
        logger.info("✅ Dashboard stopped successfully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
