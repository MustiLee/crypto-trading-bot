"""
User management module for cryptocurrency trading bot

This module provides comprehensive user management functionality including:
- User registration and authentication
- Email verification system
- Password reset functionality
- Custom trading strategy management
- Custom indicator configuration
- Session management and security

Components:
- models: SQLAlchemy models for users, sessions, strategies, and configs
- user_manager: Core user management service
- strategy_manager: Custom strategy management service  
- indicator_manager: Custom indicator configuration service
- email_service: Email verification and notification service
- auth_routes: FastAPI routes for authentication endpoints
"""

from .models import User, UserSession, CustomStrategy, IndicatorConfig
from .user_manager import UserManager
from .strategy_manager import StrategyManager
from .indicator_manager import IndicatorManager
from .strategy_tester import StrategyTester
from .email_service import EmailService
from .auth_routes import router as auth_router

__all__ = [
    'User',
    'UserSession', 
    'CustomStrategy',
    'IndicatorConfig',
    'UserManager',
    'StrategyManager',
    'IndicatorManager',
    'StrategyTester',
    'EmailService',
    'auth_router'
]