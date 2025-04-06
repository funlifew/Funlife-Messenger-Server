from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core import signals
import uuid

# Create your models here.
User = get_user_model()

class Profile(models.Model):
    """User Profile Model"""
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    status = models.CharField(max_length=100, null=True, blank=True)
    display_name = models.CharField(max_length=60, null=True, blank=True)
    bio = models.TextField(default="Hello, I'm really into funlife messenger :)")
    is_online = models.BooleanField(default=False)
    
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    