from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from utils.email_service import EmailService
import uuid, json
# Create your models here.

User = get_user_model()

class UserSession(models.Model):
    """User's Session Model"""
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    token = models.TextField(null=True, blank=True)
    device_info = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(null=True, blank=True, db_index=True)
    
    class Meta:
        ordering = ['-last_activity']
        indexes = [
            # Composite index for user and active status (common query pattern)
            models.Index(fields=['user', 'is_active'], name='user_active_idx'),
            # Composite index for checking expired sessions
            models.Index(fields=['is_active', 'expires_at'], name='active_expires_idx'),
        ]
    
    def __str__(self):
        return f"Session for {self.user.username} on {self.device_name}"
    
    def save(self, *args, **kwargs):
        """Override save to set expiration time if not already set"""
        if not self.expires_at:
            # Default session expiration: 30 days
            self.expires_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)
    
    
    @property
    def is_expired(self):
        """Check if the session has expired"""
        return self.expires_at and timezone.now() > self.expires_at
    
    @property
    def device_name(self):
        """Get a user-friendly device name from device_info"""
        if not self.device_info:
            return "Unknown Device"
        
        try:
            info = json.loads(self.device_info)
            return info.get('name', info.get('browser', 'Unknown Device'))
        except (json.JSONDecodeError, AttributeError):
            return "Unknown Device"
    
    # Methods
    
    def send_login_notification(self):
        """Send login notification email to the user"""
        try:
            EmailService.send_login_notification(self.user, self)
        except Exception as e:
            # Log error but continue
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send login notification: {str(e)}")
    
    def store_device_info(self, user_agent=None, ip=None, **extra_data):
        """Store structured device info as JSON"""
        device_data = extra_data or {}
        
        if user_agent:
            device_data.update({
                'user_agent': str(user_agent),
                'browser': self._parse_browser(user_agent),
                'os': self._parse_os(user_agent)
            })
        
        if ip:
            self.ip_address = ip
        
        self.device_info = json.dumps(device_data)
        self.save(update_fields=['device_info', 'ip_address'])
        
        # Send login notification
        self.send_login_notification()
    
    def notify_session_created(self):
        """Send notification email for new session creation"""
        if self.user and self.user.email:
            EmailService.send_login_notification(self.user, self)
    
    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    def extend_session(self, days=30):
        """Extend the session expiration"""
        self.expires_at = timezone.now() + timedelta(days=days)
        self.save(update_fields=['expires_at'])
    
    def invalidate(self):
        """Invalidate this session"""
        self.is_active = False
        self.save(update_fields=['is_active'])
    
    def store_device_info(self, user_agent=None, ip=None, **extra_data):
        """Store structured device info as JSON"""
        device_data = extra_data or {}
        
        if user_agent:
            device_data.update({
                'user_agent': str(user_agent),
                'browser': self._parse_browser(user_agent),
                'os': self._parse_os(user_agent)
            })
        
        if ip:
            self.ip_address = ip
        
        self.device_info = json.dumps(device_data)
        self.save(update_fields=['device_info', 'ip_address'])
    
    # Helper methods
    def _parse_browser(self, user_agent):
        """Extract browser info from user agent string"""
        # Simple browser detection - could be expanded
        user_agent = user_agent.lower()
        if 'firefox' in user_agent:
            return 'Firefox'
        elif 'chrome' in user_agent:
            return 'Chrome'
        elif 'safari' in user_agent:
            return 'Safari'
        elif 'edge' in user_agent:
            return 'Edge'
        elif 'opera' in user_agent or 'opr' in user_agent:
            return 'Opera'
        return 'Unknown Browser'
    
    def _parse_os(self, user_agent):
        """Extract OS info from user agent string"""
        # Simple OS detection - could be expanded
        user_agent = user_agent.lower()
        if 'windows' in user_agent:
            return 'Windows'
        elif 'mac os' in user_agent or 'macos' in user_agent:
            return 'macOS'
        elif 'linux' in user_agent:
            return 'Linux'
        elif 'android' in user_agent:
            return 'Android'
        elif 'ios' in user_agent or 'iphone' in user_agent or 'ipad' in user_agent:
            return 'iOS'
        return 'Unknown OS'

    @classmethod
    def get_active_sessions(cls, user):
        """Get all active sessions for a user"""
        now = timezone.now()
        return cls.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=now
        )
    
    @classmethod
    def invalidate_all_sessions(cls, user, exclude_id=None):
        """Invalidate all user sessions, optionally excluding one"""
        sessions = cls.objects.filter(user=user, is_active=True)
        if exclude_id:
            sessions = sessions.exclude(id=exclude_id)
        sessions.update(is_active=False)
    