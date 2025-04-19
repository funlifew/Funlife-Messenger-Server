from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.serializers import UserSerializer
from friendships.models import Friendship, FriendshipStatus
from .models import Message, TypingStatus

User = get_user_model()

class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model"""
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'receiver', 'encrypted_content', 
            'is_read', 'is_delivered', 'created_at', 
            'delivered_at', 'read_at'
        ]
        read_only_fields = [
            'id', 'sender', 'is_read', 'is_delivered', 
            'created_at', 'delivered_at', 'read_at'
        ]

class MessageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new encrypted message
    
    The plaintext content should already be encrypted by the client
    using the recipient's public key before submitting.
    """
    receiver_id = serializers.UUIDField(required=True)
    encrypted_content = serializers.CharField(required=True)
    
    class Meta:
        model = Message
        fields = ['receiver_id', 'encrypted_content']
    
    def validate_receiver_id(self, value):
        """Validate the receiver exists and is a friend"""
        user = self.context['request'].user
        
        try:
            receiver = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Receiver not found")
        
        # Check for self-messaging
        if user == receiver:
            raise serializers.ValidationError("Cannot send message to yourself")
        
        # Check if users are friends
        friendship = Friendship.get_friendship(user, receiver)
        if not friendship or friendship.status != FriendshipStatus.ACCEPTED:
            raise serializers.ValidationError("You can only message users who are your friends")
        
        # Check for blocked status
        if friendship and friendship.status == FriendshipStatus.BLOCKED:
            # Don't reveal blocking information
            raise serializers.ValidationError("Cannot send message to this user")
        
        # Ensure receiver has a public key
        if not receiver.public_key:
            raise serializers.ValidationError("Recipient has not set up encryption")
        
        self.receiver = receiver
        return value
    
    def validate_encrypted_content(self, value):
        """Validate the encrypted content format"""
        import json
        
        # Verify that the content is valid JSON
        try:
            payload = json.loads(value)
            
            # Check for required fields
            required_fields = ['encrypted_session_key', 'iv', 'ciphertext']
            for field in required_fields:
                if field not in payload:
                    raise serializers.ValidationError(f"Missing required field: {field}")
                    
            # Add validation for base64 encoded fields
            try:
                import base64
                base64.b64decode(payload['encrypted_session_key'])
                base64.b64decode(payload['iv'])
                base64.b64decode(payload['ciphertext'])
            except Exception:
                raise serializers.ValidationError("Invalid base64 encoding in payload fields")
                    
            return value
        except json.JSONDecodeError:
            raise serializers.ValidationError("Invalid encrypted content format")
    
    def create(self, validated_data):
        """Create and return a new message"""
        user = self.context['request'].user
        receiver = self.receiver
        
        message = Message.objects.create(
            sender=user,
            receiver=receiver,
            encrypted_content=validated_data['encrypted_content']
        )
        
        return message

class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversation list"""
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    is_sender = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'receiver', 'encrypted_content',
            'is_read', 'is_delivered', 'created_at', 
            'is_sender'
        ]
    
    def get_is_sender(self, obj):
        """Determine if the current user is the sender of the message"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.sender == request.user
        return False

class ConversationSummarySerializer(serializers.Serializer):
    """Serializer for conversation summaries"""
    partner = UserSerializer()
    last_message = MessageSerializer()
    unread_count = serializers.IntegerField()

class TypingStatusSerializer(serializers.ModelSerializer):
    """Serializer for typing status"""
    user = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    
    class Meta:
        model = TypingStatus
        fields = ['id', 'user', 'recipient', 'is_typing', 'timestamp']
        read_only_fields = ['id', 'user', 'timestamp']

class TypingStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating typing status"""
    recipient_id = serializers.UUIDField(required=True)
    is_typing = serializers.BooleanField(required=True)
    
    def validate_recipient_id(self, value):
        """Validate the recipient exists and is a friend"""
        user = self.context['request'].user
        
        try:
            recipient = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient not found")
        
        # Check if users are friends
        if not Friendship.are_friends(user, recipient):
            raise serializers.ValidationError("You can only send typing status to friends")
        
        self.recipient = recipient
        return value

class KeyPairGenerationSerializer(serializers.Serializer):
    """Serializer for generating a new key pair"""
    pass

class PublicKeySerializer(serializers.Serializer):
    """Serializer for retrieving a user's public key"""
    user_id = serializers.UUIDField(required=True)
    
    def validate_user_id(self, value):
        """Validate that the user exists"""
        try:
            user = User.objects.get(id=value)
            self.user = user
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")