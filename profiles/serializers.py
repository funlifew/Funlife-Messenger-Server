from rest_framework import serializers
from accounts.serializers import UserSerializer
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    """Profile View Serializer"""
    user = UserSerializer(read_only=True)
    offline_duration = serializers.CharField(source='offline_duration_display', read_only=True)
    
    class Meta:
        model = Profile
        fields = ['id', 'user', 'display_name', 'status', 'bio', 'is_online', 'last_seen', 'offline_duration', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'is_online', 'last_seen', 'offline_duration', 'created_at', 'updated_at']