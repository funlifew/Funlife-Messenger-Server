from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid
# Create your models here.

User = get_user_model()

class Session(models.Model):
    """User's Session Model"""
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    token = models.TextField(null=True, blank=True)
    device_info = models.TextField(null=True, blank=True)
    ip_address = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    