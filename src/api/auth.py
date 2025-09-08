from fastapi import APIRouter, HTTPException, Depends, status, Body, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import secrets
import hashlib
import jwt
from datetime import datetime, timedelta, timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from loguru import logger

from ..database.db_manager import TradingDBManager as Database
from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Pydantic models for request/response
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str

class LoginRequest(BaseModel):
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
    last_login: Optional[str]
    created_at: str

class UserSessionResponse(BaseModel):
    session_token: str
    user: UserResponse
    expires_at: str

class RegisterResponse(BaseModel):
    success: bool
    message: str

class VerificationCodeRequest(BaseModel):
    email: EmailStr

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    verification_code: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetVerifyRequest(BaseModel):
    email: EmailStr
    verification_code: str

class PasswordResetFinalizeRequest(BaseModel):
    email: EmailStr
    new_password: str

class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    telegram_id: Optional[str] = None

# JWT settings
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Email settings (configure these environment variables)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_EMAIL = os.getenv('SMTP_EMAIL', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
AUTH_TEST_MODE = os.getenv('AUTH_TEST_MODE', 'true').lower() == 'true'

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        salt, password_hash = hashed.split(':')
        return password_hash == hashlib.sha256((password + salt).encode()).hexdigest()
    except:
        return False

def generate_jwt_token(user_id: str) -> str:
    """Generate JWT token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def generate_verification_code() -> str:
    """Generate 6-digit verification code. Fixed in test mode."""
    if AUTH_TEST_MODE:
        return "111111"
    return f"{secrets.randbelow(1000000):06d}"

async def send_verification_email(email: str, verification_code: str, purpose: str = "verification"):
    """Send verification/reset email. Skips SMTP in test mode."""
    subject_map = {
        "verification": "E-posta Doğrulama Kodu",
        "password_reset": "Şifre Sıfırlama Kodu",
    }
    subject = subject_map.get(purpose, "Doğrulama Kodu")
    html_body = f"""
    <html><body>
      <h2>{subject}</h2>
      <p>Kodunuz:</p>
      <div style='font-size:24px;font-weight:700;letter-spacing:3px'>{verification_code}</div>
      <p>Bu kod 10 dakika içinde geçerlidir.</p>
    </body></html>
    """
    if AUTH_TEST_MODE:
        logger.info(f"Test mode: {purpose} code for {email} is {verification_code}")
        return
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_EMAIL
        msg['To'] = email
        msg.attach(MIMEText(html_body, 'html'))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            if SMTP_EMAIL and SMTP_PASSWORD:
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, [email], msg.as_string())
    except Exception as e:
        logger.error(f"Failed to send {purpose} email to {email}: {e}")

def validate_password_strength(password: str) -> Optional[str]:
    """Return None if strong; otherwise return message describing issue"""
    if len(password) < 8:
        return "Şifre en az 8 karakter olmalıdır."
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_upper and has_lower and has_digit):
        return "Şifre büyük/küçük harf ve rakam içermelidir."
    return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token süresi dolmuş"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz token"
        )

@router.post("/register", response_model=RegisterResponse)
async def register_user(request: RegisterRequest):
    """Register new user"""
    db = Database()
    
    try:
        # Check if user already exists
        conn = db.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id FROM users WHERE email = %s", (request.email,))
            result = cursor.fetchone()
        conn.close()
        
        if result:
            return RegisterResponse(
                success=False, 
                message="Bu email adresi zaten kullanılıyor."
            )
        
        # Validate password
        pw_err = validate_password_strength(request.password)
        if pw_err:
            return RegisterResponse(success=False, message=pw_err)
        # Hash password
        hashed_password = hash_password(request.password)
        
        # Generate verification code
        verification_code = generate_verification_code()
        
        # Store verification code temporarily (expires in 10 minutes)
        expire_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        conn = db.get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO email_verifications (email, verification_code, expires_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    verification_code = EXCLUDED.verification_code,
                    expires_at = EXCLUDED.expires_at
            """, (request.email, verification_code, expire_time))
            conn.commit()
        conn.close()
        
        # Store user data temporarily (will be activated after email verification)
        now = datetime.now(timezone.utc)
        conn = db.get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO temp_registrations (email, password_hash, first_name, last_name, phone, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    phone = EXCLUDED.phone,
                    created_at = EXCLUDED.created_at
            """, (request.email, hashed_password, request.first_name,
                  request.last_name, request.phone, now))
            conn.commit()
        conn.close()
        
        # Send verification email
        await send_verification_email(request.email, verification_code, purpose="verification")
        
        return RegisterResponse(
            success=True,
            message="Email adresinize doğrulama kodu gönderildi. Hesabınızı aktifleştirmek için kodu giriniz."
        )
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return RegisterResponse(
            success=False,
            message="Kayıt sırasında bir hata oluştu."
        )

@router.post("/verify-email", response_model=RegisterResponse)
async def verify_email(request: VerifyEmailRequest):
    """Verify email and activate user account"""
    db = Database()
    
    try:
        # Check verification code
        conn = db.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT verification_code FROM email_verifications 
                WHERE email = %s AND expires_at > NOW()
            """, (request.email,))
            result = cursor.fetchone()
        
        if not result or result['verification_code'] != request.verification_code:
            conn.close()
            return RegisterResponse(
                success=False,
                message="Geçersiz veya süresi dolmuş doğrulama kodu."
            )
        
        # Get temporary registration data
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM temp_registrations WHERE email = %s", (request.email,))
            temp_data = cursor.fetchone()
        
        if not temp_data:
            conn.close()
            return RegisterResponse(
                success=False,
                message="Kayıt verileri bulunamadı. Lütfen tekrar kayıt olun."
            )
        
        # Create actual user account (let PostgreSQL generate UUID)
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (email, password_hash, first_name, last_name, phone, 
                                 is_active, is_email_verified, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (request.email, temp_data['password_hash'],
                  temp_data['first_name'], temp_data['last_name'], temp_data['phone'],
                  True, True, temp_data['created_at']))
            
            # Clean up temporary data
            cursor.execute("DELETE FROM email_verifications WHERE email = %s", (request.email,))
            cursor.execute("DELETE FROM temp_registrations WHERE email = %s", (request.email,))
            conn.commit()
        conn.close()
        
        return RegisterResponse(
            success=True,
            message="Hesabınız başarıyla oluşturuldu! Şimdi giriş yapabilirsiniz."
        )
        
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        return RegisterResponse(
            success=False,
            message="Doğrulama sırasında bir hata oluştu."
        )

