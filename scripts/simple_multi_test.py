#!/usr/bin/env python3
"""
Simple multi-symbol test to verify our setup works
"""

import sys
from pathlib import Path
import asyncio

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.data.ohlcv_downloader import OHLCVDownloader
from loguru import logger
import yaml
from datetime import datetime, timedelta


async def test_multi_symbol_data():
    """Test downloading data for all symbols"""
    
    # Load symbols
    config_path = Path(__file__).parent.parent / "config" / "symbols.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    symbols = config['symbols']
    downloader = OHLCVDownloader()
    
    logger.info("🔍 Testing multi-symbol data download...")
    
    for symbol_key, symbol_config in symbols.items():
        try:
            logger.info(f"Testing {symbol_key} ({symbol_config['symbol']})...")
            
            # Download small sample
            end_date = datetime.now()
            start_date = end_date - timedelta(days=2)
            
            df = await downloader.download_ohlcv(
                symbol=symbol_config['symbol'],
                timeframe="5m",
                start_date=start_date,
                end_date=end_date
            )
            
            if not df.empty:
                logger.success(f"✅ {symbol_key}: {len(df)} candles, last price: ${df['close'].iloc[-1]:.6f}")
            else:
                logger.error(f"❌ {symbol_key}: No data received")
                
        except Exception as e:
            logger.error(f"❌ {symbol_key}: Error - {e}")
    
    logger.info("🎯 Multi-symbol test complete!")


if __name__ == "__main__":
    asyncio.run(test_multi_symbol_data())