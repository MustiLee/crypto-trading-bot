#!/usr/bin/env python3
"""
Multi-Symbol Live Trading Dashboard Runner
Starts the real-time trading dashboard for BTC, ETH, and XRP
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path so `import src` works
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.realtime.multi_symbol_dashboard import MultiSymbolTradingDashboard
from src.utils.logging import setup_logging
from loguru import logger
import os


async def main():
    """Main entry point for multi-symbol trading dashboard"""
    
    # Setup logging
    setup_logging(debug=True)
    
    logger.info("🚀 Starting Multi-Symbol Trading Dashboard")
    logger.info("=" * 60)
    logger.info("Symbols: BTC/USDT, ETH/USDT, XRP/USDT")  
    logger.info("Timeframe: 5m")
    logger.info("Data Source: Binance WebSocket")
    logger.info("=" * 60)
    
    # Create and start multi-symbol dashboard
    port = int(os.getenv("PORT", "8080"))
    dashboard = MultiSymbolTradingDashboard(
        interval="5m", 
        port=port
    )
    
    try:
        logger.info(f"🌐 Multi-Symbol Dashboard will be available at: http://localhost:{port}")
        logger.info("💰 Tracking: BTC, ETH, XRP with live signals")
        logger.info("Press Ctrl+C to stop...")
        
        await dashboard.start()
        
    except KeyboardInterrupt:
        logger.info("👋 Received shutdown signal, stopping gracefully...")
    except Exception as e:
        logger.error(f"❌ Error running multi-symbol dashboard: {e}")
        raise
    finally:
        await dashboard.stop()
        logger.info("✅ Multi-symbol dashboard stopped successfully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
