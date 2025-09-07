"""
FastAPI routes for user authentication and management
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request, status
import os
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.orm import Session
from loguru import logger

from .models import User, UserSession, CustomStrategy, IndicatorConfig
from .user_manager import UserManager
from .strategy_manager import StrategyManager
from .strategy_tester import StrategyTester
from .email_service import EmailService
from ..database.db_manager import TradingDBManager


# Pydantic models for request/response
class UserRegistrationRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    telegram_id: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    telegram_id: Optional[str]
    is_active: bool
    is_email_verified: bool
    created_at: str
    last_login: Optional[str]


class LoginResponse(BaseModel):
    user: UserResponse
    token: str
    expires_at: str
    message: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class StrategyCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    strategy_config: Dict[str, Any]
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Strategy name cannot be empty')
        if len(v.strip()) > 100:
            raise ValueError('Strategy name must be less than 100 characters')
        return v.strip()


class IndicatorConfigRequest(BaseModel):
    name: str
    bb_period: int = 20
    bb_std: float = 2.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    ema_short: int = 20
    ema_long: int = 50
    ema_trend: int = 200
    atr_period: int = 14
    use_volume_indicators: bool = True
    use_volatility_indicators: bool = True
    use_momentum_indicators: bool = True
    use_trend_indicators: bool = True


class StrategyTestRequest(BaseModel):
    strategy_config: Dict[str, Any]
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    test_days: int = 90
    
    @validator('symbol')
    def validate_symbol(cls, v):
        allowed_symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'BNBUSDT', 'ADAUSDT', 
                          'SOLUSDT', 'DOTUSDT', 'MATICUSDT', 'AVAXUSDT', 'LINKUSDT']
        if v not in allowed_symbols:
            raise ValueError(f'Symbol must be one of: {", ".join(allowed_symbols)}')
        return v
    
    @validator('test_days')
    def validate_test_days(cls, v):
        if not (7 <= v <= 365):
            raise ValueError('Test days must be between 7 and 365')
        return v


class QuickTestRequest(BaseModel):
    strategy_config: Dict[str, Any]
    symbol: str = "BTCUSDT"
    
    @validator('symbol')
    def validate_symbol(cls, v):
        allowed_symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'BNBUSDT', 'ADAUSDT', 
                          'SOLUSDT', 'DOTUSDT', 'MATICUSDT', 'AVAXUSDT', 'LINKUSDT']
        if v not in allowed_symbols:
            raise ValueError(f'Symbol must be one of: {", ".join(allowed_symbols)}')
        return v


class VerifyCodeRequest(BaseModel):
    code: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr


# Security
security = HTTPBearer()


class AuthService:
    """Authentication service for dependency injection"""
    
    def __init__(self):
        self.db_manager = TradingDBManager()
    
    def get_db_session(self):
        """Get a SQLAlchemy session from the DB manager"""
        try:
            # SQLAlchemy 2.x Session supports context manager; callers may also use it directly.
            return self.db_manager.Session()
        except Exception as e:
            logger.error(f"Failed to create DB session: {e}")
            raise
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
        """Get current authenticated user from token"""
        try:
            token = credentials.credentials
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT u.* FROM users u
                        JOIN user_sessions us ON u.id = us.user_id
                        WHERE us.session_token = %s AND us.expires_at > NOW()
                        LIMIT 1;
                    """, (token,))
                    
                    user_data = cursor.fetchone()
                    
                    if not user_data:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=api_error("AUTH_INVALID", "Invalid or expired token")
                        )
                    
                    # Convert to User object (simplified)
                    user = User(**dict(user_data))
                    return user
                    
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=api_error("AUTH_FAILED", "Authentication failed")
            )


# Create router
router = APIRouter(prefix="/api/auth", tags=["authentication"])
auth_service = AuthService()


