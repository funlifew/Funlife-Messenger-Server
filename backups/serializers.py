from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from .models import Backup
from user_sessions.models import UserSession
from accounts.serializers import UserSerializer

User = get_user_model()

class BackupSerializer(serializers.ModelSerializer):
    """Serializer for backup model"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Backup
        fields = ['id', 'user', 'checksum', 'size', 'created_at']
        read_only_fields = ['id', 'user', 'checksum', 'size', 'created_at']

class BackupCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating backups"""
    session_id = serializers.UUIDField(required=True)
    
    class Meta:
        model = Backup
        fields = ['encrypted_data', 'checksum', 'size', 'session_id']
    
    def validate_encrypted_data(self, value):
        """Validate encrypted data is present"""
        if not value:
            raise serializers.ValidationError("Encrypted data is required")
        return value
    
    def validate_session_id(self, value):
        """Validate session exists and is old enough"""
        user = self.context['request'].user
        
        try:
            session = UserSession.objects.get(id=value, user=user, is_active=True)
            
            # Check if session is at least 24 hours old
            min_age = timezone.now() - timedelta(hours=24)
            if session.created_at > min_age:
                hours_to_wait = round(24 - (timezone.now() - session.created_at).total_seconds() / 3600, 1)
                raise serializers.ValidationError(
                    f"Session must be at least 24 hours old to create a backup. Please wait {hours_to_wait} more hours."
                )
            
            self.session = session
            return value
        except UserSession.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive session")
    
    def create(self, validated_data):
        """Create a new backup"""
        user = self.context['request'].user
        session_id = validated_data.pop('session_id')
        
        return Backup.objects.create(
            user=user,
            session=self.session,
            **validated_data
        )

class BackupDownloadSerializer(serializers.Serializer):
    """Serializer for downloading backup data"""
    backup_id = serializers.UUIDField(required=True)
    
    def validate_backup_id(self, value):
        """Validate backup exists and belongs to user"""
        user = self.context['request'].user
        
        try:
            backup = Backup.objects.get(id=value, user=user)
            self.backup = backup
            return value
        except Backup.DoesNotExist:
            raise serializers.ValidationError("Backup not found")