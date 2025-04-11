from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Friendship, FriendshipStatus
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=Friendship)
def friendship_updated(sender, instance, created, **kwargs):
    """Handle friendship updates and status changes"""
    if created:
        # New friendship created - could add notifications here
        pass
    else:
        # Friendship status changed
        if instance.status == FriendshipStatus.ACCEPTED:
            # When a friendship is accepted, we could send notifications
            pass
        elif instance.status == FriendshipStatus.REJECTED:
            # When a friendship is rejected, we could handle cleanup
            pass
        elif instance.status == FriendshipStatus.BLOCKED:
            # When a user is blocked, we might want to:
            # 1. Delete any existing messages between the users
            # 2. Prevent future messages
            pass

@receiver(post_delete, sender=Friendship)
def friendship_deleted(sender, instance, **kwargs):
    """Handle friendship deletion"""
    # Could add cleanup tasks or notifications here
    pass