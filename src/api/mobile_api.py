"""
Mobile API endpoints for React Native application
Provides authentication, strategy management, and dashboard data APIs
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from ..database.connection import get_db_session
from ..user_management.user_manager import UserManager
from ..user_management.strategy_manager import StrategyManager
from loguru import logger

# Create API router
mobile_router = APIRouter(prefix="/api/v1", tags=["Mobile API"])
security = HTTPBearer()

# Pydantic models for request/response
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    telegram_id: Optional[str] = None

class StrategyRequest(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]

class TestStrategyRequest(BaseModel):
    symbol: str

class LayoutPreferencesRequest(BaseModel):
    asset_order: List[str]

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    telegram_id: Optional[str]
    is_active: bool
    is_email_verified: bool
    last_login: Optional[datetime]
    created_at: datetime

class SessionResponse(BaseModel):
    session_token: str
    user: UserResponse
    expires_at: datetime

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

# Dependency to get current user from token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
):
    """Extract user from authorization token"""
    token = credentials.credentials
    user_manager = UserManager(db)
    user = user_manager.validate_session(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token"
        )
    
    return user

# Authentication endpoints
@mobile_router.post("/auth/login", response_model=SessionResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db_session)
):
    """User login endpoint"""
    try:
        from ..user_management.models import User, UserSession
        from datetime import datetime
        
        # Find user by email
        user = db.query(User).filter(User.email == login_data.email).first()
        
        if not user or not user.check_password(login_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active"
            )
        
        # Create new session
        session = UserSession.create_session(user.id)
        session.user_agent = "Mobile App"
        session.ip_address = "mobile"
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        db.add(session)
        db.commit()
        
        # Refresh to get user relationship
        db.refresh(session)
        
        return SessionResponse(
            session_token=session.session_token,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=user.phone,
                telegram_id=user.telegram_id,
                is_active=user.is_active,
                is_email_verified=user.is_email_verified,
                last_login=user.last_login,
                created_at=user.created_at
            ),
            expires_at=session.expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        logger.error(f"Login error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@mobile_router.post("/auth/register", response_model=ApiResponse)
async def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db_session)
):
    """User registration endpoint"""
    try:
        # For test mode, create user directly
        import os
        AUTH_TEST_MODE = os.getenv("AUTH_TEST_MODE", "false").lower() == "true"
        
        if AUTH_TEST_MODE:
            from ..user_management.models import User
            from werkzeug.security import generate_password_hash
            
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == register_data.email).first()
            if existing_user:
                return ApiResponse(
                    success=False,
                    message="User with this email already exists"
                )
            
            # Create new user directly
            user = User(
                email=register_data.email,
                first_name=register_data.first_name,
                last_name=register_data.last_name,
                phone=register_data.phone,
                telegram_id=register_data.telegram_id,
                is_active=True,  # Auto-activate in test mode
                is_email_verified=True  # Auto-verify in test mode
            )
            user.set_password(register_data.password)
            
            db.add(user)
            db.commit()
            
            return ApiResponse(
                success=True,
                message="User registered successfully (test mode - auto-verified)"
            )
        
        # For production mode (not implemented yet)
        return ApiResponse(
            success=False,
            message="Registration not implemented for production mode"
        )
        
    except Exception as e:
        db.rollback()
        import traceback
        logger.error(f"Registration error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@mobile_router.post("/auth/logout", response_model=ApiResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
):
    """User logout endpoint"""
    try:
        token = credentials.credentials
        user_manager = UserManager(db)
        success = user_manager.logout_user(token)
        
        return ApiResponse(
            success=success,
            message="Logged out successfully" if success else "Logout failed"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@mobile_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        telegram_id=current_user.telegram_id,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        last_login=current_user.last_login,
        created_at=current_user.created_at
    )

# Password reset endpoints
class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetVerifyRequest(BaseModel):
    email: EmailStr
    verification_code: str

class PasswordResetCompleteRequest(BaseModel):
    email: EmailStr
    new_password: str

@mobile_router.post("/auth/request-password-reset", response_model=ApiResponse)
async def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db_session)
):
    """Request password reset"""
    try:
        # For test mode, always return success
        import os
        AUTH_TEST_MODE = os.getenv("AUTH_TEST_MODE", "false").lower() == "true"
        
        if AUTH_TEST_MODE:
            return ApiResponse(
                success=True,
                message="If the email exists, a password reset code has been sent. Use code 111111 for test mode."
            )
        
        # For production mode (not implemented yet)
        return ApiResponse(
            success=False,
            message="Password reset not implemented for production mode"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )

@mobile_router.post("/auth/verify-password-reset", response_model=ApiResponse)
async def verify_password_reset(
    request: PasswordResetVerifyRequest,
    db: Session = Depends(get_db_session)
):
    """Verify password reset code"""
    try:
        # For test mode, accept default code "111111"
        import os
        AUTH_TEST_MODE = os.getenv("AUTH_TEST_MODE", "false").lower() == "true"
        
        if AUTH_TEST_MODE and request.verification_code == "111111":
            return ApiResponse(
                success=True,
                message="Verification code accepted (test mode)"
            )
        
        # For production, validate against actual token (not implemented yet)
        return ApiResponse(
            success=False,
            message="Password reset verification not implemented"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset verification failed"
        )

@mobile_router.post("/auth/reset-password", response_model=ApiResponse)
async def reset_password(
    request: PasswordResetCompleteRequest,
    db: Session = Depends(get_db_session)
):
    """Complete password reset"""
    try:
        # Simple implementation - find user by email and reset password
        from ..user_management.models import User
        
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            return ApiResponse(
                success=False,
                message="User not found"
            )
        
        # Validate new password
        if len(request.new_password) < 8:
            return ApiResponse(
                success=False,
                message="Password must be at least 8 characters long"
            )
        
        # Set new password
        user.set_password(request.new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        db.commit()
        
        return ApiResponse(
            success=True,
            message="Password reset successful"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )

# Email verification endpoints
class EmailVerificationRequest(BaseModel):
    email: EmailStr
    verification_code: str

@mobile_router.post("/auth/verify-email", response_model=ApiResponse)
async def verify_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db_session)
):
    """Verify email address"""
    try:
        from ..user_management.models import User
        
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            return ApiResponse(
                success=False,
                message="User not found"
            )
        
        # For test mode, accept default code "111111"
        import os
        AUTH_TEST_MODE = os.getenv("AUTH_TEST_MODE", "false").lower() == "true"
        
        if AUTH_TEST_MODE and request.verification_code == "111111":
            user.is_email_verified = True
            user.is_active = True
            user.email_verification_token = None
            user.email_verification_expires = None
            db.commit()
            
            return ApiResponse(
                success=True,
                message="Email verified successfully (test mode)"
            )
        
        return ApiResponse(
            success=False,
            message="Email verification not implemented for production"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )

@mobile_router.post("/auth/resend-verification", response_model=ApiResponse)
async def resend_verification(
    request: PasswordResetRequest,  # Reuse since it only has email
    db: Session = Depends(get_db_session)
):
    """Resend email verification code"""
    try:
        # For test mode, always return success
        import os
        AUTH_TEST_MODE = os.getenv("AUTH_TEST_MODE", "false").lower() == "true"
        
        if AUTH_TEST_MODE:
            return ApiResponse(
                success=True,
                message="Verification code resent (use 111111 for test mode)"
            )
        
        return ApiResponse(
            success=False,
            message="Email verification not implemented for production"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification code"
        )

# Strategy endpoints
@mobile_router.post("/strategies/create", response_model=ApiResponse)
async def create_strategy(
    strategy_data: StrategyRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new trading strategy"""
    try:
        from ..user_management.models import CustomStrategy
        import json
        
        # Create strategy directly in the database
        strategy = CustomStrategy(
            user_id=current_user.id,
            name=strategy_data.name.strip(),
            description=strategy_data.description.strip() if strategy_data.description else None,
            strategy_config=json.dumps(strategy_data.parameters),
            is_active=True
        )
        
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        
        logger.info(f"Strategy created successfully: {strategy_data.name} for user {current_user.id}")
        
        return ApiResponse(
            success=True,
            message="Strategy created successfully",
            data={"strategy_id": str(strategy.id)}
        )
        
    except Exception as e:
        db.rollback()
        import traceback
        logger.error(f"Strategy creation error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strategy creation failed: {str(e)}"
        )

