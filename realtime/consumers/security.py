from .base import BaseConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from security_logs.models import SecurityLog, EventType, SeverityLevel
from django.db.models import Q

class SecurityConsumer(BaseConsumer):
    """Consumer for security-related events"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        await super().connect()
        
        if not hasattr(self, 'user') or self.user.is_anonymous:
            return
            
        # Send security summary on connect
        await self.send_security_summary()
    
    # Handler methods
    
    async def handle_get_security_logs(self, data):
        """Handle fetching security logs"""
        event_type = data.get('event_type')
        severity = data.get('severity')
        limit = data.get('limit', 100)
        
        # Get security logs
        logs = await self.get_security_logs(event_type, severity, limit)
        
        await self.send_json({
            'type': 'security_logs',
            'logs': logs,
            'count': len(logs),
            'timestamp': timezone.now().isoformat()
        })
    
    # Database methods
    
    @database_sync_to_async
    def get_security_summary(self):
        """Get security summary for the user"""
        try:
            # Get counts of different event types
            login_count = SecurityLog.objects.filter(
                user=self.user,
                event_type=EventType.LOGIN,
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).count()
            
            failed_login_count = SecurityLog.objects.filter(
                user=self.user,
                event_type=EventType.FAILED_LOGIN,
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).count()
            
            warning_count = SecurityLog.objects.filter(
                user=self.user,
                severity__gte=SeverityLevel.WARNING,
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).count()
            
            # Get unique IP addresses
            ip_addresses = SecurityLog.objects.filter(
                user=self.user,
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).values_list('ip_address', flat=True).distinct()
            
            # Get most recent login
            last_login = SecurityLog.objects.filter(
                user=self.user,
                event_type=EventType.LOGIN
            ).order_by('-created_at').first()
            
            return {
                'login_count': login_count,
                'failed_login_count': failed_login_count,
                'warning_count': warning_count,
                'unique_ip_count': len([ip for ip in ip_addresses if ip]),
                'last_login': {
                    'timestamp': last_login.created_at.isoformat() if last_login else None,
                    'ip_address': last_login.ip_address if last_login else None,
                    'device_info': last_login.device_info if last_login else None
                } if last_login else None
            }
        except Exception as e:
            return {
                'error': str(e)
            }
    
    @database_sync_to_async
    def get_security_logs(self, event_type=None, severity=None, limit=100):
        """Get security logs for the user"""
        try:
            # Start with all logs for this user
            query = SecurityLog.objects.filter(user=self.user)
            
            # Apply filters if provided
            if event_type:
                query = query.filter(event_type=event_type)
            
            if severity is not None:  # Zero is a valid severity level
                query = query.filter(severity=severity)
            
            # Order by newest first and apply limit
            logs = query.order_by('-created_at')[:limit]
            
            return [{
                'id': str(log.id),
                'event_type': log.event_type,
                'event_type_display': log.get_event_type_display(),
                'severity': log.severity,
                'severity_display': log.get_severity_display(),
                'ip_address': log.ip_address,
                'device_info': log.device_info,
                'details': log.details,
                'created_at': log.created_at.isoformat()
            } for log in logs]
        except Exception:
            return []
    
    # Notification methods
    
    async def send_security_summary(self):
        """Send security summary to the client"""
        summary = await self.get_security_summary()
        
        await self.send_json({
            'type': 'security_summary',
            'summary': summary,
            'timestamp': timezone.now().isoformat()
        })
    
    # Channel layer event handlers
    
    async def security_event(self, event):
        """Handle security event notification"""
        await self.send_json(event)