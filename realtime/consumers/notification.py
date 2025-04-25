from .base import BaseConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from security_logs.models import SecurityLog, EventType, SeverityLevel
from django.db.models import Q

class NotificationConsumer(BaseConsumer):
    """Consumer for system-wide notifications"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        await super().connect()
        
        if not hasattr(self, 'user') or self.user.is_anonymous:
            return
            
        # Send any pending notifications on connect
        await self.send_pending_notifications()
    
    # Handler methods
    
    async def handle_mark_read(self, data):
        """Handle marking notifications as read"""
        notification_id = data.get('notification_id')
        
        if not notification_id:
            await self.send_json({
                'type': 'error',
                'code': 'missing_notification_id',
                'message': 'Notification ID is required'
            })
            return
            
        # Mark notification as read
        result = await self.mark_notification_read(notification_id)
        
        if result.get('success'):
            await self.send_json({
                'type': 'notification_marked_read',
                'notification_id': notification_id,
                'timestamp': timezone.now().isoformat()
            })
        else:
            await self.send_json({
                'type': 'error',
                'code': result.get('code'),
                'message': result.get('message')
            })
    
    async def handle_clear_all(self, data):
        """Handle clearing all notifications"""
        # Clear all notifications
        result = await self.clear_all_notifications()
        
        if result.get('success'):
            await self.send_json({
                'type': 'notifications_cleared',
                'count': result.get('count'),
                'timestamp': timezone.now().isoformat()
            })
        else:
            await self.send_json({
                'type': 'error',
                'code': result.get('code'),
                'message': result.get('message')
            })
    
    # Database methods
    
    @database_sync_to_async
    def get_pending_notifications(self):
        """Get pending notifications for the user"""
        # This is a placeholder - you'll need to implement a Notification model
        # For now, we'll use security logs as an example
        try:
            logs = SecurityLog.objects.filter(
                user=self.user,
                severity__gte=SeverityLevel.WARNING
            ).order_by('-created_at')[:10]
            
            return [{
                'id': str(log.id),
                'type': log.event_type,
                'title': log.get_event_type_display(),
                'message': f"Security alert: {log.get_event_type_display()}",
                'severity': log.severity,
                'timestamp': log.created_at.isoformat(),
                'details': log.details
            } for log in logs]
        except Exception:
            return []
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read"""
        # This is a placeholder - implement with your Notification model
        return {
            'success': True,
        }
    
    @database_sync_to_async
    def clear_all_notifications(self):
        """Clear all notifications for the user"""
        # This is a placeholder - implement with your Notification model
        return {
            'success': True,
            'count': 0
        }
    
    # Notification methods
    
    async def send_pending_notifications(self):
        """Send any pending notifications to the client"""
        notifications = await self.get_pending_notifications()
        
        if notifications:
            await self.send_json({
                'type': 'pending_notifications',
                'notifications': notifications,
                'count': len(notifications),
                'timestamp': timezone.now().isoformat()
            })
    
    # Channel layer event handlers
    
    async def security_alert(self, event):
        """Handle security alert notification"""
        await self.send_json(event)
    
    async def friend_notification(self, event):
        """Handle friend-related notification"""
        await self.send_json(event)
    
    async def system_notification(self, event):
        """Handle system notification"""
        await self.send_json(event)