@router.post("/resend-verification", response_model=RegisterResponse)
async def resend_verification_code(request: VerificationCodeRequest):
    """Resend verification code"""
    db = Database()
    
    try:
        # Check if there's a pending registration
        conn = db.get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT email FROM temp_registrations WHERE email = %s", (request.email,))
            result = cursor.fetchone()
        
        if not result:
            conn.close()
            return RegisterResponse(
                success=False,
                message="Bu email için bekleyen bir kayıt bulunamadı."
            )
        
        # Simple throttle: limit 1 resend per 60 seconds
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT created_at FROM email_verifications WHERE email = %s",
                (request.email,),
            )
            prev = cursor.fetchone()
        if prev and prev.get('created_at') and (datetime.now(timezone.utc) - prev['created_at']).total_seconds() < 60:
            conn.close()
            return RegisterResponse(success=False, message="Çok sık istek yapıldı. Lütfen 1 dakika sonra tekrar deneyin.")

        # Generate new verification code
        verification_code = generate_verification_code()
        expire_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        # Update verification code
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE email_verifications 
                SET verification_code = %s, expires_at = %s, created_at = NOW()
                WHERE email = %s
            """, (verification_code, expire_time, request.email))
            conn.commit()
        conn.close()
        
        # Send verification email
        await send_verification_email(request.email, verification_code, purpose="verification")
        
        return RegisterResponse(
            success=True,
            message="Yeni doğrulama kodu email adresinize gönderildi."
        )
        
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        return RegisterResponse(
            success=False,
            message="Doğrulama kodu gönderilirken bir hata oluştu."
        )

@router.post("/login", response_model=UserSessionResponse)
async def login_user(request: LoginRequest):
    """User login"""
    db = Database()
    
    try:
        # Get user data
        conn = db.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, email, password_hash, first_name, last_name, phone, telegram_id,
                       is_active, is_email_verified, created_at
                FROM users WHERE email = %s AND is_active = true
            """, (request.email,))
            result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "AUTH_INVALID", "message": "Geçersiz email veya şifre"}
            )
        
        user = result
        
        # Verify password
        if not verify_password(request.password, user['password_hash']):
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "AUTH_INVALID", "message": "Geçersiz email veya şifre"}
            )
        
        # Generate JWT token
        token = generate_jwt_token(user['id'])
        expires_at = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
        
        # Update last login and create session record
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET last_login = %s WHERE id = %s",
                (datetime.now(timezone.utc), user['id'])
            )
            
            cursor.execute("""
                INSERT INTO user_sessions (user_id, session_token, expires_at)
                VALUES (%s, %s, %s)
            """, (user['id'], token, expires_at))
            conn.commit()
        conn.close()
        
        return UserSessionResponse(
            session_token=token,
            user=UserResponse(
                id=user['id'],
                email=user['email'],
                first_name=user['first_name'],
                last_name=user['last_name'],
                phone=user['phone'],
                telegram_id=user['telegram_id'],
                is_active=user['is_active'],
                is_email_verified=user['is_email_verified'],
                last_login=datetime.now(timezone.utc).isoformat(),
                created_at=user['created_at'].isoformat()
            ),
            expires_at=expires_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Giriş sırasında bir hata oluştu"
        )

