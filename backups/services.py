from django.contrib.auth import get_user_model
from .models import Backup
from messagings.models import Message
from friendships.models import Friendship, FriendshipStatus
from profiles.models import Profile
from user_sessions.models import UserSession
from django.db.models import Q
import hashlib
import json

User = get_user_model()

class BackupService:
    """Service for handling backup operations"""
    
    @staticmethod
    def generate_backup_data(user):
        """Generate backup data for a user"""
        # Basic user data (without sensitive info)
        user_data = {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'created_at': user.created_at.isoformat(),
        }
        
        # Profile data
        try:
            profile = user.profile
            profile_data = {
                'id': str(profile.id),
                'display_name': profile.display_name,
                'status': profile.status,
                'bio': profile.bio,
                'created_at': profile.created_at.isoformat(),
            }
        except Profile.DoesNotExist:
            profile_data = {}
        
        # Friends data
        friends = Friendship.get_user_friends(user)
        friends_data = []
        
        for friend in friends:
            friendship = Friendship.get_friendship(user, friend)
            friend_data = {
                'id': str(friend.id),
                'username': friend.username,
                'status': friendship.status if friendship else None,
                'created_at': friendship.created_at.isoformat() if friendship else None,
            }
            
            # Add friend's profile if available
            try:
                friend_profile = friend.profile
                friend_data['profile'] = {
                    'display_name': friend_profile.display_name,
                    'status': friend_profile.status,
                }
            except Profile.DoesNotExist:
                pass
                
            friends_data.append(friend_data)
        
        # Messages data (encrypt with client's key in real app)
        messages = Message.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).order_by('created_at')
        
        messages_data = []
        for message in messages:
            message_data = {
                'id': str(message.id),
                'sender': message.sender.username,
                'receiver': message.receiver.username,
                'created_at': message.created_at.isoformat(),
                'is_read': message.is_read,
                'is_delivered': message.is_delivered,
                'encrypted_content': message.encrypted_content,
            }
            messages_data.append(message_data)
        
        # Combine all data
        backup_data = {
            'user': user_data,
            'profile': profile_data,
            'friends': friends_data,
            'messages': messages_data,
        }
        
        return backup_data
    
    @staticmethod
    def calculate_checksum(data):
        """Calculate SHA-256 checksum for data integrity"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    @staticmethod
    def create_backup(user, session, encrypted_data, size, checksum):
        """Create a new backup in the database"""
        return Backup.objects.create(
            user=user,
            session=session,
            encrypted_data=encrypted_data,
            size=size,
            checksum=checksum
        )