from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """User Serializer"""
    class Meta:
        model = User
        read_only_fields = ["id", "username", "password", "email", "role", "is_superuser", "is_staff"]

class RegisterSerializer(serializers.ModelSerializer):
    """Register Flow Serializer"""
    class Meta:
        model = User
        write_only_fields = ['username', 'password', 'email']

class LoginSerializer(serializers.ModelSerializer):
    """Login Flow Serializer"""
    class Meta:
        model = User
        write_only_fields = ['username', 'password']