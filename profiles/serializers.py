from rest_framework import serializers
from accounts.serializers import UserSerializer
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    """Profile View Serializer"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Profile
        read_only_fields = ['id', 'public_key', 'last_seen', 'is_online', 'created_at', 'updated_at']