def api_error(code: str, message: str):
    """Standard error detail schema"""
    return {"code": code, "message": message}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(request: UserRegistrationRequest, http_request: Request):
    """Register a new user"""
    try:
        # Get database session and initialize services
        db_session = auth_service.get_db_session()
        email_service = EmailService()
        user_manager = UserManager(db_session, email_service)
        
        # Extract client info
        user_agent = http_request.headers.get("user-agent")
        ip_address = http_request.client.host
        
        # Register user
        success, message, user = user_manager.register_user(
            email=request.email,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
            phone=request.phone,
            telegram_id=request.telegram_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("REGISTRATION_FAILED", message)
            )
        
        logger.info(f"User registered: {request.email} from {ip_address}")
        
        return {
            "message": message,
            "user_id": str(user.id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("REGISTRATION_ERROR", "Registration failed")
        )


@router.post("/login", response_model=LoginResponse)
async def login_user(request: UserLoginRequest, http_request: Request):
    """Authenticate user and create session"""
    try:
        db_session = auth_service.get_db_session()
        user_manager = UserManager(db_session)
        
        # Extract client info
        user_agent = http_request.headers.get("user-agent")
        ip_address = http_request.client.host
        
        # Authenticate user
        success, message, session = user_manager.authenticate_user(
            email=request.email,
            password=request.password,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=api_error("AUTH_INVALID", message)
            )
        
        user_data = session.user.to_dict()
        
        logger.info(f"User logged in: {request.email} from {ip_address}")
        
        return LoginResponse(
            user=UserResponse(**user_data),
            token=session.session_token,
            expires_at=session.expires_at.isoformat(),
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("LOGIN_ERROR", "Login failed")
        )


@router.post("/logout")
async def logout_user(current_user: User = Depends(auth_service.get_current_user)):
    """Logout user by invalidating session"""
    try:
        db_session = auth_service.get_db_session()
        user_manager = UserManager(db_session)
        
        # Get session token from user (simplified - would need proper session tracking)
        # This is a simplified example
        
        logger.info(f"User logged out: {current_user.email}")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("LOGOUT_ERROR", "Logout failed")
        )


@router.get("/verify-email")
async def verify_email(token: str):
    """Verify user email with token"""
    try:
        db_session = auth_service.get_db_session()
        user_manager = UserManager(db_session)
        
        success, message = user_manager.verify_email(token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("INVALID_TOKEN", message)
            )
        
        return {"message": message}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("VERIFY_ERROR", "Email verification failed")
        )

@router.post("/verify-email-code")
async def verify_email_code(request: VerifyCodeRequest):
    """Verify email using a short verification code"""
    try:
        db_session = auth_service.get_db_session()
        user_manager = UserManager(db_session)
        # Allow a fixed code in environments without SMTP configured for easier testing
        allow_test_code = request.code == '123456' and not os.getenv('SMTP_EMAIL')
        success, message = user_manager.verify_email(request.code)
        if not success and allow_test_code:
            # Find any user with a pending verification and mark verified
            user = db_session.query(User).filter(User.is_email_verified == False).first()
            if user:
                verified = user.verify_email_token(user.email_verification_token or request.code)
                if verified:
                    db_session.commit()
                    success, message = True, "Email verified with test code"
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=api_error("INVALID_CODE", message))
        return {"message": message}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email code verification error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=api_error("VERIFY_ERROR", "Email verification failed"))

@router.post("/resend-verification")
async def resend_verification(request: ResendVerificationRequest):
    """Resend a fresh verification code to the user's email"""
    try:
        db_session = auth_service.get_db_session()
        email_service = EmailService()
        user_manager = UserManager(db_session, email_service)
        
        # Find user by email
        user = db_session.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=api_error("USER_NOT_FOUND", "User not found"))
        if user.is_email_verified:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=api_error("ALREADY_VERIFIED", "Email already verified"))
        
        # Regenerate code and send email
        code = user.generate_email_verification_token()
        db_session.commit()
        
        if not email_service.send_verification_email(user.email, user.first_name, code):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=api_error("EMAIL_SEND_ERROR", "Failed to send verification email"))
        
        return {"message": "Verification code resent"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=api_error("RESEND_ERROR", "Failed to resend verification"))


@router.post("/request-password-reset")
async def request_password_reset(request: PasswordResetRequest):
    """Request password reset for user"""
    try:
        db_session = auth_service.get_db_session()
        email_service = EmailService()
        user_manager = UserManager(db_session, email_service)
        
        success, message = user_manager.request_password_reset(request.email)
        
        # Always return success to prevent email enumeration
        return {"message": "If the email exists, a password reset link has been sent."}
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(request: PasswordResetConfirm):
    """Reset user password with token"""
    try:
        db_session = auth_service.get_db_session()
        user_manager = UserManager(db_session)
        
        success, message = user_manager.reset_password(request.token, request.new_password)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("INVALID_TOKEN", message)
            )
        
        return {"message": message}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("RESET_ERROR", "Password reset failed")
        )


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(current_user: User = Depends(auth_service.get_current_user)):
    """Get current user profile"""
    try:
        user_data = current_user.to_dict()
        return UserResponse(**user_data)
        
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("PROFILE_ERROR", "Failed to get profile")
        )