@router.post("/logout")
async def logout_user(user_id: str = Depends(get_current_user)):
    """User logout"""
    db = Database()
    
    try:
        # Invalidate session
        conn = db.get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_sessions WHERE user_id = %s",
                (user_id,)
            )
            conn.commit()
        conn.close()
        
        return {"message": "Başarıyla çıkış yapıldı"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Çıkış sırasında bir hata oluştu"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user_id: str = Depends(get_current_user)):
    """Get current user information"""
    db = Database()
    
    try:
        conn = db.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, email, first_name, last_name, phone, telegram_id,
                       is_active, is_email_verified, last_login, created_at
                FROM users WHERE id = %s AND is_active = true
            """, (user_id,))
            result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kullanıcı bulunamadı"
            )
        
        user = result
        
        return UserResponse(
            id=user['id'],
            email=user['email'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            phone=user['phone'],
            telegram_id=user['telegram_id'],
            is_active=user['is_active'],
            is_email_verified=user['is_email_verified'],
            last_login=user['last_login'].isoformat() if user['last_login'] else None,
            created_at=user['created_at'].isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kullanıcı bilgileri alınırken bir hata oluştu"
        )

@router.put("/me")
async def update_current_user_info(req: UpdateProfileRequest, user_id: str = Depends(get_current_user)):
    """Update current user information"""
    db = Database()
    try:
        fields = []
        values = []
        if req.first_name is not None:
            fields.append('first_name = %s')
            values.append(req.first_name)
        if req.last_name is not None:
            fields.append('last_name = %s')
            values.append(req.last_name)
        if req.phone is not None:
            fields.append('phone = %s')
            values.append(req.phone)
        if req.telegram_id is not None:
            fields.append('telegram_id = %s')
            values.append(req.telegram_id)
        if not fields:
            return {"success": True, "message": "Güncellenecek alan yok"}
        values.append(user_id)
        set_clause = ', '.join(fields)
        conn = db.get_connection()
        with conn.cursor() as cursor:
            cursor.execute(f"UPDATE users SET {set_clause} WHERE id = %s", tuple(values))
            conn.commit()
        conn.close()
        return {"success": True, "message": "Profil güncellendi"}
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(status_code=500, detail="Profil güncellenemedi")

@router.post("/request-password-reset")
async def request_password_reset(req: PasswordResetRequest):
    """Initiate password reset by verifying email+phone and issuing a verification code"""
    db = Database()
    try:
        email_value = req.email.strip()
        if not email_value:
            raise HTTPException(status_code=400, detail="Email gerekli")
        conn = db.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, is_active FROM users WHERE lower(email) = lower(%s)", (email_value,))
            user = cursor.fetchone()
        if not user:
            conn.close()
            if AUTH_TEST_MODE:
                logger.info(f"Password reset request: user not found for email={email_value}")
            return {"success": False, "message": "Kullanıcı bulunamadı"}
        if not user.get('is_active'):
            conn.close()
            if AUTH_TEST_MODE:
                logger.info(f"Password reset request: user inactive for email={email_value}")
            return {"success": False, "message": "Hesap aktif değil. Lütfen email doğrulamasını tamamlayın."}
        # Simple throttle: limit 1 request per 60 seconds
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT created_at FROM email_verifications WHERE email = %s",
                (email_value,),
            )
            prev = cursor.fetchone()
        if prev and prev.get('created_at') and (datetime.now(timezone.utc) - prev['created_at']).total_seconds() < 60:
            conn.close()
            return {"success": False, "message": "Çok sık istek yapıldı. Lütfen 1 dakika sonra tekrar deneyin."}
        code = generate_verification_code()
        expire_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO email_verifications (email, verification_code, expires_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    verification_code = EXCLUDED.verification_code,
                    expires_at = EXCLUDED.expires_at,
                    created_at = NOW()
                """,
                (email_value, code, expire_time),
            )
            conn.commit()
        conn.close()
        # Send reset email (uses SMTP outside test mode)
        await send_verification_email(email_value, code, purpose="password_reset")
        return {"success": True, "message": "Doğrulama kodu gönderildi"}
    except Exception as e:
        logger.error(f"Request password reset error: {e}")
        raise HTTPException(status_code=500, detail="İşlem başarısız")

