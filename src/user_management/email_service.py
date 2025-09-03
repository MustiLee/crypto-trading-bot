"""
Email service for user registration verification and notifications
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from loguru import logger
import aiosmtplib
from jinja2 import Environment, FileSystemLoader


class EmailService:
    """Service for sending emails to users"""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        self.from_name = os.getenv('FROM_NAME', 'Crypto Trading Bot')
        self.base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        
        # Setup Jinja2 for email templates
        template_dir = os.path.join(os.path.dirname(__file__), 'email_templates')
        os.makedirs(template_dir, exist_ok=True)
        self.template_env = Environment(loader=FileSystemLoader(template_dir))
        
        # Create default templates if they don't exist
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default email templates"""
        template_dir = os.path.join(os.path.dirname(__file__), 'email_templates')
        
        # Email verification template
        verification_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Email Verification - Crypto Trading Bot</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .button { display: inline-block; padding: 12px 25px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { padding: 20px; text-align: center; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to Crypto Trading Bot</h1>
        </div>
        <div class="content">
            <h2>Hi {{ first_name }},</h2>
            <p>Thank you for registering with our cryptocurrency trading bot platform!</p>
            <p>To complete your registration and activate your account, please click the button below to verify your email address:</p>
            <p style="text-align: center;">
                <a href="{{ verification_url }}" class="button">Verify Email Address</a>
            </p>
            <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
            <p style="word-break: break-all;"><a href="{{ verification_url }}">{{ verification_url }}</a></p>
            <p><strong>This verification link will expire in 24 hours.</strong></p>
            <p>If you didn't create an account with us, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>The Crypto Trading Bot Team</p>
        </div>
    </div>
</body>
</html>'''
        
        verification_path = os.path.join(template_dir, 'email_verification.html')
        if not os.path.exists(verification_path):
            with open(verification_path, 'w', encoding='utf-8') as f:
                f.write(verification_template)
        
        # Password reset template
        reset_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Password Reset - Crypto Trading Bot</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #e74c3c; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .button { display: inline-block; padding: 12px 25px; background: #e74c3c; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { padding: 20px; text-align: center; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <h2>Hi {{ first_name }},</h2>
            <p>We received a request to reset your password for your Crypto Trading Bot account.</p>
            <p>Click the button below to reset your password:</p>
            <p style="text-align: center;">
                <a href="{{ reset_url }}" class="button">Reset Password</a>
            </p>
            <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
            <p style="word-break: break-all;"><a href="{{ reset_url }}">{{ reset_url }}</a></p>
            <p><strong>This reset link will expire in 1 hour.</strong></p>
            <p>If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>The Crypto Trading Bot Team</p>
        </div>
    </div>
</body>
</html>'''
        
        reset_path = os.path.join(template_dir, 'password_reset.html')
        if not os.path.exists(reset_path):
            with open(reset_path, 'w', encoding='utf-8') as f:
                f.write(reset_template)
        
        # Trading signal notification template
        signal_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Trading Signal Alert - Crypto Trading Bot</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #27ae60; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .signal-box { background: white; border-left: 4px solid #27ae60; padding: 15px; margin: 15px 0; }
        .buy-signal { border-left-color: #27ae60; }
        .sell-signal { border-left-color: #e74c3c; }
        .footer { padding: 20px; text-align: center; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Trading Signal Alert</h1>
        </div>
        <div class="content">
            <h2>Hi {{ first_name }},</h2>
            <p>A new trading signal has been generated for your monitored cryptocurrencies:</p>
            <div class="signal-box {{ signal_type.lower() }}-signal">
                <h3>{{ signal_type }} Signal for {{ symbol }}</h3>
                <p><strong>Price:</strong> ${{ price }}</p>
                <p><strong>Strategy:</strong> {{ strategy }}</p>
                <p><strong>Timestamp:</strong> {{ timestamp }}</p>
                {% if rsi %}<p><strong>RSI:</strong> {{ rsi }}</p>{% endif %}
                {% if macd %}<p><strong>MACD:</strong> {{ macd }}</p>{% endif %}
            </div>
            <p><em>This is an automated notification. Please conduct your own analysis before making trading decisions.</em></p>
        </div>
        <div class="footer">
            <p>Happy Trading!<br>The Crypto Trading Bot Team</p>
        </div>
    </div>
</body>
</html>'''
        
        signal_path = os.path.join(template_dir, 'trading_signal.html')
        if not os.path.exists(signal_path):
            with open(signal_path, 'w', encoding='utf-8') as f:
                f.write(signal_template)
    
    def _get_smtp_connection(self):
        """Get SMTP connection"""
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured")
            return None
        
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            return server
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {e}")
            return None
    
    async def _send_email_async(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email asynchronously"""
        try:
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = to_email
            
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)
            
            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                start_tls=True,
                username=self.smtp_username,
                password=self.smtp_password,
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email synchronously"""
        try:
            smtp_server = self._get_smtp_connection()
            if not smtp_server:
                return False
            
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = to_email
            
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)
            
            smtp_server.send_message(message)
            smtp_server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_verification_email(self, email: str, first_name: str, token: str) -> bool:
        """
        Send email verification email
        
        Args:
            email: User email address
            first_name: User first name
            token: Verification token
            
        Returns:
            True if email sent successfully
        """
        try:
            verification_url = f"{self.base_url}/verify-email?token={token}"
            
            template = self.template_env.get_template('email_verification.html')
            html_content = template.render(
                first_name=first_name,
                verification_url=verification_url
            )
            # Append plain code for manual entry
            html_content += f"<p><strong>Doğrulama Kodunuz:</strong> {token}</p><p>Bu kod 24 saat içinde geçerlidir.</p>"
            
            subject = "Verify Your Email Address - Crypto Trading Bot"
            return self.send_email(email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Error sending verification email: {e}")
            return False
    
    def send_password_reset_email(self, email: str, first_name: str, token: str) -> bool:
        """
        Send password reset email
        
        Args:
            email: User email address
            first_name: User first name
            token: Reset token
            
        Returns:
            True if email sent successfully
        """
        try:
            reset_url = f"{self.base_url}/reset-password?token={token}"
            
            template = self.template_env.get_template('password_reset.html')
            html_content = template.render(
                first_name=first_name,
                reset_url=reset_url
            )
            
            subject = "Password Reset Request - Crypto Trading Bot"
            return self.send_email(email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            return False
    
    def send_trading_signal_email(self, email: str, first_name: str, signal_data: dict) -> bool:
        """
        Send trading signal notification email
        
        Args:
            email: User email address
            first_name: User first name
            signal_data: Dictionary containing signal information
            
        Returns:
            True if email sent successfully
        """
        try:
            template = self.template_env.get_template('trading_signal.html')
            html_content = template.render(
                first_name=first_name,
                **signal_data
            )
            
            signal_type = signal_data.get('signal_type', 'Trading')
            symbol = signal_data.get('symbol', 'Crypto')
            subject = f"{signal_type} Signal Alert for {symbol} - Crypto Trading Bot"
            
            return self.send_email(email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Error sending trading signal email: {e}")
            return False
    
    def test_email_connection(self) -> bool:
        """Test email connection and configuration"""
        try:
            smtp_server = self._get_smtp_connection()
            if smtp_server:
                smtp_server.quit()
                logger.info("Email connection test successful")
                return True
            else:
                logger.error("Email connection test failed")
                return False
                
        except Exception as e:
            logger.error(f"Email connection test error: {e}")
            return False
