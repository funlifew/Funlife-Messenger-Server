from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Backup
from security_logs.models import SecurityLog, EventType, SeverityLevel

@receiver(post_save, sender=Backup)
def backup_created(sender, instance, created, **kwargs):
    """Signal handler for backup creation"""
    if created:
        # Log the creation to security logs
        SecurityLog.log_event(
            event_type=EventType.BACKUP_CREATE,
            user=instance.user,
            ip_address=None,  # Will be filled by middleware if available
            severity=SeverityLevel.INFO,
            details={
                'backup_id': str(instance.id),
                'size': instance.size,
                'session_id': str(instance.session.id) if instance.session else None
            }
        )

@receiver(post_delete, sender=Backup)
def backup_deleted(sender, instance, **kwargs):
    """Signal handler for backup deletion"""
    # Log the deletion to security logs
    SecurityLog.log_event(
        event_type=EventType.BACKUP_DELETE,
        user=instance.user,
        ip_address=None,  # Will be filled by middleware if available
        severity=SeverityLevel.INFO,
        details={
            'backup_id': str(instance.id),
            'reason': 'manual_deletion'
        }
    )