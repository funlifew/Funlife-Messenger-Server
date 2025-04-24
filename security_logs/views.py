from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .models import SecurityLog, EventType, SeverityLevel
from .serializers import (
    SecurityLogSerializer, 
    SecurityLogFilterSerializer,
    SecurityActivitySummarySerializer
)

User = get_user_model()

class SecurityLogListView(generics.ListAPIView):
    """
    List security logs with optional filtering
    
    Admin users can see all logs, regular users can only see their own logs
    """
    
    serializer_class = SecurityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get filtered query set based on users role and query params"""
        user = self.request.user
        
        # Filter serializer for validation
        filter_serializer = SecurityLogFilterSerializer(data=self.request.query_params)
        filter_serializer.is_valid()
        filters = filter_serializer.validated_data
        
        # Base queryset
        if user.is_staff or getattr(user, 'role', None) == 'admin':
            # Admin users can see all logs
            queryset = SecurityLog.objects.all()
        else:
            # Regular users can only see their own logs
            queryset = SecurityLog.objects.filter(user=user)
        
        # Apply filters
        if 'event_type' in filters:
            queryset = queryset.filter(event_type=filters['event_type'])
            
        if 'severity' in filters:
            queryset = queryset.filter(severity=filters['severity'])
            
        if 'user_id' in filters and (user.is_staff or getattr(user, 'role', None) == 'admin'):
            queryset = queryset.filter(user__id=filters['user_id'])
            
        if 'ip_address' in filters:
            queryset = queryset.filter(ip_address=filters['ip_address'])
            
        if 'date_from' in filters:
            queryset = queryset.filter(created_at__gte=filters['date_from'])
            
        if 'date_to' in filters:
            queryset = queryset.filter(created_at__lte=filters['date_to'])
        
        # Apply limit
        limit = filters.get('limit', 100)
        
        # Always sort by newest first
        return queryset.order_by('-created_at')[:limit]

class UserSecurityLogView(generics.ListAPIView):
    """
    Get security logs for the current user
    """
    serializer_class = SecurityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get logs for the current user"""
        user = self.request.user
        return SecurityLog.get_user_logs(user)

class UserSecurityActivityView(APIView):
    """
    Get summary of security activity for the current user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get security activity summary"""
        user = request.user
        
        # Get logs from the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_logs = SecurityLog.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago
        )
        
        # Count login attempts (both successful and failed)
        login_count = recent_logs.filter(event_type=EventType.LOGIN).count()
        failed_login_count = recent_logs.filter(event_type=EventType.FAILED_LOGIN).count()
        
        # Get unique IP addresses
        unique_ips = recent_logs.values_list('ip_address', flat=True).distinct()
        unique_ip_count = len([ip for ip in unique_ips if ip])
        
        # Get suspicious activity
        suspicious_count = recent_logs.filter(
            severity__in=[SeverityLevel.WARNING, SeverityLevel.ERROR, SeverityLevel.CRITICAL]
        ).count()
        
        # Get most recent successful login
        last_login = recent_logs.filter(event_type=EventType.LOGIN).order_by('-created_at').first()
        
        # Get the 10 most recent logs
        recent_events = SecurityLogSerializer(
            recent_logs.order_by('-created_at')[:10], 
            many=True
        ).data
        
        # Compile the summary
        summary = {
            'login_count': login_count,
            'failed_login_count': failed_login_count,
            'unique_ip_count': unique_ip_count,
            'suspicious_activity_count': suspicious_count,
            'last_login': SecurityLogSerializer(last_login).data if last_login else None,
            'recent_events': recent_events
        }
        
        return Response(summary)

class SuspiciousActivityView(generics.ListAPIView):
    """
    List suspicious activity (admin only)
    """
    serializer_class = SecurityLogSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        """Get suspicious activity logs"""
        return SecurityLog.get_suspicious_logs()

class IPAddressLogsView(generics.ListAPIView):
    """
    List logs for a specific IP address (admin only)
    """
    serializer_class = SecurityLogSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        """Get logs for a specific IP address"""
        ip_address = self.kwargs.get('ip_address')
        return SecurityLog.get_logs_by_ip(ip_address)