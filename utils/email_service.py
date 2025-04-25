"""Email utility functions for the application."""
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending various types of emails in the application."""
    
    @staticmethod
    def send_email(subject, to_email, template_name, context=None, from_email=None):
        """
        Send an email using a template.
        
        Args:
            subject: Email subject
            to_email: Recipient email address or list of addresses
            template_name: Template path without extension (both .html and .txt will be used)
            context: Dictionary with context for the template
            from_email: Sender email (defaults to settings.DEFAULT_FROM_EMAIL)
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if context is None:
            context = {}
            
        # Add application name to all templates
        context['app_name'] = 'FunLife Messenger'
        
        # Default sender
        if from_email is None:
            from_email = settings.DEFAULT_FROM_EMAIL
            
        try:
            # Render HTML content
            html_content = render_to_string(f'{template_name}.html', context)
            # Create plain text content from HTML
            text_content = strip_tags(html_content)
            
            # Create message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[to_email] if isinstance(to_email, str) else to_email
            )
            
            # Attach HTML content
            msg.attach_alternative(html_content, "text/html")
            
            # Send email
            result = msg.send()
            
            if result:
                logger.info(f"Email '{subject}' sent to {to_email}")
                return True
            else:
                logger.warning(f"Failed to send email '{subject}' to {to_email}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email '{subject}' to {to_email}: {str(e)}")
            return False
    
    @classmethod
    def send_verification_email(cls, user, otp, verification_url=None):
        """
        Send verification email with OTP code.
        
        Args:
            user: User object
            otp: OTP object with verification code
            verification_url: Optional URL for verification
            
        Returns:
            bool: True if email was sent successfully
        """
        subject = "Verify Your FunLife Messenger Account"
        
        context = {
            'user': user,
            'otp_code': otp.code,
            'expires_at': otp.expires_at,
            'verification_url': verification_url
        }
        
        return cls.send_email(
            subject=subject,
            to_email=user.email,
            template_name='emails/verification',
            context=context
        )
    
    @classmethod
    def send_password_reset_email(cls, user, otp, reset_url=None):
        """
        Send password reset email with OTP code.
        
        Args:
            user: User object
            otp: OTP object with reset code
            reset_url: Optional URL for password reset
            
        Returns:
            bool: True if email was sent successfully
        """
        subject = "Reset Your FunLife Messenger Password"
        
        context = {
            'user': user,
            'otp_code': otp.code,
            'expires_at': otp.expires_at,
            'reset_url': reset_url
        }
        
        return cls.send_email(
            subject=subject,
            to_email=user.email,
            template_name='emails/password_reset',
            context=context
        )
    
    @classmethod
    def send_login_notification(cls, user, session):
        """
        Send login notification email.
        
        Args:
            user: User object
            session: UserSession object
            
        Returns:
            bool: True if email was sent successfully
        """
        subject = "New Login to Your FunLife Messenger Account"
        
        context = {
            'user': user,
            'session': session,
            'device_name': session.device_name,
            'ip_address': session.ip_address,
            'timestamp': session.created_at
        }
        
        return cls.send_email(
            subject=subject,
            to_email=user.email,
            template_name='emails/login_notification',
            context=context
        )
    
    @classmethod
    def send_security_alert(cls, user, event_type, details=None):
        """
        Send security alert email.
        
        Args:
            user: User object
            event_type: Security event type
            details: Additional details
            
        Returns:
            bool: True if email was sent successfully
        """
        subject = f"Security Alert: {event_type}"
        
        context = {
            'user': user,
            'event_type': event_type,
            'details': details,
            'timestamp': details.get('timestamp') if details else None
        }
        
        return cls.send_email(
            subject=subject,
            to_email=user.email,
            template_name='emails/security_alert',
            context=context
        )

    @classmethod
    def send_login_notification(cls, user, session):
        """
        Send login notification email.
        
        Args:
            user: User object
            session: UserSession object
            
        Returns:
            bool: True if email was sent successfully
        """
        subject = "New Login to Your FunLife Messenger Account"
        
        context = {
            'user': user,
            'session': session,
            'device_name': session.device_name,
            'ip_address': session.ip_address,
            'timestamp': session.created_at
        }
        
        return cls.send_email(
            subject=subject,
            to_email=user.email,
            template_name='emails/login_notification',
            context=context
        )

    @classmethod
    def send_security_alert(cls, user, event_type, details=None):
        """
        Send security alert email.
        
        Args:
            user: User object
            event_type: Security event type
            details: Additional details
            
        Returns:
            bool: True if email was sent successfully
        """
        subject = f"Security Alert: {event_type}"
        
        context = {
            'user': user,
            'event_type': event_type,
            'details': details,
            'timestamp': details.get('timestamp') if details else None
        }
        
        return cls.send_email(
            subject=subject,
            to_email=user.email,
            template_name='emails/security_alert',
            context=context
        )

    @classmethod
    def send_2fa_enabled_notification(cls, user):
        """
        Send notification when 2FA is enabled.
        
        Args:
            user: User object
            
        Returns:
            bool: True if email was sent successfully
        """
        subject = "Two-Factor Authentication Enabled"
        
        context = {
            'user': user,
            'timestamp': datetime.now().isoformat()
        }
        
        return cls.send_email(
            subject=subject,
            to_email=user.email,
            template_name='emails/2fa_enabled',
            context=context
        )