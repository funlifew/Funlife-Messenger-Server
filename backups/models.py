from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

class Backup(models.Model):
    """Model for storing encrypted user backups"""
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='backups',
        db_index=True
    )
    session = models.ForeignKey(
        'user_sessions.UserSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='backups'
    )
    encrypted_data = models.TextField()
    checksum = models.CharField(max_length=128)
    size = models.PositiveIntegerField(help_text="Size in bytes")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at'], name='user_backup_date_idx'),
        ]
    
    def __str__(self):
        return f"Backup for {self.user.username} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"