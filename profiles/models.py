from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
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
    
    def __str__(self):
        return f"Profile of {self.user.username} - {self.is_online}"
    
    def updated_online_status(self, is_online=True):
        """Update user's online status and last seen time"""
        self.is_online = is_online
        if not is_online:
            self.last_seen = timezone.now()
        
        self.save(update_fields=['is_online', 'last_seen'])
    
    def get_offline_duration(self):
        """Return how long the user is offline"""
        if self.is_online or not self.last_seen:
            return None
        
        now = timezone.now()
        duration = now - self.last_seen
        return duration
    
    @property
    def offline_duration_display(self):
        """Return human-readable offline duration"""
        duration = self.get_offline_duration()
        if not duration:
            return "Online" if self.is_online else "Unknown"
        
        seconds = duration.total_seconds()
        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            days = int(seconds // 86400)
            return f"{days} day{'s' if days > 1 else ''} ago"

@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    """Create or update user profile when User is created or updated"""
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)