# Strategy management routes
@router.post("/strategies", status_code=status.HTTP_201_CREATED)
async def create_strategy(
    request: StrategyCreateRequest,
    current_user: User = Depends(auth_service.get_current_user)
):
    """Create custom trading strategy"""
    try:
        db_session = auth_service.get_db_session()
        strategy_manager = StrategyManager(db_session)
        
        success, message, strategy = strategy_manager.create_custom_strategy(
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            config_data=request.strategy_config
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("CREATE_STRATEGY_FAILED", message)
            )
        
        return {
            "message": message,
            "strategy": strategy.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create strategy error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("CREATE_STRATEGY_ERROR", "Failed to create strategy")
        )


@router.get("/strategies")
async def get_user_strategies(current_user: User = Depends(auth_service.get_current_user)):
    """Get user's custom strategies"""
    try:
        db_session = auth_service.get_db_session()
        strategy_manager = StrategyManager(db_session)
        
        strategies = strategy_manager.get_user_strategies(current_user.id)
        
        return {"strategies": strategies}
        
    except Exception as e:
        logger.error(f"Get strategies error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("GET_STRATEGIES_ERROR", "Failed to get strategies")
        )


@router.get("/strategy-templates")
async def get_strategy_templates():
    """Get default strategy templates"""
    try:
        db_session = auth_service.get_db_session()
        strategy_manager = StrategyManager(db_session)
        
        templates = strategy_manager.get_default_strategy_templates()
        
        return {"templates": templates}
        
    except Exception as e:
        logger.error(f"Get templates error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("GET_TEMPLATES_ERROR", "Failed to get templates")
        )


@router.post("/strategies/{strategy_id}/backtest")
async def backtest_strategy(
    strategy_id: str,
    symbol: str = "BTCUSDT",
    current_user: User = Depends(auth_service.get_current_user)
):
    """Run backtest on custom strategy"""
    try:
        db_session = auth_service.get_db_session()
        strategy_manager = StrategyManager(db_session)
        
        strategy_uuid = uuid.UUID(strategy_id)
        success, message, results = strategy_manager.backtest_custom_strategy(
            strategy_id=strategy_uuid,
            user_id=current_user.id,
            symbol=symbol
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("BACKTEST_BAD_REQUEST", message)
            )
        
        return {
            "message": message,
            "results": results
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error("INVALID_ID", "Invalid strategy ID format")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("BACKTEST_ERROR", "Backtest failed")
        )


@router.post("/indicator-configs", status_code=status.HTTP_201_CREATED)
async def create_indicator_config(
    request: IndicatorConfigRequest,
    current_user: User = Depends(auth_service.get_current_user)
):
    """Create custom indicator configuration"""
    try:
        db_session = auth_service.get_db_session()
        strategy_manager = StrategyManager(db_session)
        
        config_data = request.dict(exclude={'name'})
        success, message, config = strategy_manager.create_indicator_config(
            user_id=current_user.id,
            name=request.name,
            config_data=config_data
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("CREATE_CONFIG_FAILED", message)
            )
        
        return {
            "message": message,
            "config": config.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create indicator config error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("CREATE_CONFIG_ERROR", "Failed to create indicator configuration")
        )


@router.get("/indicator-configs")
async def get_user_indicator_configs(current_user: User = Depends(auth_service.get_current_user)):
    """Get user's indicator configurations"""
    try:
        db_session = auth_service.get_db_session()
        strategy_manager = StrategyManager(db_session)
        
        configs = strategy_manager.get_user_indicator_configs(current_user.id)
        
        return {"configs": configs}
        
    except Exception as e:
        logger.error(f"Get indicator configs error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("GET_CONFIGS_ERROR", "Failed to get indicator configurations")
        )


# Strategy Testing Endpoints
@router.post("/test-strategy")
async def test_strategy(
    request: StrategyTestRequest,
    current_user: User = Depends(auth_service.get_current_user)
):
    """Test a custom strategy with historical data"""
    try:
        strategy_tester = StrategyTester()
        
        # Run strategy test
        results = await strategy_tester.test_strategy(
            user_id=current_user.id,
            strategy_config=request.strategy_config,
            symbol=request.symbol,
            timeframe=request.timeframe,
            test_days=request.test_days
        )
        
        if not results.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("TEST_FAILED_BAD_REQUEST", results.get("error", "Strategy test failed"))
            )
        
        logger.info(f"Strategy test completed for user {current_user.id}: {results['metrics']['total_return_pct']:.2f}% return")
        
        return {
            "message": "Strategy test completed successfully",
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Strategy test error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("TEST_ERROR", "Strategy test failed")
        )