@router.post("/verify-password-reset")
async def verify_password_reset(req: PasswordResetVerifyRequest):
    # In test mode, accept the default code
    if AUTH_TEST_MODE and req.verification_code == "111111":
        logger.info(f"Test mode: Accepting default verification code for {req.email}")
        return {"success": True, "message": "Doğrulandı"}
    
    db = Database()
    try:
        conn = db.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT verification_code FROM email_verifications WHERE email = %s AND expires_at > NOW()",
                (req.email,),
            )
            row = cursor.fetchone()
        conn.close()
        if not row or row['verification_code'] != req.verification_code:
            return {"success": False, "message": "Geçersiz doğrulama kodu"}
        return {"success": True, "message": "Doğrulandı"}
    except Exception as e:
        logger.error(f"Verify password reset error: {e}")
        raise HTTPException(status_code=500, detail="İşlem başarısız")

@router.post("/reset-password")
async def reset_password(req: PasswordResetFinalizeRequest):
    db = Database()
    try:
        # Validate new password
        pw_err = validate_password_strength(req.new_password)
        if pw_err:
            return {"success": False, "message": pw_err}
        # Hash new password
        hashed = hash_password(req.new_password)
        conn = db.get_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s AND is_active = true", (hashed, req.email))
            cursor.execute("DELETE FROM email_verifications WHERE email = %s", (req.email,))
            conn.commit()
        conn.close()
        return {"success": True, "message": "Şifre güncellendi"}
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        raise HTTPException(status_code=500, detail="Şifre güncellenemedi")
