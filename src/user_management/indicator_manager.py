"""
Indicator configuration manager for custom user-defined indicator parameters
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from loguru import logger

from .models import IndicatorConfig, User
from ..indicators.factory import add_indicators
from ..utils.config import StrategyConfig


class IndicatorManager:
    """Service class for managing custom indicator configurations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def create_indicator_config(self, user_id: uuid.UUID, name: str, 
                               config_params: Dict[str, Any]) -> Tuple[bool, str, Optional[IndicatorConfig]]:
        """
        Create custom indicator configuration for user
        
        Args:
            user_id: User UUID
            name: Configuration name
            config_params: Dictionary of indicator parameters
            
        Returns:
            Tuple of (success, message, config_object)
        """
        try:
            # Validate parameters
            validation_result = self._validate_indicator_params(config_params)
            if not validation_result[0]:
                return False, validation_result[1], None
            
            # Check for duplicate names
            existing_config = self.db_session.query(IndicatorConfig).filter(
                IndicatorConfig.user_id == user_id,
                IndicatorConfig.name == name
            ).first()
            
            if existing_config:
                return False, "Configuration with this name already exists", None
            
            # Create new indicator configuration
            config = IndicatorConfig(
                user_id=user_id,
                name=name.strip(),
                bb_period=config_params.get('bb_period', 20),
                bb_std=config_params.get('bb_std', 2.0),
                macd_fast=config_params.get('macd_fast', 12),
                macd_slow=config_params.get('macd_slow', 26),
                macd_signal=config_params.get('macd_signal', 9),
                rsi_period=config_params.get('rsi_period', 14),
                rsi_overbought=config_params.get('rsi_overbought', 70.0),
                rsi_oversold=config_params.get('rsi_oversold', 30.0),
                ema_short=config_params.get('ema_short', 20),
                ema_long=config_params.get('ema_long', 50),
                ema_trend=config_params.get('ema_trend', 200),
                atr_period=config_params.get('atr_period', 14),
                use_volume_indicators=config_params.get('use_volume_indicators', True),
                use_volatility_indicators=config_params.get('use_volatility_indicators', True),
                use_momentum_indicators=config_params.get('use_momentum_indicators', True),
                use_trend_indicators=config_params.get('use_trend_indicators', True)
            )
            
            self.db_session.add(config)
            self.db_session.commit()
            
            logger.info(f"Indicator config '{name}' created for user {user_id}")
            return True, "Indicator configuration created successfully", config
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error creating indicator config: {e}")
            return False, "Failed to create indicator configuration", None
    
    def update_indicator_config(self, config_id: uuid.UUID, user_id: uuid.UUID,
                               name: str = None, config_params: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        Update existing indicator configuration
        
        Args:
            config_id: Configuration UUID
            user_id: User UUID (for authorization)
            name: New configuration name (optional)
            config_params: New configuration parameters (optional)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            config = self.db_session.query(IndicatorConfig).filter(
                IndicatorConfig.id == config_id,
                IndicatorConfig.user_id == user_id
            ).first()
            
            if not config:
                return False, "Configuration not found"
            
            if config.is_default:
                return False, "Cannot modify default configuration"
            
            # Update name if provided
            if name is not None:
                # Check for duplicate name
                existing = self.db_session.query(IndicatorConfig).filter(
                    IndicatorConfig.user_id == user_id,
                    IndicatorConfig.name == name,
                    IndicatorConfig.id != config_id
                ).first()
                
                if existing:
                    return False, "Configuration with this name already exists"
                
                config.name = name.strip()
            
            # Update parameters if provided
            if config_params is not None:
                # Validate parameters
                validation_result = self._validate_indicator_params(config_params)
                if not validation_result[0]:
                    return False, validation_result[1]
                
                # Update parameters
                for param, value in config_params.items():
                    if hasattr(config, param):
                        setattr(config, param, value)
            
            config.updated_at = datetime.utcnow()
            self.db_session.commit()
            
            logger.info(f"Indicator config {config_id} updated for user {user_id}")
            return True, "Configuration updated successfully"
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating indicator config: {e}")
            return False, "Failed to update configuration"
    
    def delete_indicator_config(self, config_id: uuid.UUID, user_id: uuid.UUID) -> Tuple[bool, str]:
        """
        Delete indicator configuration
        
        Args:
            config_id: Configuration UUID
            user_id: User UUID (for authorization)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            config = self.db_session.query(IndicatorConfig).filter(
                IndicatorConfig.id == config_id,
                IndicatorConfig.user_id == user_id
            ).first()
            
            if not config:
                return False, "Configuration not found"
            
            if config.is_default:
                return False, "Cannot delete default configuration"
            
            self.db_session.delete(config)
            self.db_session.commit()
            
            logger.info(f"Indicator config {config_id} deleted for user {user_id}")
            return True, "Configuration deleted successfully"
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error deleting indicator config: {e}")
            return False, "Failed to delete configuration"
    
    def get_user_indicator_configs(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Get all indicator configurations for a user
        
        Args:
            user_id: User UUID
            
        Returns:
            List of configuration dictionaries
        """
        try:
            configs = self.db_session.query(IndicatorConfig).filter(
                IndicatorConfig.user_id == user_id
            ).order_by(IndicatorConfig.is_default.desc(), IndicatorConfig.created_at.desc()).all()
            
            return [config.to_dict() for config in configs]
            
        except Exception as e:
            logger.error(f"Error getting user indicator configs: {e}")
            return []
    
    def get_indicator_config(self, config_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get specific indicator configuration
        
        Args:
            config_id: Configuration UUID
            user_id: User UUID (for authorization)
            
        Returns:
            Configuration dictionary or None
        """
        try:
            config = self.db_session.query(IndicatorConfig).filter(
                IndicatorConfig.id == config_id,
                IndicatorConfig.user_id == user_id
            ).first()
            
            if config:
                return config.to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting indicator config: {e}")
            return None
    
    def set_default_config(self, config_id: uuid.UUID, user_id: uuid.UUID) -> Tuple[bool, str]:
        """
        Set a configuration as the default for the user
        
        Args:
            config_id: Configuration UUID
            user_id: User UUID
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # First, remove default status from all user configs
            self.db_session.query(IndicatorConfig).filter(
                IndicatorConfig.user_id == user_id
            ).update({'is_default': False})
            
            # Set new default
            config = self.db_session.query(IndicatorConfig).filter(
                IndicatorConfig.id == config_id,
                IndicatorConfig.user_id == user_id
            ).first()
            
            if not config:
                return False, "Configuration not found"
            
            config.is_default = True
            config.updated_at = datetime.utcnow()
            self.db_session.commit()
            
            logger.info(f"Set default indicator config {config_id} for user {user_id}")
            return True, "Default configuration set successfully"
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error setting default config: {e}")
            return False, "Failed to set default configuration"
    
    def get_default_config(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get user's default indicator configuration
        
        Args:
            user_id: User UUID
            
        Returns:
            Default configuration dictionary or None
        """
        try:
            config = self.db_session.query(IndicatorConfig).filter(
                IndicatorConfig.user_id == user_id,
                IndicatorConfig.is_default == True
            ).first()
            
            if config:
                return config.to_dict()
            
            # If no default found, return the first config or create one
            config = self.db_session.query(IndicatorConfig).filter(
                IndicatorConfig.user_id == user_id
            ).first()
            
            if config:
                # Set as default
                config.is_default = True
                self.db_session.commit()
                return config.to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting default config: {e}")
            return None
    
    def apply_custom_indicators(self, df, config_id: uuid.UUID, user_id: uuid.UUID):
        """
        Apply custom indicator configuration to DataFrame
        
        Args:
            df: OHLCV DataFrame
            config_id: Configuration UUID
            user_id: User UUID
            
        Returns:
            DataFrame with custom indicators applied
        """
        try:
            config = self.db_session.query(IndicatorConfig).filter(
                IndicatorConfig.id == config_id,
                IndicatorConfig.user_id == user_id
            ).first()
            
            if not config:
                logger.warning(f"Config {config_id} not found, using default indicators")
                return add_indicators(df, StrategyConfig())
            
            # Create custom StrategyConfig based on user configuration
            custom_config = self._create_strategy_config_from_indicator_config(config)
            
            # Apply indicators with custom configuration
            return add_indicators(df, custom_config)
            
        except Exception as e:
            logger.error(f"Error applying custom indicators: {e}")
            # Fallback to default indicators
            return add_indicators(df, StrategyConfig())
    
    def get_predefined_configs(self) -> List[Dict[str, Any]]:
        """
        Get predefined indicator configurations that users can adopt
        
        Returns:
            List of predefined configuration dictionaries
        """
        return [
            {
                "name": "Conservative",
                "description": "Safe parameters for stable markets",
                "config": {
                    "bb_period": 20,
                    "bb_std": 2.0,
                    "macd_fast": 12,
                    "macd_slow": 26,
                    "macd_signal": 9,
                    "rsi_period": 14,
                    "rsi_overbought": 70.0,
                    "rsi_oversold": 30.0,
                    "ema_short": 20,
                    "ema_long": 50,
                    "ema_trend": 200,
                    "atr_period": 14,
                    "use_volume_indicators": True,
                    "use_volatility_indicators": True,
                    "use_momentum_indicators": True,
                    "use_trend_indicators": True
                }
            },
            {
                "name": "Aggressive",
                "description": "Faster parameters for volatile markets",
                "config": {
                    "bb_period": 15,
                    "bb_std": 1.8,
                    "macd_fast": 8,
                    "macd_slow": 21,
                    "macd_signal": 5,
                    "rsi_period": 9,
                    "rsi_overbought": 75.0,
                    "rsi_oversold": 25.0,
                    "ema_short": 10,
                    "ema_long": 30,
                    "ema_trend": 100,
                    "atr_period": 10,
                    "use_volume_indicators": True,
                    "use_volatility_indicators": True,
                    "use_momentum_indicators": True,
                    "use_trend_indicators": True
                }
            },
            {
                "name": "Scalping",
                "description": "Fast parameters for quick trades",
                "config": {
                    "bb_period": 10,
                    "bb_std": 1.5,
                    "macd_fast": 5,
                    "macd_slow": 13,
                    "macd_signal": 3,
                    "rsi_period": 5,
                    "rsi_overbought": 80.0,
                    "rsi_oversold": 20.0,
                    "ema_short": 5,
                    "ema_long": 20,
                    "ema_trend": 50,
                    "atr_period": 7,
                    "use_volume_indicators": True,
                    "use_volatility_indicators": False,
                    "use_momentum_indicators": True,
                    "use_trend_indicators": False
                }
            },
            {
                "name": "Swing Trading",
                "description": "Longer-term parameters for swing trades",
                "config": {
                    "bb_period": 30,
                    "bb_std": 2.2,
                    "macd_fast": 15,
                    "macd_slow": 35,
                    "macd_signal": 12,
                    "rsi_period": 21,
                    "rsi_overbought": 65.0,
                    "rsi_oversold": 35.0,
                    "ema_short": 30,
                    "ema_long": 100,
                    "ema_trend": 300,
                    "atr_period": 21,
                    "use_volume_indicators": True,
                    "use_volatility_indicators": True,
                    "use_momentum_indicators": True,
                    "use_trend_indicators": True
                }
            }
        ]
    
    def _validate_indicator_params(self, config_params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate indicator parameters
        
        Args:
            config_params: Dictionary of parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Bollinger Bands validation
            bb_period = config_params.get('bb_period', 20)
            bb_std = config_params.get('bb_std', 2.0)
            
            if not (5 <= bb_period <= 50):
                return False, "Bollinger Bands period must be between 5 and 50"
            if not (1.0 <= bb_std <= 3.5):
                return False, "Bollinger Bands standard deviation must be between 1.0 and 3.5"
            
            # MACD validation
            macd_fast = config_params.get('macd_fast', 12)
            macd_slow = config_params.get('macd_slow', 26)
            macd_signal = config_params.get('macd_signal', 9)
            
            if macd_fast >= macd_slow:
                return False, "MACD fast period must be less than slow period"
            if not (3 <= macd_fast <= 20):
                return False, "MACD fast period must be between 3 and 20"
            if not (15 <= macd_slow <= 50):
                return False, "MACD slow period must be between 15 and 50"
            if not (3 <= macd_signal <= 15):
                return False, "MACD signal period must be between 3 and 15"
            
            # RSI validation
            rsi_period = config_params.get('rsi_period', 14)
            rsi_overbought = config_params.get('rsi_overbought', 70.0)
            rsi_oversold = config_params.get('rsi_oversold', 30.0)
            
            if not (3 <= rsi_period <= 30):
                return False, "RSI period must be between 3 and 30"
            if rsi_oversold >= rsi_overbought:
                return False, "RSI oversold level must be less than overbought level"
            if not (10.0 <= rsi_oversold <= 45.0):
                return False, "RSI oversold level must be between 10 and 45"
            if not (55.0 <= rsi_overbought <= 90.0):
                return False, "RSI overbought level must be between 55 and 90"
            
            # EMA validation
            ema_short = config_params.get('ema_short', 20)
            ema_long = config_params.get('ema_long', 50)
            ema_trend = config_params.get('ema_trend', 200)
            
            if not (3 <= ema_short <= 50):
                return False, "Short EMA period must be between 3 and 50"
            if not (20 <= ema_long <= 200):
                return False, "Long EMA period must be between 20 and 200"
            if not (50 <= ema_trend <= 500):
                return False, "Trend EMA period must be between 50 and 500"
            if ema_short >= ema_long:
                return False, "Short EMA period must be less than long EMA period"
            if ema_long >= ema_trend:
                return False, "Long EMA period must be less than trend EMA period"
            
            # ATR validation
            atr_period = config_params.get('atr_period', 14)
            if not (5 <= atr_period <= 30):
                return False, "ATR period must be between 5 and 30"
            
            return True, "Parameters are valid"
            
        except Exception as e:
            return False, f"Parameter validation error: {str(e)}"
    
    def _create_strategy_config_from_indicator_config(self, indicator_config: IndicatorConfig) -> StrategyConfig:
        """
        Convert IndicatorConfig to StrategyConfig format
        
        Args:
            indicator_config: IndicatorConfig object
            
        Returns:
            StrategyConfig object with custom parameters
        """
        # This is a simplified example - you'd need to implement proper conversion
        # based on your StrategyConfig structure
        config = StrategyConfig()
        
        # Apply custom parameters (this would need to be implemented based on your config structure)
        # config.indicators.bollinger_bands.period = indicator_config.bb_period
        # config.indicators.bollinger_bands.std_dev = indicator_config.bb_std
        # ... and so on
        
        return config