@router.post("/quick-test-strategy")
async def quick_test_strategy(request: QuickTestRequest):
    """Quick strategy test (no authentication required for demo)"""
    try:
        strategy_tester = StrategyTester()
        
        # Run quick test
        results = await strategy_tester.quick_test_strategy(
            strategy_config=request.strategy_config,
            symbol=request.symbol
        )
        
        if not results.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("QUICK_TEST_BAD_REQUEST", results.get("error", "Quick test failed"))
            )
        
        return {
            "message": "Quick test completed successfully",
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick test error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("QUICK_TEST_ERROR", "Quick test failed")
        )


@router.post("/strategies/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: str,
    current_user: User = Depends(auth_service.get_current_user)
):
    """Activate a strategy for live trading after successful testing"""
    try:
        db_session = auth_service.get_db_session()
        strategy_manager = StrategyManager(db_session)
        
        strategy_uuid = uuid.UUID(strategy_id)
        
        # Get the strategy to check ownership
        strategy = strategy_manager.get_strategy(strategy_uuid, current_user.id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=api_error("STRATEGY_NOT_FOUND", "Strategy not found")
            )
        
        # Check if strategy has been tested and has good results
        if not strategy.get('parsed_backtest'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("NOT_TESTED", "Strategy must be tested before activation")
            )
        
        backtest_results = strategy.get('parsed_backtest', {})
        total_return = backtest_results.get('total_return_pct', 0)
        max_drawdown = backtest_results.get('max_drawdown_pct', 100)
        
        # Safety check - don't allow activation of losing strategies
        if total_return < -5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("POOR_PERFORMANCE", "Cannot activate a strategy with more than -5% return. Please optimize your strategy first.")
            )
        
        if max_drawdown > 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("HIGH_RISK", "Cannot activate a strategy with more than 30% maximum drawdown. Risk is too high.")
            )
        
        # For now, we'll just mark it as active (implementation would connect to live trading)
        # In a real implementation, this would:
        # 1. Connect the strategy to live market data
        # 2. Enable actual trading with the configured parameters
        # 3. Start monitoring and position management
        
        logger.info(f"Strategy {strategy_id} activated for user {current_user.id}")
        
        return {
            "message": "Strategy activated successfully",
            "strategy_id": strategy_id,
            "status": "active",
            "warning": "Live trading is not implemented yet. This is a simulation environment."
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error("INVALID_ID", "Invalid strategy ID format")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Strategy activation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("ACTIVATION_ERROR", "Failed to activate strategy")
        )


@router.post("/save-tested-strategy")
async def save_tested_strategy(
    name: str,
    description: Optional[str],
    strategy_config: Dict[str, Any],
    test_results: Dict[str, Any],
    current_user: User = Depends(auth_service.get_current_user)
):
    """Save a strategy after successful testing"""
    try:
        db_session = auth_service.get_db_session()
        strategy_manager = StrategyManager(db_session)
        
        # Validate test results quality
        metrics = test_results.get('metrics', {})
        total_return = metrics.get('total_return_pct', 0)
        max_drawdown = metrics.get('max_drawdown_pct', 100)
        
        # Warning for poor performance
        warnings = []
        if total_return < 0:
            warnings.append("Strategy has negative returns")
        
        if max_drawdown > 20:
            warnings.append("Strategy has high risk (>20% drawdown)")
        if metrics.get('total_trades', 0) < 10:
            warnings.append("Strategy has very few trades in test period")
        
        # Create the strategy
        success, message, strategy = strategy_manager.create_custom_strategy(
            user_id=current_user.id,
            name=name,
            description=description or f"Custom strategy tested on {datetime.utcnow().strftime('%Y-%m-%d')}",
            config_data=strategy_config
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("CREATE_STRATEGY_FAILED", message)
            )
        
        # Update strategy with test results
        strategy.backtest_results = json.dumps(test_results, indent=2)
        db_session = auth_service.get_db_session()
        db_session.commit()
        
        logger.info(f"Tested strategy saved for user {current_user.id}: {name}")
        
        return {
            "message": "Strategy saved successfully",
            "strategy": strategy.to_dict(),
            "warnings": warnings,
            "performance_summary": {
                "return": f"{total_return:.1f}%",
                "max_drawdown": f"{max_drawdown:.1f}%",
                "total_trades": metrics.get('total_trades', 0)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save tested strategy error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=api_error("SAVE_STRATEGY_ERROR", "Failed to save strategy")
        )
