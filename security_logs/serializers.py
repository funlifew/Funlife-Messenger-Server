from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.serializers import UserSerializer
from .models import SecurityLog, EventType, SeverityLevel

User = get_user_model()

class SecurityLogSerializer(serializers.ModelSerializer):
    """Serializer for SecurityLog model"""
    
    user = UserSerializer(read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    
    class Meta:
        model = SecurityLog
        fields = [
            'id', 'user', 'event_type', 'event_type_display', 'ip_address',
            'device_info', 'severity', 'severity_display', 'details', 'created_at'
        ]
        
        read_only_fields = fields

class SecurityLogFilterSerializer(serializers.Serializer):
    """Serializer for filtering security logs"""
    event_type = serializers.ChoiceField(choices=EventType.choices, required=False)
    severity = serializers.ChoiceField(choices=SeverityLevel.choices, required=False)
    user_id = serializers.UUIDField(required=False)
    ip_address = serializers.IPAddressField(required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    limit = serializers.IntegerField(min_value=1, max_value=1000, default=100, required=False)

class SecurityActivitySummarySerializer(serializers.Serializer):
    """Serializer for summarizing security activity"""
    login_count = serializers.IntegerField()
    failed_login_count = serializers.IntegerField()
    suspicious_activity_count = serializers.IntegerField()
    unique_ip_count = serializers.IntegerField()
    last_login = SecurityLogSerializer()
    recent_events = SecurityLogSerializer(many=True)