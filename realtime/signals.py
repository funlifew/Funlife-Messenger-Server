from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

from profiles.models import Profile
from friendships.models import Friendship, FriendshipStatus
from messagings.models import Message
from security_logs.models import SecurityLog, SeverityLevel
from user_sessions.models import UserSession
from backups.models import Backup

channel_layer = get_channel_layer()

# Profile signals
@receiver(post_save, sender=Profile)
def profile_updated(sender, instance, created, **kwargs):
    """Broadcast profile updates to friends"""
    if not created:  # Only for updates, not new profiles
        try:
            from friendships.models import Friendship
            
            # Get user's friends
            friends = Friendship.get_user_friends(instance.user)
            
            # Create update event
            event = {
                'type': 'profile_update',
                'user_id': str(instance.user.id),
                'username': instance.user.username,
                'display_name': instance.display_name,
                'status': instance.status,
                'is_online': instance.is_online,
                'timestamp': timezone.now().isoformat()
            }
            
            # Send to each friend
            for friend in friends:
                async_to_sync(channel_layer.group_send)(
                    f'user_{friend.id}',
                    event
                )
        except Exception:
            pass

# Friendship signals
@receiver(post_save, sender=Friendship)
def friendship_updated(sender, instance, created, **kwargs):
    """Broadcast friendship updates"""
    try:
        event_type = 'friend_request' if created else 'friendship_update'
        
        # Create event data
        event = {
            'type': event_type,
            'friendship_id': str(instance.id),
            'user_id': str(instance.user.id),
            'username': instance.user.username,
            'friend_id': str(instance.friend.id),
            'friend_username': instance.friend.username,
            'status': instance.status,
            'timestamp': timezone.now().isoformat()
        }
        
        # Send to recipient
        async_to_sync(channel_layer.group_send)(
            f'user_{instance.friend.id}',
            event
        )
    except Exception:
        pass

# Security Log signals
@receiver(post_save, sender=SecurityLog)
def security_log_created(sender, instance, created, **kwargs):
    """Broadcast security events"""
    if created and instance.user and instance.severity >= SeverityLevel.WARNING:
        try:
            # Create event data
            event = {
                'type': 'security_alert',
                'log_id': str(instance.id),
                'event_type': instance.event_type,
                'event_type_display': instance.get_event_type_display(),
                'severity': instance.severity,
                'severity_display': instance.get_severity_display(),
                'ip_address': instance.ip_address,
                'details': instance.details,
                'timestamp': instance.created_at.isoformat()
            }
            
            # Send to user
            async_to_sync(channel_layer.group_send)(
                f'user_{instance.user.id}',
                event
            )
        except Exception:
            pass

# Session signals
@receiver(post_save, sender=UserSession)
def session_updated(sender, instance, created, **kwargs):
    """Broadcast session events"""
    try:
        event_type = 'session_created' if created else 'session_updated'
        
        # Create event data
        event = {
            'type': event_type,
            'session_id': str(instance.id),
            'is_active': instance.is_active,
            'device_name': instance.device_name,
            'ip_address': instance.ip_address,
            'expires_at': instance.expires_at.isoformat(),
            'timestamp': timezone.now().isoformat()
        }
        
        # Send to user
        async_to_sync(channel_layer.group_send)(
            f'user_{instance.user.id}',
            event
        )
    except Exception:
        pass

# Backup signals
@receiver(post_save, sender=Backup)
def backup_created(sender, instance, created, **kwargs):
    """Broadcast backup events"""
    if created:
        try:
            # Create event data
            event = {
                'type': 'backup_created',
                'backup_id': str(instance.id),
                'size': instance.size,
                'timestamp': instance.created_at.isoformat()
            }
            
            # Send to user
            async_to_sync(channel_layer.group_send)(
                f'user_{instance.user.id}',
                event
            )
        except Exception:
            pass