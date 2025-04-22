from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid


User = get_user_model()

class SeverityType(models.TextChoices):
    """This is an class for types of security logs"""
    INFO=0
    WARNING=1
    ERROR=2
    CRITICAL=3

class EventType(models.TextChoices):
    """This is an class types for event of sec logs"""
    LOGIN = "login"
    LOGOUT = "logout"
    RESET_PASSWORD = "reset_password"
    REGISTRATION = 'registration'
    FAILED_LOGIN = 'failed_login'
    PROFILE_CHANGE = 'profile_change'
    FRIEND_REQUEST_SENT = 'friend_request_sent'
    FRIEND_REQUEST_ACCEPT = 'friend_request_accept'
    FRIEND_REQUEST_REJECT = 'friend_request_reject'


# Create your models here.
class SecurityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    user = models.ForeignKey(User, related_name='security_logs', on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    event_type = models.CharField(max_length=100, choices=EventType, db_index=True)
    ip_address = models.GenericIPAddressField(db_index=True)
    device_info = models.TextField(db_index=True)
    severity = models.ChardField(db_index=True, choices=SeverityType, max_length=40)
    details = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)