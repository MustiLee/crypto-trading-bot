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
        user_manager = UserManager(db)
        success, message, session = user_manager.authenticate_user(
            email=login_data.email,
            password=login_data.password,
            user_agent="Mobile App",
            ip_address="mobile"
        )
        
        if not success or not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        
        return SessionResponse(
            session_token=session.session_token,
            user=UserResponse(
                id=str(session.user.id),
                email=session.user.email,
                first_name=session.user.first_name,
                last_name=session.user.last_name,
                phone=session.user.phone,
                telegram_id=session.user.telegram_id,
                is_active=session.user.is_active,
                is_email_verified=session.user.is_email_verified,
                last_login=session.user.last_login,
                created_at=session.user.created_at
            ),
            expires_at=session.expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@mobile_router.post("/auth/register", response_model=ApiResponse)
async def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db_session)
):
    """User registration endpoint"""
    try:
        user_manager = UserManager(db)
        success, message, user = user_manager.register_user(
            email=register_data.email,
            password=register_data.password,
            first_name=register_data.first_name,
            last_name=register_data.last_name,
            phone=register_data.phone,
            telegram_id=register_data.telegram_id
        )
        
        return ApiResponse(
            success=success,
            message=message
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
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

# Strategy endpoints
@mobile_router.post("/strategies/create", response_model=ApiResponse)
async def create_strategy(
    strategy_data: StrategyRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new trading strategy"""
    try:
        strategy_manager = StrategyManager(db)
        success, message, strategy = strategy_manager.create_strategy(
            user_id=current_user.id,
            name=strategy_data.name,
            description=strategy_data.description,
            strategy_config=strategy_data.parameters
        )
        
        return ApiResponse(
            success=success,
            message=message,
            data={"strategy_id": str(strategy.id)} if strategy else None
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Strategy creation failed"
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
        strategy_manager = StrategyManager(db)
        
        # Convert string ID to UUID
        strategy_uuid = uuid.UUID(strategy_id)
        
        success, message, result = await strategy_manager.backtest_custom_strategy(
            strategy_id=strategy_uuid,
            user_id=current_user.id,
            symbol=test_data.symbol
        )
        
        return ApiResponse(
            success=success,
            message=message,
            data=result
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid strategy ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Strategy test failed"
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