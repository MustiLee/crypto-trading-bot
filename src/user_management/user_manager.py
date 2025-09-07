"""
User management service for registration, authentication, and profile management
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from loguru import logger
from email_validator import validate_email, EmailNotValidError

from .models import User, UserSession, CustomStrategy, IndicatorConfig

# Try to import email service, but don't fail if dependencies missing
try:
    from .email_service import EmailService
    EMAIL_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Email service not available: {e}")
    EmailService = None
    EMAIL_SERVICE_AVAILABLE = False


class UserManager:
    """Service class for user management operations"""
    
    def __init__(self, db_session: Session, email_service = None):
        self.db_session = db_session
        if EMAIL_SERVICE_AVAILABLE and email_service is None:
            self.email_service = EmailService()
        else:
            self.email_service = email_service
    
    def register_user(self, email: str, password: str, first_name: str, 
                     last_name: str, phone: str = None, telegram_id: str = None) -> Tuple[bool, str, Optional[User]]:
        """
        Register a new user
        
        Args:
            email: User email address
            password: User password (will be hashed)
            first_name: User first name
            last_name: User last name
            phone: Optional phone number
            telegram_id: Optional Telegram ID
            
        Returns:
            Tuple of (success, message, user_object)
        """
        try:
            # Validate email format
            try:
                valid_email = validate_email(email)
                email = valid_email.email
            except EmailNotValidError:
                return False, "Invalid email format", None
            
            # Check if user already exists
            existing_user = self.db_session.query(User).filter(User.email == email).first()
            if existing_user:
                return False, "User with this email already exists", None
            
            # Validate password strength
            if len(password) < 8:
                return False, "Password must be at least 8 characters long", None
            
            # Create new user
            user = User(
                email=email,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                phone=phone.strip() if phone else None,
                telegram_id=telegram_id.strip() if telegram_id else None
            )
            user.set_password(password)
            
            # Generate email verification token
            verification_token = user.generate_email_verification_token()
            
            # Add to database
            self.db_session.add(user)
            self.db_session.commit()
            
            # Create default indicator config
            self._create_default_indicator_config(user.id)
            
            # Send verification email
            if self.email_service:
                email_sent = self.email_service.send_verification_email(
                    email, first_name, verification_token
                )
                if not email_sent:
                    logger.warning(f"Failed to send verification email to {email}")
            
            logger.info(f"User registered successfully: {email}")
            return True, "User registered successfully. Please check your email for verification.", user
            
        except IntegrityError as e:
            self.db_session.rollback()
            logger.error(f"Database error during user registration: {e}")
            return False, "User registration failed due to database error", None
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Unexpected error during user registration: {e}")
            return False, "User registration failed", None
    
    def verify_email(self, token: str) -> Tuple[bool, str]:
        """
        Verify user email with token
        
        Args:
            token: Email verification token
            
        Returns:
            Tuple of (success, message)
        """
        try:
            user = self.db_session.query(User).filter(
                User.email_verification_token == token
            ).first()
            
            if not user:
                return False, "Invalid verification token"
            
            if user.verify_email_token(token):
                self.db_session.commit()
                logger.info(f"Email verified successfully for user: {user.email}")
                return True, "Email verified successfully. Your account is now active."
            else:
                return False, "Verification token has expired"
                
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error during email verification: {e}")
            return False, "Email verification failed"
    
    def authenticate_user(self, email: str, password: str, user_agent: str = None, 
                         ip_address: str = None) -> Tuple[bool, str, Optional[UserSession]]:
        """
        Authenticate user and create session
        
        Args:
            email: User email
            password: User password
            user_agent: User agent string
            ip_address: Client IP address
            
        Returns:
            Tuple of (success, message, session)
        """
        try:
            user = self.db_session.query(User).filter(User.email == email).first()
            
            if not user or not user.check_password(password):
                return False, "Invalid email or password", None
            
            if not user.is_active:
                return False, "Account is not active. Please verify your email.", None
            
            if not user.is_email_verified:
                return False, "Please verify your email address before logging in.", None
            
            # Create new session
            session = UserSession.create_session(user.id)
            session.user_agent = user_agent
            session.ip_address = ip_address
            
            # Update last login
            user.last_login = datetime.utcnow()
            
            self.db_session.add(session)
            self.db_session.commit()
            
            logger.info(f"User authenticated successfully: {email}")
            return True, "Login successful", session
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error during user authentication: {e}")
            return False, "Authentication failed", None
    
    def validate_session(self, session_token: str) -> Optional[User]:
        """
        Validate user session and return user
        
        Args:
            session_token: Session token to validate
            
        Returns:
            User object if valid, None otherwise
        """
        try:
            session = self.db_session.query(UserSession).filter(
                UserSession.session_token == session_token
            ).first()
            
            if not session or not session.is_valid():
                return None
            
            return session.user
            
        except Exception as e:
            logger.error(f"Error during session validation: {e}")
            return None
    
    def logout_user(self, session_token: str) -> bool:
        """
        Logout user by invalidating session
        
        Args:
            session_token: Session token to invalidate
            
        Returns:
            True if successful
        """
        try:
            session = self.db_session.query(UserSession).filter(
                UserSession.session_token == session_token
            ).first()
            
            if session:
                self.db_session.delete(session)
                self.db_session.commit()
                logger.info(f"User session invalidated: {session_token[:8]}...")
                return True
                
            return False
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error during logout: {e}")
            return False
    
    def request_password_reset(self, email: str) -> Tuple[bool, str]:
        """
        Request password reset for user
        
        Args:
            email: User email address
            
        Returns:
            Tuple of (success, message)
        """
        try:
            user = self.db_session.query(User).filter(User.email == email).first()
            
            if not user:
                # Don't reveal if email exists
                return True, "If the email exists, a password reset link has been sent."
            
            # Generate password reset token
            reset_token = user.generate_password_reset_token()
            self.db_session.commit()
            
            # Send password reset email
            if self.email_service:
                email_sent = self.email_service.send_password_reset_email(
                    email, user.first_name, reset_token
                )
                if not email_sent:
                    logger.warning(f"Failed to send password reset email to {email}")
            
            logger.info(f"Password reset requested for user: {email}")
            return True, "If the email exists, a password reset link has been sent."
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error during password reset request: {e}")
            return False, "Password reset request failed"
    
    def reset_password(self, token: str, new_password: str) -> Tuple[bool, str]:
        """
        Reset user password with token
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            Tuple of (success, message)
        """
        try:
            user = self.db_session.query(User).filter(
                User.password_reset_token == token
            ).first()
            
            if not user:
                return False, "Invalid reset token"
            
            if not user.verify_password_reset_token(token):
                return False, "Reset token has expired"
            
            # Validate new password
            if len(new_password) < 8:
                return False, "Password must be at least 8 characters long"
            
            # Set new password and clear reset token
            user.set_password(new_password)
            user.password_reset_token = None
            user.password_reset_expires = None
            
            self.db_session.commit()
            
            logger.info(f"Password reset successfully for user: {user.email}")
            return True, "Password reset successfully"
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error during password reset: {e}")
            return False, "Password reset failed"
    
    def create_custom_strategy(self, user_id: uuid.UUID, name: str, description: str, 
                              strategy_config: Dict) -> Tuple[bool, str, Optional[CustomStrategy]]:
        """
        Create custom strategy for user
        
        Args:
            user_id: User ID
            name: Strategy name
            description: Strategy description
            strategy_config: Strategy configuration dictionary
            
        Returns:
            Tuple of (success, message, strategy)
        """
        try:
            strategy = CustomStrategy(
                user_id=user_id,
                name=name.strip(),
                description=description.strip() if description else None,
                strategy_config=json.dumps(strategy_config)
            )
            
            self.db_session.add(strategy)
            self.db_session.commit()
            
            logger.info(f"Custom strategy created: {name} for user {user_id}")
            return True, "Strategy created successfully", strategy
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error creating custom strategy: {e}")
            return False, "Failed to create strategy", None
    
    def get_user_strategies(self, user_id: uuid.UUID) -> List[CustomStrategy]:
        """
        Get all strategies for user
        
        Args:
            user_id: User ID
            
        Returns:
            List of user strategies
        """
        try:
            strategies = self.db_session.query(CustomStrategy).filter(
                CustomStrategy.user_id == user_id,
                CustomStrategy.is_active == True
            ).all()
            
            return strategies
            
        except Exception as e:
            logger.error(f"Error getting user strategies: {e}")
            return []
    
    def _create_default_indicator_config(self, user_id: uuid.UUID):
        """Create default indicator configuration for new user"""
        try:
            config = IndicatorConfig(
                user_id=user_id,
                name="Default Configuration",
                is_default=True
            )
            
            self.db_session.add(config)
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Error creating default indicator config: {e}")
    
    def cleanup_expired_sessions(self):
        """Clean up expired user sessions"""
        try:
            expired_count = self.db_session.query(UserSession).filter(
                UserSession.expires_at < datetime.utcnow()
            ).delete()
            
            self.db_session.commit()
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
                
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error cleaning up expired sessions: {e}")
    
    def get_user_preferences(self, user_id: uuid.UUID) -> dict:
        """
        Get user preferences from the database
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of user preferences or None if not found
        """
        try:
            user = self.db_session.query(User).filter(User.id == user_id).first()
            
            if not user or not user.preferences:
                return {}
            
            # Parse JSON preferences if they exist
            import json
            try:
                return json.loads(user.preferences)
            except (json.JSONDecodeError, TypeError):
                return {}
                
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {}
    
    def save_user_preferences(self, user_id: uuid.UUID, preferences: dict) -> bool:
        """
        Save user preferences to the database
        
        Args:
            user_id: User ID
            preferences: Dictionary of preferences to save
            
        Returns:
            True if successful
        """
        try:
            user = self.db_session.query(User).filter(User.id == user_id).first()
            
            if not user:
                logger.error(f"User not found: {user_id}")
                return False
            
            # Convert preferences to JSON string
            import json
            user.preferences = json.dumps(preferences)
            
            self.db_session.commit()
            logger.info(f"User preferences saved for user {user_id}")
            return True
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving user preferences: {e}")
            return False