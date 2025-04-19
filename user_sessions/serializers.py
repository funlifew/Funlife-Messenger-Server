from rest_framework import serializers
from .models import UserSession
from accounts.serializers import UserSerializer

class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for UserSession model"""
    user = UserSerializer(read_only=True)
    device_name = serializers.CharField(read_only=True, source='device_name')
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'user', 'device_info', 'ip_address', 'is_active',
            'created_at', 'expires_at', 'last_activity', 'device_name'
        ]

        read_only_fields = [
            'id', 'user', 'device_info', 'ip_address', 
            'created_at', 'last_activity'
        ]


class SessionUpdateSerializer(serializers.Serializer):
    """Serializer for updating session properties"""
    expires_at = serializers.DateTimeField(required=False)
    is_active = serializers.BooleanField(required=False)
