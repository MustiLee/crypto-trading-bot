"""
Strategy management service for custom user-defined trading strategies
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from loguru import logger

from .models import CustomStrategy, IndicatorConfig, User
from ..backtest.engine import BacktestEngine
from ..utils.config import StrategyConfig


class StrategyManager:
    """Service class for managing custom trading strategies"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def create_custom_strategy(self, user_id: uuid.UUID, name: str, description: str, 
                              config_data: Dict[str, Any]) -> Tuple[bool, str, Optional[CustomStrategy]]:
        """
        Create a new custom strategy for a user
        
        Args:
            user_id: User UUID
            name: Strategy name
            description: Strategy description
            config_data: Strategy configuration dictionary
            
        Returns:
            Tuple of (success, message, strategy_object)
        """
        try:
            # Validate strategy configuration
            validation_result = self._validate_strategy_config(config_data)
            if not validation_result[0]:
                return False, validation_result[1], None
            
            # Check for duplicate strategy names for this user
            existing_strategy = self.db_session.query(CustomStrategy).filter(
                CustomStrategy.user_id == user_id,
                CustomStrategy.name == name,
                CustomStrategy.is_active == True
            ).first()
            
            if existing_strategy:
                return False, "Strategy with this name already exists", None
            
            # Create new custom strategy
            strategy = CustomStrategy(
                user_id=user_id,
                name=name.strip(),
                description=description.strip() if description else None,
                strategy_config=json.dumps(config_data, indent=2)
            )
            
            self.db_session.add(strategy)
            self.db_session.commit()
            
            logger.info(f"Custom strategy '{name}' created for user {user_id}")
            return True, "Strategy created successfully", strategy
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error creating custom strategy: {e}")
            return False, "Failed to create strategy", None
    
    def update_custom_strategy(self, strategy_id: uuid.UUID, user_id: uuid.UUID,
                              name: str = None, description: str = None,
                              config_data: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        Update an existing custom strategy
        
        Args:
            strategy_id: Strategy UUID
            user_id: User UUID (for authorization)
            name: New strategy name (optional)
            description: New strategy description (optional)
            config_data: New strategy configuration (optional)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            strategy = self.db_session.query(CustomStrategy).filter(
                CustomStrategy.id == strategy_id,
                CustomStrategy.user_id == user_id,
                CustomStrategy.is_active == True
            ).first()
            
            if not strategy:
                return False, "Strategy not found"
            
            # Update fields if provided
            if name is not None:
                # Check for duplicate name
                existing = self.db_session.query(CustomStrategy).filter(
                    CustomStrategy.user_id == user_id,
                    CustomStrategy.name == name,
                    CustomStrategy.id != strategy_id,
                    CustomStrategy.is_active == True
                ).first()
                
                if existing:
                    return False, "Strategy with this name already exists"
                
                strategy.name = name.strip()
            
            if description is not None:
                strategy.description = description.strip() if description else None
            
            if config_data is not None:
                # Validate new configuration
                validation_result = self._validate_strategy_config(config_data)
                if not validation_result[0]:
                    return False, validation_result[1]
                
                strategy.strategy_config = json.dumps(config_data, indent=2)
            
            strategy.updated_at = datetime.utcnow()
            self.db_session.commit()
            
            logger.info(f"Custom strategy {strategy_id} updated for user {user_id}")
            return True, "Strategy updated successfully"
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating custom strategy: {e}")
            return False, "Failed to update strategy"
    
    def delete_custom_strategy(self, strategy_id: uuid.UUID, user_id: uuid.UUID) -> Tuple[bool, str]:
        """
        Soft delete a custom strategy (mark as inactive)
        
        Args:
            strategy_id: Strategy UUID
            user_id: User UUID (for authorization)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            strategy = self.db_session.query(CustomStrategy).filter(
                CustomStrategy.id == strategy_id,
                CustomStrategy.user_id == user_id,
                CustomStrategy.is_active == True
            ).first()
            
            if not strategy:
                return False, "Strategy not found"
            
            strategy.is_active = False
            strategy.updated_at = datetime.utcnow()
            self.db_session.commit()
            
            logger.info(f"Custom strategy {strategy_id} deleted for user {user_id}")
            return True, "Strategy deleted successfully"
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error deleting custom strategy: {e}")
            return False, "Failed to delete strategy"
    
    def get_user_strategies(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Get all active strategies for a user
        
        Args:
            user_id: User UUID
            
        Returns:
            List of strategy dictionaries
        """
        try:
            strategies = self.db_session.query(CustomStrategy).filter(
                CustomStrategy.user_id == user_id,
                CustomStrategy.is_active == True
            ).order_by(CustomStrategy.created_at.desc()).all()
            
            strategy_list = []
            for strategy in strategies:
                strategy_dict = strategy.to_dict()
                # Parse JSON config for easier frontend handling
                if strategy_dict['strategy_config']:
                    try:
                        strategy_dict['parsed_config'] = json.loads(strategy_dict['strategy_config'])
                    except json.JSONDecodeError:
                        strategy_dict['parsed_config'] = {}
                
                if strategy_dict['backtest_results']:
                    try:
                        strategy_dict['parsed_backtest'] = json.loads(strategy_dict['backtest_results'])
                    except json.JSONDecodeError:
                        strategy_dict['parsed_backtest'] = {}
                
                strategy_list.append(strategy_dict)
            
            return strategy_list
            
        except Exception as e:
            logger.error(f"Error getting user strategies: {e}")
            return []
    
    def get_strategy(self, strategy_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get a specific strategy for a user
        
        Args:
            strategy_id: Strategy UUID
            user_id: User UUID (for authorization)
            
        Returns:
            Strategy dictionary or None
        """
        try:
            strategy = self.db_session.query(CustomStrategy).filter(
                CustomStrategy.id == strategy_id,
                CustomStrategy.user_id == user_id,
                CustomStrategy.is_active == True
            ).first()
            
            if not strategy:
                return None
            
            strategy_dict = strategy.to_dict()
            # Parse JSON config
            if strategy_dict['strategy_config']:
                try:
                    strategy_dict['parsed_config'] = json.loads(strategy_dict['strategy_config'])
                except json.JSONDecodeError:
                    strategy_dict['parsed_config'] = {}
            
            if strategy_dict['backtest_results']:
                try:
                    strategy_dict['parsed_backtest'] = json.loads(strategy_dict['backtest_results'])
                except json.JSONDecodeError:
                    strategy_dict['parsed_backtest'] = {}
            
            return strategy_dict
            
        except Exception as e:
            logger.error(f"Error getting strategy: {e}")
            return None
    
    async def backtest_custom_strategy(self, strategy_id: uuid.UUID, user_id: uuid.UUID,
                                symbol: str = "BTCUSDT") -> Tuple[bool, str, Optional[Dict]]:
        """
        Run backtest on a custom strategy
        
        Args:
            strategy_id: Strategy UUID
            user_id: User UUID (for authorization)
            symbol: Symbol to backtest (default: BTCUSDT)
            
        Returns:
            Tuple of (success, message, backtest_results)
        """
        try:
            strategy = self.db_session.query(CustomStrategy).filter(
                CustomStrategy.id == strategy_id,
                CustomStrategy.user_id == user_id,
                CustomStrategy.is_active == True
            ).first()
            
            if not strategy:
                return False, "Strategy not found", None
            
            # Parse strategy configuration
            try:
                config_data = json.loads(strategy.strategy_config)
            except json.JSONDecodeError:
                return False, "Invalid strategy configuration", None
            
            # Convert to StrategyConfig format (simplified)
            # This would need to be implemented based on your strategy structure
            config_path = self._create_temporary_config(config_data)
            
            # Run backtest using existing BacktestEngine
            backtest_engine = BacktestEngine(config_path, symbol, config_data.get('strategy_type', 'quality_over_quantity'))
            
            # Get historical data (you'll need to implement this data source)
            from ..data.ohlcv_downloader import OHLCVDownloader
            downloader = OHLCVDownloader()
            
            # Download data for backtest (last 3 months)
            from datetime import datetime, timedelta
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=90)
            
            df = await downloader.download_ohlcv(symbol, "1h", start_date, end_date)
            
            if df.empty:
                return False, "No historical data available for backtest", None
            
            # Run backtest
            backtest_result = backtest_engine.run_backtest(df)
            
            if not backtest_result:
                return False, "Backtest execution failed", None
            
            # Store backtest results
            strategy.backtest_results = json.dumps(backtest_result['metrics'], indent=2)
            strategy.updated_at = datetime.utcnow()
            self.db_session.commit()
            
            logger.info(f"Backtest completed for strategy {strategy_id}")
            return True, "Backtest completed successfully", backtest_result['metrics']
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return False, f"Backtest failed: {str(e)}", None
    
    def create_indicator_config(self, user_id: uuid.UUID, name: str, 
                               config_data: Dict[str, Any]) -> Tuple[bool, str, Optional[IndicatorConfig]]:
        """
        Create custom indicator configuration for user
        
        Args:
            user_id: User UUID
            name: Configuration name
            config_data: Indicator parameters
            
        Returns:
            Tuple of (success, message, config_object)
        """
        try:
            # Check for duplicate names
            existing = self.db_session.query(IndicatorConfig).filter(
                IndicatorConfig.user_id == user_id,
                IndicatorConfig.name == name
            ).first()
            
            if existing:
                return False, "Configuration with this name already exists", None
            
            # Create indicator config
            config = IndicatorConfig(
                user_id=user_id,
                name=name.strip(),
                **config_data
            )
            
            self.db_session.add(config)
            self.db_session.commit()
            
            logger.info(f"Indicator config '{name}' created for user {user_id}")
            return True, "Indicator configuration created successfully", config
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error creating indicator config: {e}")
            return False, "Failed to create indicator configuration", None
    
    def get_user_indicator_configs(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Get all indicator configurations for a user
        
        Args:
            user_id: User UUID
            
        Returns:
            List of indicator configuration dictionaries
        """
        try:
            configs = self.db_session.query(IndicatorConfig).filter(
                IndicatorConfig.user_id == user_id
            ).order_by(IndicatorConfig.is_default.desc(), IndicatorConfig.created_at.desc()).all()
            
            return [config.to_dict() for config in configs]
            
        except Exception as e:
            logger.error(f"Error getting user indicator configs: {e}")
            return []
    
    def get_default_strategy_templates(self) -> List[Dict[str, Any]]:
        """
        Get default strategy templates that users can customize
        
        Returns:
            List of strategy template dictionaries
        """
        return [
            {
                "name": "Quality Over Quantity",
                "description": "Conservative strategy focusing on high-quality signals with multiple confirmations",
                "strategy_type": "quality_over_quantity",
                "config": {
                    "indicators": {
                        "bollinger_bands": {"period": 20, "std_dev": 2.0},
                        "macd": {"fast": 12, "slow": 26, "signal": 9},
                        "rsi": {"period": 14, "overbought": 55, "oversold": 45},
                        "ema": {"short": 20, "long": 50, "trend": 200},
                        "atr": {"period": 14}
                    },
                    "filters": {
                        "volume_confirmation": True,
                        "trend_filter": True,
                        "volatility_filter": True,
                        "min_signal_gap": 5
                    },
                    "risk_management": {
                        "position_size_pct": 0.05,
                        "stop_loss_atr_multiplier": 2.0,
                        "take_profit_ratio": 2.0
                    }
                }
            },
            {
                "name": "Trend Momentum",
                "description": "Trend-following strategy with momentum confirmation",
                "strategy_type": "trend_momentum",
                "config": {
                    "indicators": {
                        "macd": {"fast": 12, "slow": 26, "signal": 9},
                        "adx": {"period": 14, "threshold": 20},
                        "supertrend": {"period": 10, "multiplier": 3.0},
                        "momentum": {"period": 10},
                        "rsi": {"period": 14, "upper": 70, "lower": 40}
                    },
                    "filters": {
                        "trend_strength": True,
                        "volume_surge": True,
                        "momentum_confirmation": True
                    },
                    "risk_management": {
                        "position_size_pct": 0.08,
                        "trailing_stop": True,
                        "atr_stop_multiplier": 2.5
                    }
                }
            },
            {
                "name": "Volatility Breakout",
                "description": "Strategy that capitalizes on volatility expansion and breakouts",
                "strategy_type": "volatility_breakout",
                "config": {
                    "indicators": {
                        "bollinger_bands": {"period": 20, "std_dev": 2.0},
                        "keltner_channels": {"period": 20, "multiplier": 2.0},
                        "atr": {"period": 14},
                        "volume_ratio": {"period": 20},
                        "rsi": {"period": 14}
                    },
                    "breakout": {
                        "squeeze_threshold": 0.2,
                        "volume_threshold": 2.0,
                        "atr_expansion": True
                    },
                    "risk_management": {
                        "position_size_pct": 0.06,
                        "volatility_sizing": True,
                        "breakout_stop": True
                    }
                }
            }
        ]
    
    def _validate_strategy_config(self, config_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate strategy configuration format and parameters
        
        Args:
            config_data: Strategy configuration dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Basic structure validation
            required_sections = ['indicators', 'filters', 'risk_management']
            for section in required_sections:
                if section not in config_data:
                    return False, f"Missing required section: {section}"
            
            # Validate indicator parameters
            indicators = config_data.get('indicators', {})
            
            # Bollinger Bands validation
            if 'bollinger_bands' in indicators:
                bb = indicators['bollinger_bands']
                if not (5 <= bb.get('period', 20) <= 50):
                    return False, "Bollinger Bands period must be between 5 and 50"
                if not (1.0 <= bb.get('std_dev', 2.0) <= 3.0):
                    return False, "Bollinger Bands standard deviation must be between 1.0 and 3.0"
            
            # MACD validation
            if 'macd' in indicators:
                macd = indicators['macd']
                fast = macd.get('fast', 12)
                slow = macd.get('slow', 26)
                if fast >= slow:
                    return False, "MACD fast period must be less than slow period"
                if not (5 <= fast <= 20):
                    return False, "MACD fast period must be between 5 and 20"
                if not (20 <= slow <= 40):
                    return False, "MACD slow period must be between 20 and 40"
            
            # RSI validation
            if 'rsi' in indicators:
                rsi = indicators['rsi']
                if not (5 <= rsi.get('period', 14) <= 30):
                    return False, "RSI period must be between 5 and 30"
                
                overbought = rsi.get('overbought', 70)
                oversold = rsi.get('oversold', 30)
                if oversold >= overbought:
                    return False, "RSI oversold level must be less than overbought level"
                if not (20 <= oversold <= 40):
                    return False, "RSI oversold level must be between 20 and 40"
                if not (60 <= overbought <= 80):
                    return False, "RSI overbought level must be between 60 and 80"
            
            # Risk management validation
            risk_mgmt = config_data.get('risk_management', {})
            position_size = risk_mgmt.get('position_size_pct', 0.05)
            if not (0.01 <= position_size <= 0.25):
                return False, "Position size must be between 1% and 25%"
            
            return True, "Configuration is valid"
            
        except Exception as e:
            return False, f"Configuration validation error: {str(e)}"
    
    def _create_temporary_config(self, config_data: Dict[str, Any]) -> str:
        """
        Create temporary configuration file for backtesting
        
        Args:
            config_data: Strategy configuration dictionary
            
        Returns:
            Path to temporary config file
        """
        # This would create a temporary YAML file compatible with your existing config system
        # Implementation would depend on your specific config format
        import tempfile
        import yaml
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        
        # Convert to your config format
        yaml_config = {
            'backtest': {
                'initial_cash': 10000,
                'size_pct': config_data.get('risk_management', {}).get('position_size_pct', 0.05),
                'allow_short': False
            },
            'execution': {
                'fee_pct': 0.001,
                'slippage_pct': 0.0005,
                'touch_tolerance_pct': 0.02
            },
            'indicators': config_data.get('indicators', {}),
            'filters': config_data.get('filters', {})
        }
        
        yaml.dump(yaml_config, temp_file, default_flow_style=False)
        temp_file.close()
        
        return temp_file.name