import asyncio
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Optional, List
from loguru import logger
# import pandas_ta as ta  # Temporarily disabled
from enum import Enum
import json

from .binance_stream import BinanceKlineStream, HistoricalDataInitializer
from ..utils.config import StrategyConfig, load_strategy_config
from ..strategy.bb_macd_strategy import build_signals
from ..database.db_manager import TradingDBManager


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class LiveSignalGenerator:
    """
    Real-time signal generation using the winning Realistic1 strategy
    """
    
    def __init__(self, symbol: str = "btcusdt", interval: str = "5m", 
                 strategy_config_path: Optional[str] = None):
        self.symbol = symbol.upper()
        self.interval = interval
        
        # Load winning strategy configuration (Realistic1)
        if strategy_config_path:
            self.strategy = load_strategy_config(strategy_config_path)
        else:
            # Use Realistic1 configuration by default
            self.strategy = self._get_realistic1_config()
        
        # Data management
        self.historical_initializer = HistoricalDataInitializer(symbol.upper(), interval)
        self.stream = BinanceKlineStream(symbol.lower(), interval, buffer_size=1000)
        
        # Current market data with indicators
        self.market_data = pd.DataFrame()
        self.current_signals = pd.Series(dtype=bool)
        self.current_price = 0.0
        self.last_signal = SignalType.NEUTRAL
        self.last_signal_time = None
        
        # Current indicators for dashboard
        self.latest_indicators = {}
        self.current_signal = SignalType.NEUTRAL
        
        # Signal history
        self.signal_history: List[Dict] = []
        
        # Callbacks for signal updates
        self.signal_callbacks: List = []
        
        # Database manager
        self.db = TradingDBManager()
        
        logger.info(f"Initialized live signal generator for {self.symbol} {self.interval}")
    
    def _get_realistic1_config(self) -> StrategyConfig:
        """Get the winning Realistic1 strategy configuration"""
        from ..utils.config import (
            StrategyConfig, BollingerConfig, MACDConfig, RSIConfig, 
            ExecutionConfig, RiskConfig, ExitsConfig, BacktestConfig,
            FiltersConfig, EMATrendConfig, TimeBasedExit, MidbandExit
        )
        
        return StrategyConfig(
            bollinger=BollingerConfig(length=20, std=2.0),
            macd=MACDConfig(fast=12, slow=26, signal=9),
            rsi=RSIConfig(length=14, use_filter=True, rsi_buy_max=50.0, rsi_sell_min=50.0),
            filters=FiltersConfig(ema_trend=EMATrendConfig(use=False)),  # No EMA filter
            execution=ExecutionConfig(touch_tolerance_pct=0.001, slippage_pct=0.0005, fee_pct=0.0004),
            risk=RiskConfig(use_atr=True, atr_length=14, stop_mult=2.0, trail_mult=2.5),
            exits=ExitsConfig(
                time_based=TimeBasedExit(use=True, max_bars_in_trade=100),
                midband_exit=MidbandExit(use=False)
            ),
            backtest=BacktestConfig(initial_cash=10000.0, size_pct=0.95, allow_short=False, plot=True)
        )
    
    def add_signal_callback(self, callback):
        """Add callback for signal updates"""
        self.signal_callbacks.append(callback)
    
    def remove_signal_callback(self, callback):
        """Remove callback"""
        if callback in self.signal_callbacks:
            self.signal_callbacks.remove(callback)
    
    async def initialize(self):
        """Initialize with historical data and start real-time streaming"""
        try:
            # Step 1: Test database connection
            if not self.db.test_connection():
                raise ValueError("Failed to connect to database")
            
            # Step 2: Try to load existing data from database
            logger.info("Loading market data from database...")
            self.market_data = self.db.get_market_data(self.symbol, self.interval, limit=500)
            
            # Step 3: If no data in DB, fetch fresh historical data
            if self.market_data.empty or len(self.market_data) < 100:
                logger.info("No sufficient data in database, fetching fresh historical data...")
                historical_df = await self.historical_initializer.fetch_initial_data(limit=500)
                
                if historical_df.empty:
                    raise ValueError("Failed to fetch historical data for initialization")
                
                # Calculate indicators
                historical_df_with_indicators = self._calculate_indicators(historical_df)
                
                # Save to database
                await self._save_to_database(historical_df_with_indicators)
                
                # Set market data
                self.market_data = historical_df_with_indicators
                logger.info(f"📊 Loaded and saved {len(self.market_data)} historical candles")
            else:
                logger.info(f"📊 Loaded {len(self.market_data)} candles from database")
            
            # Step 4: Load recent signals from database
            self.signal_history = self.db.get_recent_signals(limit=10)
            logger.info(f"📊 Loaded {len(self.signal_history)} recent signals from database")
            
            # Step 5: Populate stream buffer with historical data
            for timestamp, row in self.market_data.iterrows():
                kline_data = {
                    'timestamp': timestamp,
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume'],
                    'is_closed': True
                }
                self.stream.klines_buffer.append(kline_data)
            
            # Step 6: Force recalculate indicators and generate initial signals
            logger.info("🔧 Force recalculating indicators for dashboard display...")
            await self._force_calculate_and_update_indicators()
            
            # Step 7: Add callback for new data
            self.stream.add_callback(self._on_new_kline)
            
            # Step 8: Stream connection will be managed by the multi-symbol dashboard
            logger.info("Live signal generator initialization completed")
            # Note: Real-time stream connection is handled by MultiSymbolTradingDashboard
            
        except Exception as e:
            logger.error(f"Failed to initialize live signal generator: {e}")
            raise
    
    async def _on_new_kline(self, kline_data: Dict):
        """Handle new kline data from stream"""
        try:
            # Always update current price for live display
            self.current_price = kline_data['close']
            
            if kline_data['is_closed']:
                logger.info(f"🔔 New closed 5m candle: {kline_data['timestamp']} | Close: ${kline_data['close']:.2f}")
                
                # Add new closed candle to market data and recalculate indicators
                await self._add_new_candle_and_recalculate(kline_data)
                
                # Update indicators and signals on closed candles
                await self._update_indicators_and_signals()
            else:
                logger.debug(f"Live price update: ${kline_data['close']:.2f}")
                # Notify web clients about price change even without new signals
                await self._notify_price_update()
            
        except Exception as e:
            logger.error(f"Error processing new kline: {e}")
    
    async def _add_new_candle_and_recalculate(self, kline_data: Dict):
        """Add new closed candle to market data and recalculate all indicators"""
        try:
            # Convert kline data to pandas row
            new_row = pd.Series({
                'open': kline_data['open'],
                'high': kline_data['high'], 
                'low': kline_data['low'],
                'close': kline_data['close'],
                'volume': kline_data['volume']
            }, name=kline_data['timestamp'])
            
            # Add to market data (append new row)
            if not self.market_data.empty:
                # Check if this timestamp already exists in market data
                if kline_data['timestamp'] in self.market_data.index:
                    # Update existing row instead of adding duplicate
                    self.market_data.loc[kline_data['timestamp']] = new_row
                    logger.info(f"📊 Updated existing candle at {kline_data['timestamp']}")
                else:
                    # Append new row
                    self.market_data = pd.concat([self.market_data, new_row.to_frame().T])
                    logger.info(f"📊 Added new candle to market data at {kline_data['timestamp']}")
            else:
                # First row
                self.market_data = new_row.to_frame().T
                logger.info(f"📊 Initialized market data with first candle at {kline_data['timestamp']}")
            
            # Sort by timestamp to ensure proper order
            self.market_data = self.market_data.sort_index()
            
            # Keep only the last 1000 candles for performance
            if len(self.market_data) > 1000:
                self.market_data = self.market_data.tail(1000)
            
            logger.info(f"📊 Market data now has {len(self.market_data)} periods")
            
            # Recalculate all indicators with updated data
            self.market_data = self._calculate_indicators(self.market_data)
            
            # Save updated data to database
            await self._save_to_database(self.market_data.tail(1))
            
        except Exception as e:
            logger.error(f"Error adding new candle: {e}")
            import traceback
            traceback.print_exc()
    
    async def _save_to_database(self, df_with_indicators: pd.DataFrame):
        """Save market data and indicators to database"""
        try:
            # Prepare candles data
            candles = []
            for timestamp, row in df_with_indicators.iterrows():
                candle = {
                    'timestamp': timestamp,
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume'])
                }
                candles.append(candle)
            
            # Save market data to database
            if self.db.save_market_data(self.symbol, self.interval, candles):
                logger.info(f"💾 Saved {len(candles)} candles to database")
                
                # Save indicators for each candle
                for candle in candles:
                    if 'market_data_id' in candle:
                        # Get corresponding row from dataframe
                        row = df_with_indicators.loc[candle['timestamp']]
                        
                        indicators = {
                            'rsi': float(row.get('RSI')) if pd.notna(row.get('RSI')) else None,
                            'macd': float(row.get('MACD')) if pd.notna(row.get('MACD')) else None,
                            'macd_signal': float(row.get('MACD_SIGNAL')) if pd.notna(row.get('MACD_SIGNAL')) else None,
                            'macd_histogram': float(row.get('MACD_HIST')) if pd.notna(row.get('MACD_HIST')) else None,
                            'bb_upper': float(row.get('BBU')) if pd.notna(row.get('BBU')) else None,
                            'bb_middle': float(row.get('BBM')) if pd.notna(row.get('BBM')) else None,
                            'bb_lower': float(row.get('BBL')) if pd.notna(row.get('BBL')) else None,
                            'atr': float(row.get('ATR')) if pd.notna(row.get('ATR')) else None
                        }
                        
                        self.db.save_indicators(self.symbol, candle['market_data_id'], indicators)
                
                logger.info(f"💾 Saved indicators for {len(candles)} candles to database")
            else:
                logger.error("Failed to save market data to database")
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
    
    async def _force_calculate_and_update_indicators(self):
        """Force recalculate all indicators and update signals - used for initialization"""
        try:
            if self.market_data.empty or len(self.market_data) < 50:
                logger.debug("Insufficient market data for indicator calculation")
                return
            
            # Force recalculate indicators using raw OHLCV data
            raw_data = self.market_data[['open', 'high', 'low', 'close', 'volume']].copy()
            df_with_indicators = self._calculate_indicators(raw_data)
            
            # Update the market_data with fresh indicators
            self.market_data = df_with_indicators
            
            # Generate signals
            buy_signals, sell_signals = build_signals(df_with_indicators, self.strategy)
            
            # Check for new signal
            await self._check_new_signals(buy_signals, sell_signals, df_with_indicators)
            
            # Update latest indicators for dashboard
            latest_row = df_with_indicators.iloc[-1]
            self.latest_indicators = {
                'RSI': float(latest_row.get('RSI')) if pd.notna(latest_row.get('RSI')) else 0,
                'MACD': float(latest_row.get('MACD')) if pd.notna(latest_row.get('MACD')) else 0,
                'MACD_SIGNAL': float(latest_row.get('MACD_SIGNAL')) if pd.notna(latest_row.get('MACD_SIGNAL')) else 0,
                'BBU': float(latest_row.get('BBU')) if pd.notna(latest_row.get('BBU')) else 0,
                'BBL': float(latest_row.get('BBL')) if pd.notna(latest_row.get('BBL')) else 0,
                'BBM': float(latest_row.get('BBM')) if pd.notna(latest_row.get('BBM')) else 0,
                'ATR': float(latest_row.get('ATR')) if pd.notna(latest_row.get('ATR')) else 0
            }
            
            # Log indicator update
            rsi_val = latest_row.get('RSI')
            macd_val = latest_row.get('MACD')
            rsi_str = f"{rsi_val:.1f}" if pd.notna(rsi_val) else "N/A"
            macd_str = f"{macd_val:.4f}" if pd.notna(macd_val) else "N/A"
            
            logger.info(f"🔄 FORCED indicator recalculation at {df_with_indicators.index[-1]} | "
                       f"RSI: {rsi_str} | MACD: {macd_str}")
            
            # Notify callbacks with fresh indicator data
            await self._notify_indicator_update()
            
        except Exception as e:
            logger.error(f"Error in force calculate indicators: {e}")

    async def _update_indicators_and_signals(self):
        """Update technical indicators and generate signals"""
        try:
            # Use current market data (updated with new candles) 
            if self.market_data.empty or len(self.market_data) < 50:
                logger.debug("Insufficient market data for indicator calculation")
                return
            
            # Market data already has indicators (calculated in _add_new_candle_and_recalculate)
            df_with_indicators = self.market_data
            
            # Generate signals
            buy_signals, sell_signals = build_signals(df_with_indicators, self.strategy)
            
            # Check for new signal
            await self._check_new_signals(buy_signals, sell_signals, df_with_indicators)
            
            # Update latest indicators for dashboard
            latest_row = df_with_indicators.iloc[-1]
            self.latest_indicators = {
                'RSI': float(latest_row.get('RSI')) if pd.notna(latest_row.get('RSI')) else 0,
                'MACD': float(latest_row.get('MACD')) if pd.notna(latest_row.get('MACD')) else 0,
                'MACD_SIGNAL': float(latest_row.get('MACD_SIGNAL')) if pd.notna(latest_row.get('MACD_SIGNAL')) else 0,
                'BBU': float(latest_row.get('BBU')) if pd.notna(latest_row.get('BBU')) else 0,
                'BBL': float(latest_row.get('BBL')) if pd.notna(latest_row.get('BBL')) else 0,
                'BBM': float(latest_row.get('BBM')) if pd.notna(latest_row.get('BBM')) else 0,
                'ATR': float(latest_row.get('ATR')) if pd.notna(latest_row.get('ATR')) else 0
            }
            
            # Log indicator update
            # Format indicator values safely
            rsi_val = latest_row.get('RSI')
            macd_val = latest_row.get('MACD')
            rsi_str = f"{rsi_val:.1f}" if pd.notna(rsi_val) else "N/A"
            macd_str = f"{macd_val:.4f}" if pd.notna(macd_val) else "N/A"
            
            logger.info(f"📊 Indicators updated at {df_with_indicators.index[-1]} | "
                       f"RSI: {rsi_str} | MACD: {macd_str}")
            
            # Notify callbacks with indicator update (even if no new signal)
            await self._notify_indicator_update()
            
        except Exception as e:
            logger.error(f"Error updating indicators and signals: {e}")
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        try:
            if len(df) == 0:
                return pd.DataFrame()
            
            # Manual indicator calculations (replacement for pandas_ta)
            bb = self._calculate_bollinger_bands(df, self.strategy.bollinger.length, self.strategy.bollinger.std)
            macd = self._calculate_macd(df, self.strategy.macd.fast, self.strategy.macd.slow, self.strategy.macd.signal)
            rsi = self._calculate_rsi(df, self.strategy.rsi.length)
            
            # Calculate ATR if needed
            atr = None
            if self.strategy.risk.use_atr:
                atr = self._calculate_atr(df, self.strategy.risk.atr_length)
            
            # Calculate EMA if needed for trend filter
            ema_trend = None
            if hasattr(self.strategy, 'filters') and hasattr(self.strategy.filters, 'ema_trend') and self.strategy.filters.ema_trend.use:
                ema_trend = self._calculate_ema(df['close'], self.strategy.filters.ema_trend.length)
            
            # Combine all indicators
            result = df.copy()
            
            if bb is not None:
                # Rename BB columns to standard format
                bb_cols = [col for col in bb.columns if 'BBL_' in col or 'BBM_' in col or 'BBU_' in col]
                if len(bb_cols) >= 3:
                    bb_lower = [col for col in bb_cols if 'BBL_' in col][0]
                    bb_middle = [col for col in bb_cols if 'BBM_' in col][0]
                    bb_upper = [col for col in bb_cols if 'BBU_' in col][0]
                    
                    result['BBL'] = bb[bb_lower]
                    result['BBM'] = bb[bb_middle]
                    result['BBU'] = bb[bb_upper]
            
            if macd is not None:
                # Rename MACD columns - be more flexible with column names
                macd_cols = list(macd.columns)
                logger.debug(f"MACD columns: {macd_cols}")
                
                for col in macd_cols:
                    if 'MACDh_' in col:
                        result['MACD_HIST'] = macd[col]
                    elif 'MACDs_' in col:
                        result['MACD_SIGNAL'] = macd[col]
                    elif 'MACD_' in col and 'MACDh_' not in col and 'MACDs_' not in col:
                        result['MACD'] = macd[col]
            
            if rsi is not None:
                result['RSI'] = rsi
                
            if atr is not None:
                result['ATR'] = atr
            
            if ema_trend is not None:
                result['EMA_TREND'] = ema_trend
            
            # Remove NaN values
            result = result.dropna()
            
            logger.debug(f"Calculated indicators for {len(result)} periods")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return pd.DataFrame()
    
    async def _check_new_signals(self, buy_signals: pd.Series, sell_signals: pd.Series, df: pd.DataFrame):
        """Check for new trading signals"""
        try:
            if buy_signals.empty or sell_signals.empty:
                return
            
            # Get the latest signal
            latest_buy = buy_signals.iloc[-1] if not buy_signals.empty else False
            latest_sell = sell_signals.iloc[-1] if not sell_signals.empty else False
            latest_timestamp = df.index[-1]
            latest_price = df['close'].iloc[-1]
            
            new_signal = None
            
            if latest_buy:
                new_signal = SignalType.BUY
            elif latest_sell:
                new_signal = SignalType.SELL
            else:
                new_signal = SignalType.NEUTRAL
            
            # Only notify if signal changed
            if new_signal != self.last_signal:
                signal_data = {
                    'timestamp': latest_timestamp.isoformat() if hasattr(latest_timestamp, 'isoformat') else str(latest_timestamp),
                    'signal': new_signal.value,
                    'price': float(latest_price),
                    'symbol': self.symbol,
                    'timeframe': self.interval,
                    'rsi': float(df['RSI'].iloc[-1]) if 'RSI' in df.columns and pd.notna(df['RSI'].iloc[-1]) else None,
                    'macd': float(df['MACD'].iloc[-1]) if 'MACD' in df.columns and pd.notna(df['MACD'].iloc[-1]) else None,
                    'macd_signal': float(df['MACD_SIGNAL'].iloc[-1]) if 'MACD_SIGNAL' in df.columns and pd.notna(df['MACD_SIGNAL'].iloc[-1]) else None,
                    'bb_position': self._get_bb_position(df.iloc[-1])
                }
                
                # Store signal
                self.last_signal = new_signal
                self.current_signal = new_signal  # Update current signal for dashboard
                self.last_signal_time = latest_timestamp
                self.signal_history.insert(0, signal_data)  # Add to beginning
                
                # Limit history size
                if len(self.signal_history) > 100:
                    self.signal_history = self.signal_history[:100]
                
                # Save signal to database (try to get market_data_id from recent candle)
                try:
                    # Get the most recent candle from database for this timestamp
                    recent_df = self.db.get_market_data(self.symbol, self.interval, limit=1)
                    if not recent_df.empty:
                        # Get market_data_id from the most recent candle
                        market_data_id = recent_df.index[0] if hasattr(recent_df.index[0], '__int__') else None
                        if market_data_id:
                            # Save signal to database with market_data_id reference
                            if self.db.save_signal(self.symbol, market_data_id, new_signal.value, 
                                                 signal_strength=1.0, strategy_name="realistic1"):
                                logger.info(f"💾 Saved {new_signal.value} signal to database")
                            else:
                                logger.warning(f"Failed to save {new_signal.value} signal to database")
                    else:
                        # Save signal without market_data_id (direct approach)
                        signal_data_db = {
                            'signal_type': new_signal.value,
                            'signal_strength': 1.0 if new_signal != SignalType.NEUTRAL else 0.0,
                            'strategy_name': 'realistic1'
                        }
                        # Use a direct database insertion method if available
                        logger.info(f"💾 Attempting to save {new_signal.value} signal without market_data_id")
                    
                except Exception as e:
                    logger.warning(f"Could not save signal to database: {e}")
                
                logger.info(f"NEW SIGNAL: {new_signal.value} at {latest_price:.2f} | "
                          f"RSI: {signal_data['rsi']:.1f if signal_data['rsi'] else 'N/A'} | "
                          f"MACD: {signal_data['macd']:.4f if signal_data['macd'] else 'N/A'} | "
                          f"BB: {signal_data['bb_position']}")
                
                # Notify callbacks
                for callback in self.signal_callbacks:
                    try:
                        await callback(signal_data)
                    except Exception as e:
                        logger.error(f"Error in signal callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error checking new signals: {e}")
    
    async def _notify_price_update(self):
        """Notify callbacks about price updates without new signals"""
        try:
            # Create update data with current price and indicators
            indicators = {}
            if not self.market_data.empty:
                latest_row = self.market_data.iloc[-1]
                if 'RSI' in self.market_data.columns and pd.notna(latest_row['RSI']):
                    indicators['rsi'] = float(latest_row['RSI'])
                if 'MACD' in self.market_data.columns and pd.notna(latest_row['MACD']):
                    indicators['macd'] = float(latest_row['MACD'])
                if 'MACD_SIGNAL' in self.market_data.columns and pd.notna(latest_row['MACD_SIGNAL']):
                    indicators['macd_signal'] = float(latest_row['MACD_SIGNAL'])
                if 'BBL' in self.market_data.columns and pd.notna(latest_row['BBL']):
                    indicators['bb_lower'] = float(latest_row['BBL'])
                if 'BBU' in self.market_data.columns and pd.notna(latest_row['BBU']):
                    indicators['bb_upper'] = float(latest_row['BBU'])
            
            update_data = {
                'signal': self.last_signal.value if self.last_signal else 'NEUTRAL',
                'price': self.current_price,
                'timestamp': datetime.utcnow().isoformat(),
                'indicators': indicators,
                'current_signal': self.last_signal.value if self.last_signal else 'NEUTRAL',
                'is_price_update': True  # Flag to indicate this is just a price update
            }
            
            # Notify callbacks
            for callback in self.signal_callbacks:
                try:
                    await callback(update_data)
                except Exception as e:
                    logger.error(f"Error in price update callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error notifying price update: {e}")
    
    async def _notify_indicator_update(self):
        """Notify callbacks about indicator updates after closed candles"""
        try:
            # Create update data with updated indicators and closed candle timestamp
            indicators = {}
            if not self.market_data.empty:
                latest_row = self.market_data.iloc[-1]
                if 'RSI' in self.market_data.columns and pd.notna(latest_row['RSI']):
                    indicators['rsi'] = float(latest_row['RSI'])
                if 'MACD' in self.market_data.columns and pd.notna(latest_row['MACD']):
                    indicators['macd'] = float(latest_row['MACD'])
                if 'MACD_SIGNAL' in self.market_data.columns and pd.notna(latest_row['MACD_SIGNAL']):
                    indicators['macd_signal'] = float(latest_row['MACD_SIGNAL'])
                if 'BBL' in self.market_data.columns and pd.notna(latest_row['BBL']):
                    indicators['bb_lower'] = float(latest_row['BBL'])
                if 'BBU' in self.market_data.columns and pd.notna(latest_row['BBU']):
                    indicators['bb_upper'] = float(latest_row['BBU'])
            
            update_data = {
                'signal': self.last_signal.value if self.last_signal else 'NEUTRAL',
                'price': self.current_price,
                'timestamp': self.market_data.index[-1].isoformat() if not self.market_data.empty else datetime.utcnow().isoformat(),
                'indicators': indicators,
                'current_signal': self.last_signal.value if self.last_signal else 'NEUTRAL',
                'is_price_update': True,  # Still a price update but with refreshed indicators
                'indicator_updated': True  # Flag to indicate indicators were recalculated
            }
            
            # Notify callbacks
            for callback in self.signal_callbacks:
                try:
                    await callback(update_data)
                except Exception as e:
                    logger.error(f"Error in indicator update callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error notifying indicator update: {e}")
    
    def _calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()
    
    def _calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return prices.rolling(window=period).mean()
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI manually"""
        try:
            close = df['close']
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            logger.warning(f"RSI calculation error: {e}")
            return pd.Series(index=df.index, dtype=float)
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """Calculate Bollinger Bands manually"""
        try:
            close = df['close']
            sma = self._calculate_sma(close, period)
            rolling_std = close.rolling(window=period).std()
            
            bb_data = pd.DataFrame(index=df.index)
            bb_data[f'BBL_{period}_{std_dev}'] = sma - (rolling_std * std_dev)
            bb_data[f'BBM_{period}_{std_dev}'] = sma
            bb_data[f'BBU_{period}_{std_dev}'] = sma + (rolling_std * std_dev)
            
            return bb_data
        except Exception as e:
            logger.warning(f"Bollinger Bands calculation error: {e}")
            return pd.DataFrame(index=df.index)
    
    def _calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Calculate MACD manually"""
        try:
            close = df['close']
            exp1 = self._calculate_ema(close, fast)
            exp2 = self._calculate_ema(close, slow)
            
            macd_line = exp1 - exp2
            signal_line = self._calculate_ema(macd_line, signal)
            histogram = macd_line - signal_line
            
            macd_data = pd.DataFrame(index=df.index)
            macd_data[f'MACD_{fast}_{slow}_{signal}'] = macd_line
            macd_data[f'MACDs_{fast}_{slow}_{signal}'] = signal_line
            macd_data[f'MACDh_{fast}_{slow}_{signal}'] = histogram
            
            return macd_data
        except Exception as e:
            logger.warning(f"MACD calculation error: {e}")
            return pd.DataFrame(index=df.index)
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range manually"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            prev_close = close.shift(1)
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean()
            
            return atr
        except Exception as e:
            logger.warning(f"ATR calculation error: {e}")
            return pd.Series(index=df.index, dtype=float)

    def _get_bb_position(self, row) -> str:
        """Get price position relative to Bollinger Bands"""
        try:
            if 'BBL' not in row or 'BBU' not in row:
                return "unknown"
                
            price = row['close']
            bb_lower = row['BBL']
            bb_upper = row['BBU']
            bb_middle = row.get('BBM', (bb_lower + bb_upper) / 2)
            
            if price <= bb_lower:
                return "lower"
            elif price >= bb_upper:
                return "upper"
            elif price >= bb_middle:
                return "upper_half"
            else:
                return "lower_half"
                
        except Exception:
            return "unknown"
    
    def get_current_market_data(self) -> Dict:
        """Get current market data and signals"""
        try:
            if self.market_data.empty:
                return {}
            
            latest = self.market_data.iloc[-1]
            current_price = self.stream.get_current_price()
            
            return {
                'timestamp': self.market_data.index[-1].isoformat(),
                'symbol': self.symbol,
                'timeframe': self.interval,
                'price': current_price or latest['close'],
                'open': latest['open'],
                'high': latest['high'],
                'low': latest['low'],
                'volume': latest['volume'],
                'indicators': {
                    'rsi': latest.get('RSI'),
                    'macd': latest.get('MACD'),
                    'macd_signal': latest.get('MACD_SIGNAL'),
                    'macd_hist': latest.get('MACD_HIST'),
                    'bb_lower': latest.get('BBL'),
                    'bb_middle': latest.get('BBM'),
                    'bb_upper': latest.get('BBU'),
                    'atr': latest.get('ATR')
                },
                'current_signal': self.last_signal.value if self.last_signal else SignalType.NEUTRAL.value,
                'bb_position': self._get_bb_position(latest)
            }
            
        except Exception as e:
            logger.error(f"Error getting current market data: {e}")
            return {}
    
    def get_signal_history(self) -> List[Dict]:
        """Get recent signal history"""
        return self.signal_history.copy()
    
    async def stop(self):
        """Stop the live signal generator"""
        logger.info("Stopping live signal generator...")
        await self.stream.disconnect()


# Example usage
async def main():
    """Example usage of LiveSignalGenerator"""
    
    # Create signal generator with Realistic1 strategy
    signal_gen = LiveSignalGenerator(
        symbol="btcusdt", 
        interval="5m",
        strategy_config_path="config/strategy.realistic1.yaml"
    )
    
    # Add callback to print signals
    async def on_signal(signal_data):
        print(f"🚨 {signal_data['signal']} signal at {signal_data['price']:.2f}")
    
    signal_gen.add_signal_callback(on_signal)
    
    try:
        # Initialize and start
        await signal_gen.initialize()
        
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        await signal_gen.stop()


if __name__ == "__main__":
    asyncio.run(main())