@mobile_router.post("/strategies/{strategy_id}/test", response_model=ApiResponse)
async def test_strategy(
    strategy_id: str,
    test_data: TestStrategyRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Run backtest for a strategy"""
    try:
        from ..user_management.models import CustomStrategy
        import json
        import random
        
        # Convert string ID to UUID and verify strategy exists
        try:
            strategy_uuid = uuid.UUID(strategy_id)
        except ValueError:
            return ApiResponse(
                success=False,
                message="Invalid strategy ID format"
            )
        
        # Check if strategy belongs to user
        strategy = db.query(CustomStrategy).filter(
            CustomStrategy.id == strategy_uuid,
            CustomStrategy.user_id == current_user.id,
            CustomStrategy.is_active == True
        ).first()
        
        if not strategy:
            return ApiResponse(
                success=False,
                message="Strategy not found or not accessible"
            )
        
        # For test mode, return mock backtest results
        import os
        AUTH_TEST_MODE = os.getenv("AUTH_TEST_MODE", "false").lower() == "true"
        
        if AUTH_TEST_MODE:
            # Generate realistic mock backtest results
            mock_result = {
                "strategy_name": strategy.name,
                "symbol": test_data.symbol,
                "total_trades": random.randint(50, 200),
                "winning_trades": random.randint(30, 120),
                "total_return": round(random.uniform(-10, 25), 2),
                "max_drawdown": round(random.uniform(5, 15), 2),
                "sharpe_ratio": round(random.uniform(0.8, 2.5), 2),
                "test_period": "30 days",
                "parameters": json.loads(strategy.strategy_config)
            }
            
            return ApiResponse(
                success=True,
                message="Backtest completed successfully (test mode)",
                data=mock_result
            )
        
        # For production mode
        return ApiResponse(
            success=False,
            message="Backtest not implemented for production mode"
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid strategy ID format"
        )
    except Exception as e:
        import traceback
        logger.error(f"Strategy test error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strategy test failed: {str(e)}"
        )

@mobile_router.get("/strategies/my-strategies", response_model=ApiResponse)
async def get_user_strategies(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get user's strategies"""
    try:
        user_manager = UserManager(db)
        strategies = user_manager.get_user_strategies(current_user.id)
        
        strategies_data = []
        for strategy in strategies:
            strategies_data.append({
                "id": str(strategy.id),
                "name": strategy.name,
                "description": strategy.description,
                "created_at": strategy.created_at,
                "is_active": strategy.is_active
            })
        
        return ApiResponse(
            success=True,
            message="Strategies retrieved successfully",
            data=strategies_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve strategies"
        )

@mobile_router.post("/strategies/{strategy_id}/activate", response_model=ApiResponse)
async def activate_strategy(
    strategy_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Activate a strategy"""
    try:
        # In a real implementation, you would:
        # 1. Validate the strategy belongs to the user
        # 2. Activate the strategy in the database
        # 3. Possibly restart/update the trading engine
        
        return ApiResponse(
            success=True,
            message="Strategy activated successfully"
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid strategy ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Strategy activation failed"
        )

# Dashboard endpoints
@mobile_router.get("/dashboard/symbols", response_model=ApiResponse)
async def get_symbol_data():
    """Get current symbol data for dashboard"""
    try:
        # This would normally fetch real-time data
        # For now, return sample data
        symbols_data = {
            "BTC": {
                "price": 45000.00,
                "signal": "BUY",
                "indicators": {"RSI": 65.5, "MACD": 120.5, "BB_UPPER": 46000, "BB_LOWER": 44000},
                "timestamp": datetime.utcnow().isoformat()
            },
            "ETH": {
                "price": 3200.00,
                "signal": "NEUTRAL",
                "indicators": {"RSI": 52.3, "MACD": -15.2, "BB_UPPER": 3250, "BB_LOWER": 3150},
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        return ApiResponse(
            success=True,
            message="Symbol data retrieved successfully",
            data=symbols_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve symbol data"
        )

# User preferences endpoints
@mobile_router.get("/user/layout-preferences", response_model=ApiResponse)
async def get_user_layout_preferences(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get user's layout preferences"""
    try:
        user_manager = UserManager(db)
        preferences = user_manager.get_user_preferences(current_user.id)
        
        # If no preferences exist, return empty preferences
        if not preferences:
            return ApiResponse(
                success=True,
                message="No preferences found",
                data={"asset_order": []}
            )
        
        return ApiResponse(
            success=True,
            message="Preferences retrieved successfully",
            data={"asset_order": preferences.get("asset_order", [])}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve layout preferences"
        )

@mobile_router.post("/user/layout-preferences", response_model=ApiResponse)
async def save_user_layout_preferences(
    preferences: LayoutPreferencesRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Save user's layout preferences"""
    try:
        user_manager = UserManager(db)
        success = user_manager.save_user_preferences(
            current_user.id, 
            {"asset_order": preferences.asset_order}
        )
        
        return ApiResponse(
            success=success,
            message="Preferences saved successfully" if success else "Failed to save preferences"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save layout preferences"
        )