from .base import BaseConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from profiles.models import Profile
from friendships.models import Friendship

class ProfileConsumer(BaseConsumer):
    """Consumer for profile-related events"""
    
    async def connect(self):
        await super().connect()
        
        if not hasattr(self, 'user') or self.user.is_anonymous:
            return
            
        # Update user's online status
        await self.update_online_status(True)
        
        # Notify friends of online status
        await self.notify_friends_status_change(True)
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'user') and not self.user.is_anonymous:
            # Update user's online status
            await self.update_online_status(False)
            
            # Notify friends of offline status
            await self.notify_friends_status_change(False)
            
        await super().disconnect(close_code)
    
    # Handler methods
    async def handle_update_status(self, data):
        """Handle status update requests"""
        status = data.get('status')
        if not status:
            await self.send_json({
                'type': 'error',
                'code': 'missing_status',
                'message': 'Status message is required'
            })
            return
            
        # Update status in database
        success = await self.update_user_status(status)
        
        if success:
            # Notify friends of status update
            await self.notify_friends_status_update(status)
            
            await self.send_json({
                'type': 'status_updated',
                'status': status,
                'timestamp': timezone.now().isoformat()
            })
        else:
            await self.send_json({
                'type': 'error',
                'code': 'status_update_failed',
                'message': 'Failed to update status'
            })
    
    # Database methods:
    @database_sync_to_async
    def update_user_status(self, status):
        """Update user's status message"""
        try:
            profile = self.user.profile
            profile.status = status
            profile.save(update_fields=['status'])
            return True
        except Exception as e:
            return False
    
    @database_sync_to_async
    def get_user_friends(self):
        """Get list of user's friends"""
        return list(Friendship.get_user_friends(self.user))
    
    # Notification methods
    
    async def notify_friends_status_change(self, is_online):
        """Notify friends of online/offline status change"""
        friends = await self.get_user_friends()
        
        for friend in friends:
            # Send to each friend's personal group
            await self.channel_layer.group_send(
                f'user_{friend.id}',
                {
                    'type': 'presence_update',
                    'user_id': str(self.user.id),
                    'username': self.user.username,
                    'is_online': is_online,
                    'timestamp': timezone.now().isoformat()
                }
            )
    
    async def notify_friends_status_update(self, status):
        """Notify friends of status message update"""
        friends = await self.get_user_friends()
        
        for friend in friends:
            # Send to each friend's personal group
            await self.channel_layer.group_send(
                f'user_{friend.id}',
                {
                    'type': 'status_message_update',
                    'user_id': str(self.user.id),
                    'username': self.user.username,
                    'status': status,
                    'timestamp': timezone.now().isoformat()
                }
            )
    
    # Channel layer event handlers
    async def presence_update(self, event):
        """Handle presence update event from channel layer"""
        await self.send_json(event)
    
    async def status_message_update(self, event):
        """Handle status message update event from channel layer"""
        await self.send_json(event)
    