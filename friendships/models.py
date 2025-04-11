from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

# Create your models here.

class FriendshipStatus(models.TextChoices):
    """Friendship status choices"""
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
    BLOCKED = "blocked", "Blocked"

class Friendship(models.Model):
    """Friendship model to manage user relationships"""
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="friendships_initiated",
        db_index=True
    )
    friend = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="friendships_received",
        db_index=True
    )
    status = models.CharField(
        max_length=20, 
        choices=FriendshipStatus.choices,
        default=FriendshipStatus.PENDING,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # Ensure unique friendship between users
        unique_together = [['user', 'friend']]
        # Default ordering by creation date
        ordering = ['-created_at']
        # Add composite indexes for common query patterns
        indexes = [
            models.Index(fields=['user', 'status'], name='user_status_idx'),
            models.Index(fields=['friend', 'status'], name='friend_status_idx'),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} -> {self.friend.username} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Override save to prevent self-friendship"""
        if self.user == self.friend:
            raise ValueError("Users cannot be friends with themselves")
        super().save(*args, **kwargs)
    
    # Helper methods
    @classmethod
    def are_friends(cls, user1, user2):
        """Check if two users are friends"""
        friendship1 = cls.objects.filter(
            user=user1, 
            friend=user2, 
            status=FriendshipStatus.ACCEPTED
        ).exists()
        
        friendship2 = cls.objects.filter(
            user=user2, 
            friend=user1, 
            status=FriendshipStatus.ACCEPTED
        ).exists()
        
        return friendship1 or friendship2
    
    @classmethod
    def get_friendship(cls, user1, user2):
        """Get friendship object between two users (in either direction)"""
        try:
            return cls.objects.get(user=user1, friend=user2)
        except cls.DoesNotExist:
            try:
                return cls.objects.get(user=user2, friend=user1)
            except cls.DoesNotExist:
                return None
    
    @classmethod
    def get_user_friends(cls, user):
        """Get all friends of a user (with ACCEPTED status)"""
        # Friends where user is the requester
        friends1 = cls.objects.filter(
            user=user,
            status=FriendshipStatus.ACCEPTED
        ).values_list('friend', flat=True)
        
        # Friends where user is the receiver
        friends2 = cls.objects.filter(
            friend=user,
            status=FriendshipStatus.ACCEPTED
        ).values_list('user', flat=True)
        
        # Combine both querysets and return User objects
        return User.objects.filter(id__in=list(friends1) + list(friends2))
    
    @classmethod
    def get_pending_requests(cls, user):
        """Get all pending friend requests for a user"""
        return cls.objects.filter(
            friend=user,
            status=FriendshipStatus.PENDING
        )
    
    @classmethod
    def get_sent_requests(cls, user):
        """Get all friend requests sent by a user"""
        return cls.objects.filter(
            user=user,
            status=FriendshipStatus.PENDING
        )
    
    @classmethod
    def get_blocked_users(cls, user):
        """Get all users blocked by a user"""
        return cls.objects.filter(
            user=user,
            status=FriendshipStatus.BLOCKED
        ).values_list('friend', flat=True)
    
    def accept(self):
        """Accept a friend request"""
        if self.status == FriendshipStatus.PENDING:
            self.status = FriendshipStatus.ACCEPTED
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    def reject(self):
        """Reject a friend request"""
        if self.status == FriendshipStatus.PENDING:
            self.status = FriendshipStatus.REJECTED
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    def block(self):
        """Block a user"""
        self.status = FriendshipStatus.BLOCKED
        self.save(update_fields=['status', 'updated_at'])
        return True
    
    def unblock(self):
        """Unblock a previously blocked user"""
        if self.status == FriendshipStatus.BLOCKED:
            self.delete()
            return True
        return False