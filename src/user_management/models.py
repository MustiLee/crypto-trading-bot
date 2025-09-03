"""
User management models using SQLAlchemy
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

Base = declarative_base()


class User(Base):
    """User model for registration and authentication"""
    
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(254), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=True)
    telegram_id = Column(String(50), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    custom_strategies = relationship("CustomStrategy", back_populates="user", cascade="all, delete-orphan")
    user_sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def set_password(self, password: str):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def generate_email_verification_token(self) -> str:
        """Generate a short 6-digit email verification code"""
        code = str(secrets.randbelow(10**6)).zfill(6)
        self.email_verification_token = code
        # Token expires in 24 hours
        self.email_verification_expires = datetime.utcnow().replace(tzinfo=timezone.utc) + \
                                          datetime.timedelta(hours=24)
        return self.email_verification_token
    
    def generate_password_reset_token(self) -> str:
        """Generate password reset token"""
        self.password_reset_token = secrets.token_urlsafe(32)
        # Token expires in 1 hour
        self.password_reset_expires = datetime.utcnow().replace(tzinfo=timezone.utc) + \
                                      datetime.timedelta(hours=1)
        return self.password_reset_token
    
    def verify_email_token(self, token: str) -> bool:
        """Verify email verification token"""
        if not self.email_verification_token or not self.email_verification_expires:
            return False
        
        if datetime.utcnow().replace(tzinfo=timezone.utc) > self.email_verification_expires:
            return False
        
        if self.email_verification_token == token:
            self.is_email_verified = True
            self.is_active = True
            self.email_verification_token = None
            self.email_verification_expires = None
            return True
        
        return False
    
    def verify_password_reset_token(self, token: str) -> bool:
        """Verify password reset token"""
        if not self.password_reset_token or not self.password_reset_expires:
            return False
        
        if datetime.utcnow().replace(tzinfo=timezone.utc) > self.password_reset_expires:
            return False
        
        return self.password_reset_token == token
    
    def to_dict(self):
        """Convert user to dictionary (excluding sensitive data)"""
        return {
            'id': str(self.id),
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'telegram_id': self.telegram_id,
            'is_active': self.is_active,
            'is_email_verified': self.is_email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class UserSession(Base):
    """User session model for authentication tracking"""
    
    __tablename__ = 'user_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="user_sessions")
    
    @classmethod
    def create_session(cls, user_id: uuid.UUID, expires_hours: int = 24):
        """Create new user session"""
        session = cls(
            user_id=user_id,
            session_token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow().replace(tzinfo=timezone.utc) + datetime.timedelta(hours=expires_hours)
        )
        return session
    
    def is_valid(self) -> bool:
        """Check if session is still valid"""
        return datetime.utcnow().replace(tzinfo=timezone.utc) < self.expires_at


class CustomStrategy(Base):
    """Custom user-defined trading strategies"""
    
    __tablename__ = 'custom_strategies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Strategy configuration (JSON stored as text)
    strategy_config = Column(Text, nullable=False)  # JSON string
    
    # Performance tracking
    backtest_results = Column(Text, nullable=True)  # JSON string
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="custom_strategies")
    
    def to_dict(self):
        """Convert strategy to dictionary"""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'strategy_config': self.strategy_config,
            'backtest_results': self.backtest_results,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class IndicatorConfig(Base):
    """User-customized indicator configurations"""
    
    __tablename__ = 'indicator_configs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    
    # Bollinger Bands
    bb_period = Column(Integer, default=20)
    bb_std = Column(Float, default=2.0)
    
    # MACD
    macd_fast = Column(Integer, default=12)
    macd_slow = Column(Integer, default=26)
    macd_signal = Column(Integer, default=9)
    
    # RSI
    rsi_period = Column(Integer, default=14)
    rsi_overbought = Column(Float, default=70.0)
    rsi_oversold = Column(Float, default=30.0)
    
    # EMA
    ema_short = Column(Integer, default=20)
    ema_long = Column(Integer, default=50)
    ema_trend = Column(Integer, default=200)
    
    # ATR
    atr_period = Column(Integer, default=14)
    
    # Advanced indicators
    use_volume_indicators = Column(Boolean, default=True)
    use_volatility_indicators = Column(Boolean, default=True)
    use_momentum_indicators = Column(Boolean, default=True)
    use_trend_indicators = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    is_default = Column(Boolean, default=False)
    
    def to_dict(self):
        """Convert indicator config to dictionary"""
        return {
            'id': str(self.id),
            'name': self.name,
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'macd_fast': self.macd_fast,
            'macd_slow': self.macd_slow,
            'macd_signal': self.macd_signal,
            'rsi_period': self.rsi_period,
            'rsi_overbought': self.rsi_overbought,
            'rsi_oversold': self.rsi_oversold,
            'ema_short': self.ema_short,
            'ema_long': self.ema_long,
            'ema_trend': self.ema_trend,
            'atr_period': self.atr_period,
            'use_volume_indicators': self.use_volume_indicators,
            'use_volatility_indicators': self.use_volatility_indicators,
            'use_momentum_indicators': self.use_momentum_indicators,
            'use_trend_indicators': self.use_trend_indicators,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
