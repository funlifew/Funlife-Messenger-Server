from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid, json


User = get_user_model()

class SeverityLevel(models.IntegerChoices):
    """Severity levels for security events"""
    INFO = 0, "Information"
    WARNING = 1, "Warning"
    ERROR = 2, "Error"
    CRITICAL = 3, "Critical"

class EventType(models.TextChoices):
    """Types of security events to log"""
    # Authentication events
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    FAILED_LOGIN = "failed_login", "Failed Login"
    
    # Account events
    REGISTRATION = "registration", "Registration"
    ACCOUNT_LOCK = "account_lock", "Account Locked"
    ACCOUNT_UNLOCK = "account_unlock", "Account Unlocked"
    EMAIL_CHANGE = "email_change", "Email Changed"
    EMAIL_VERIFICATION = "email_verification", "Email Verified"
    
    # Password events
    PASSWORD_CHANGE = "password_change", "Password Changed"
    PASSWORD_RESET_REQUEST = "password_reset_request", "Password Reset Requested"
    PASSWORD_RESET = "password_reset", "Password Reset"
    
    # Two-factor events
    TWO_FACTOR_ENABLE = "2fa_enable", "Two-Factor Enabled"
    TWO_FACTOR_DISABLE = "2fa_disable", "Two-Factor Disabled"
    TWO_FACTOR_SUCCESS = "2fa_success", "Two-Factor Success"
    TWO_FACTOR_FAILURE = "2fa_failure", "Two-Factor Failure"
    
    # Profile events
    PROFILE_UPDATE = "profile_update", "Profile Updated"
    KEY_GENERATION = "key_generation", "Key Pair Generated"
    
    # Session events
    SESSION_CREATE = "session_create", "Session Created"
    SESSION_EXPIRE = "session_expire", "Session Expired"
    SESSION_INVALIDATE = "session_invalidate", "Session Invalidated"
    ALL_SESSIONS_INVALIDATE = "all_sessions_invalidate", "All Sessions Invalidated"
    
    # Friend events
    FRIEND_REQUEST_SENT = "friend_request_sent", "Friend Request Sent"
    FRIEND_REQUEST_ACCEPT = "friend_request_accept", "Friend Request Accepted"
    FRIEND_REQUEST_REJECT = "friend_request_reject", "Friend Request Rejected"
    FRIEND_BLOCK = "friend_block", "User Blocked"
    FRIEND_UNBLOCK = "friend_unblock", "User Unblocked"
    
    # Message events
    MESSAGE_SEND = "message_send", "Message Sent"
    MESSAGE_DELETE = "message_delete", "Message Deleted"
    
    # Other events
    API_ACCESS = "api_access", "API Endpoint Access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded", "Rate Limit Exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity", "Suspicious Activity"
    ADMIN_ACTION = "admin_action", "Administrative Action"


class SecurityLog(models.Model):
    """Model for storing security-related events"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    user = models.ForeignKey(
        User, 
        related_name='security_logs', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        db_index=True
    )
    event_type = models.CharField(
        max_length=100, 
        choices=EventType.choices, 
        db_index=True
    )
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True, 
        db_index=True
    )
    device_info = models.TextField(
        null=True, 
        blank=True
    )
    severity = models.IntegerField(
        choices=SeverityLevel.choices,
        default=SeverityLevel.INFO, 
        db_index=True
    )
    details = models.JSONField(
        null=True, 
        blank=True, 
        help_text="Additional details about the event in JSON format"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'event_type'], name='user_event_idx'),
            models.Index(fields=['severity', 'created_at'], name='severity_time_idx'),
        ]
    
    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        return f"{self.event_type} - {username} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

    @staticmethod
    def log_event(event_type, user=None, ip_address=None, device_info=None, severity=SeverityLevel.INFO, details=None):
        """
        Create a new security log entry
        
        Args:
            event_type: Type of event from EventType choices
            user: User associated with the event (optional)
            ip_address: IP address of the client (optional)
            device_info: Client device information (optional)
            severity: Severity level from SeverityLevel choices
            details: Additional details as dict (will be stored as JSON)
            
        Returns:
            The created SecurityLog instance
        """
        
        # Convert device_info to string if it's a dict
        if device_info and isinstance(device_info, dict):
            device_info = json.dumps(device_info)
        
        return SecurityLog.objects.create(
            event_type=event_type,
            user=user,
            ip_address=ip_address,
            device_info=device_info,
            severity=severity,
            details=details
        )
    
    @classmethod
    def get_user_logs(cls, user, limit=100):
        """Get recent security logs for a specific user"""
        return cls.objects.filter(user=user).order_by('-created_at')[:limit]
    
    @classmethod
    def get_logs_by_event(cls, event_type, limit=100):
        """Get recent security logs of a specific event type"""
        return cls.objects.filter(event_type=event_type).order_by('-created_at')[:limit]

    @classmethod
    def get_logs_by_severity(cls, severity_level, limit=100):
        """Get recent security logs of a specific severity level"""
        return cls.objects.filter(severity=severity_level).order_by('-created_at')[:limit]
    
    @classmethod
    def get_logs_by_ip(cls, ip_address, limit=100):
        """Get recent security logs from a specific IP address"""
        return cls.objects.filter(ip_address=ip_address).order_by('-created_at')[:limit]
    
    @classmethod
    def get_suspicious_logs(cls, limit=100):
        """Get recent security logs with suspicious activity"""
        return cls.objects.filter(
            severity__in=[SeverityLevel.WARNING, SeverityLevel.ERROR, SeverityLevel.CRITICAL]
        ).order_by('-created_at')[:limit]
    
    @classmethod
    def get_recent_logs(cls, days=7, limit=100):
        """Get recent security logs from the last X days"""
        start_date = timezone.now() - timezone.timedelta(days=days)
        return cls.objects.filter(created_at__gte=start_date).order_by('-created_at')[:limit]