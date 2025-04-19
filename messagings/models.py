from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from friendships.models import Friendship, FriendshipStatus
from django.core.exceptions import ValidationError
import uuid

User = get_user_model()

# Create your models here.

class Message(models.Model):
    """
    Message model for storing encrypted communications between users
    
    The content is end-to-end encrypted - only the sender and receiver
    can decrypt the message using their private keys.
    """
    
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        db_index=True
    )
    receiver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='received_messages',
        db_index=True
    )
    # Contains JSON with encrypted session key, IV, and ciphertext
    encrypted_content = models.TextField()
    
    # Message status fields
    is_read = models.BooleanField(default=False, db_index=True)
    is_delivered = models.BooleanField(default=False, db_index=True)
    
    # Message metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            # Composite indexes for common query patterns
            models.Index(fields=['sender', 'receiver', 'created_at'], name='message_conversation_idx'),
            models.Index(fields=['receiver', 'is_read'], name='unread_messages_idx'),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"
    
    def save(self, *args, **kwargs):
        """Override save to perform validation and set timestamps"""
        # Prevent messaging self
        if self.sender == self.receiver:
            raise ValidationError("Cannot send message to self")
            
        # Check if users are friends, except during migrations
        if not self._state.adding or (self.sender_id and self.receiver_id):
            if not self._check_friendship_status():
                raise ValidationError("Messages can only be sent between friends")
            
            # Ensure receiver has a public key
            if not self.receiver.public_key:
                raise ValidationError("Cannot send message: recipient has no public key")
            
        # Set delivered_at timestamp if is_delivered changed
        if self.is_delivered and not self.delivered_at:
            self.delivered_at = timezone.now()
            
        # Set read_at timestamp if is_read changed
        if self.is_read and not self.read_at:
            self.read_at = timezone.now()
            
        super().save(*args, **kwargs)
    
    def _check_friendship_status(self):
        """Check if sender and receiver are friends"""
        friendship = Friendship.get_friendship(self.sender, self.receiver)
        
        # Only allow messaging if users are friends
        if not friendship or friendship.status != FriendshipStatus.ACCEPTED:
            # Explicitly block messaging if blocked
            if friendship and friendship.status == FriendshipStatus.BLOCKED:
                return False
            return False
        return True
    
    def mark_as_delivered(self):
        """Mark message as delivered"""
        if not self.is_delivered:
            self.is_delivered = True
            self.delivered_at = timezone.now()
            self.save(update_fields=['is_delivered', 'delivered_at'])
            return True
        return False
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            # If message is read, it must also be delivered
            if not self.is_delivered:
                self.is_delivered = True
                self.delivered_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at', 'is_delivered', 'delivered_at'])
            return True
        return False
    
    @classmethod
    def get_conversation(cls, user1, user2, limit=50, offset=0):
        """Get conversation between two users"""
        # Get messages sent in both directions
        messages = cls.objects.filter(
            Q(sender=user1, receiver=user2) | 
            Q(sender=user2, receiver=user1)
        ).order_by('-created_at')
        
        # Apply pagination
        if limit:
            return messages[offset:offset+limit]
        return messages
    
    def get_unread_count(cls, user):
        """Get count of unread messages for a user"""
        return cls.objects.filter(receiver=user, is_read=False).count()
    
    @classmethod
    def get_conversations_summary(cls, user):
        """Get summary of all conversations for a user"""
        # Get all users the current user has exchanged messages with
        conversation_partners = User.objects.filter(
            Q(sent_messages__receiver=user) | 
            Q(received_messages__sender=user)
        ).distinct()
        
        # For each partner, get the most recent message
        conversations = []
        for partner in conversation_partners:
            # Check if they're still friends
            if not Friendship.are_friends(user, partner):
                continue
                
            last_message = cls.objects.filter(
                Q(sender=user, receiver=partner) | 
                Q(sender=partner, receiver=user)
            ).order_by('-created_at').first()
            
            if last_message:
                unread_count = cls.objects.filter(
                    sender=partner, 
                    receiver=user, 
                    is_read=False
                ).count()
                
                conversations.append({
                    'partner': partner,
                    'last_message': last_message,
                    'unread_count': unread_count
                })
        
        # Sort by most recent message
        return sorted(
            conversations, 
            key=lambda x: x['last_message'].created_at, 
            reverse=True
        )

class TypingStatus(models.Model):
    """Model to track typing status between users"""
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='typing_statuses',
        db_index=True
    )
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='typing_notifications',
        db_index=True
    )
    is_typing = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now=True, db_index=True)
    
    class Meta:
        unique_together = [['user', 'recipient']]
        indexes = [
            models.Index(fields=['user', 'recipient', 'is_typing'], name='typing_status_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.username} typing to {self.recipient.username}: {self.is_typing}"
    
    @classmethod
    def set_typing(cls, user, recipient, is_typing):
        """Set or update typing status"""
        # Verify users are friends before allowing typing status updates
        if not Friendship.are_friends(user, recipient):
            return None
            
        obj, created = cls.objects.update_or_create(
            user=user,
            recipient=recipient,
            defaults={'is_typing': is_typing, 'timestamp': timezone.now()}
        )
        return obj
    
    @classmethod
    def get_status(cls, user, recipient):
        """Get typing status between two users"""
        try:
            return cls.objects.get(user=user, recipient=recipient)
        except cls.DoesNotExist:
            return None