from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.serializers import UserSerializer
from profiles.serializers import ProfileSerializer
from .models import Friendship, FriendshipStatus

User = get_user_model()

class FriendshipSerializer(serializers.ModelSerializer):
    """Serializer for Friendship model"""
    user = UserSerializer(read_only=True)
    friend = UserSerializer(read_only=True)
    
    class Meta:
        model = Friendship
        fields = ['id', 'user', 'friend', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'friend', 'created_at', 'updated_at']

class FriendRequestSerializer(serializers.Serializer):
    """Serializer for sending friend requests"""
    username = serializers.CharField(required=True)
    
    def validate_username(self, value):
        """Checking for existing username"""
        user = self.context['request'].user
        
        # Check if username exists
        friend = self._check_for_username(value)
        
        # Cannot send request to self
        if friend == user:
            raise serializers.ValidationError("You cannot send a friend request to yourself")

        # Check if friendship already exists (in either direction)
        self._check_for_existing_friendships(user, friend)
        
        self.friend = friend
        return value
    
    # Helper methods
    def _check_for_username(self, username):
        """Check if friend username exists"""
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
    
    def _check_for_existing_friendships(self, user, friend):
        """Check for existing friendships (prevents duplication)"""
        existing = Friendship.get_friendship(user, friend)
        if not existing:
            return
            
        # Handle different friendship statuses
        if existing.status == FriendshipStatus.ACCEPTED:
            raise serializers.ValidationError("You are already friends with this user")
            
        elif existing.status == FriendshipStatus.PENDING:
            if existing.user == user:
                raise serializers.ValidationError("You have already sent a friend request to this user")
            else:
                raise serializers.ValidationError(f"{friend.username} has already sent you a friend request")
                
        elif existing.status == FriendshipStatus.BLOCKED:
            # Generic message for privacy/security
            raise serializers.ValidationError("Unable to send friend request")

class FriendProfileSerializer(serializers.ModelSerializer):
    """Serializer for friend profile data"""
    profile = ProfileSerializer(source='profiles', read_only=True)
    friendship_id = serializers.SerializerMethodField()
    friendship_status = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'profile', 'friendship_id', 'friendship_status']
    
    def get_friendship_id(self, obj):
        """Get the friendship ID between request user and this user"""
        request_user = self.context['request'].user
        friendship = Friendship.get_friendship(request_user, obj)
        return str(friendship.id) if friendship else None
    
    def get_friendship_status(self, obj):
        """Get the friendship status between request user and this user"""
        request_user = self.context['request'].user
        friendship = Friendship.get_friendship(request_user, obj)
        return friendship.status if friendship else None
    
class FriendRequestActionSerializer(serializers.Serializer):
    """Serializer for accepting/rejecting/blocking friend requests"""
    friendship_id = serializers.UUIDField(required=True)
    
    def validate_friendship_id(self, value):
        """Validate the friendship ID"""
        user = self.context['request'].user
        
        try:
            friendship = Friendship.objects.get(id=value)
            
            # Check if the current user is part of this friendship
            if friendship.user != user and friendship.friend != user:
                raise serializers.ValidationError("Invalid friendship request")
                
            self.friendship = friendship
            return value
        except Friendship.DoesNotExist:
            raise serializers.ValidationError("Friend request not found")