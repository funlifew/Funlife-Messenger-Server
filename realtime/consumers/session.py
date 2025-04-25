from .base import BaseConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from user_sessions.models import UserSession
from django.db.models import Q

class SessionConsumer(BaseConsumer):
    """Consumer for user session management"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        await super().connect()
        
        if not hasattr(self, 'user') or self.user.is_anonymous:
            return
            
        # Send active sessions on connect
        await self.send_active_sessions()
    
    # Handler methods
    
    async def handle_invalidate_session(self, data):
        """Handle invalidating a session"""
        session_id = data.get('session_id')
        
        if not session_id:
            await self.send_json({
                'type': 'error',
                'code': 'missing_session_id',
                'message': 'Session ID is required'
            })
            return
            
        # Invalidate session
        result = await self.invalidate_session(session_id)
        
        if result.get('success'):
            await self.send_json({
                'type': 'session_invalidated',
                'session_id': session_id,
                'timestamp': timezone.now().isoformat()
            })
            
            # Also notify other sessions of the same user
            await self.channel_layer.group_send(
                f'user_{self.user.id}',
                {
                    'type': 'session_update',
                    'action': 'invalidated',
                    'session_id': session_id,
                    'timestamp': timezone.now().isoformat()
                }
            )
        else:
            await self.send_json({
                'type': 'error',
                'code': result.get('code'),
                'message': result.get('message')
            })
    
    async def handle_invalidate_all_sessions(self, data):
        """Handle invalidating all sessions except current"""
        current_session_id = data.get('current_session_id')
        
        if not current_session_id:
            await self.send_json({
                'type': 'error',
                'code': 'missing_current_session_id',
                'message': 'Current session ID is required'
            })
            return
            
        # Invalidate all other sessions
        result = await self.invalidate_all_sessions(current_session_id)
        
        if result.get('success'):
            await self.send_json({
                'type': 'all_sessions_invalidated',
                'count': result.get('count'),
                'timestamp': timezone.now().isoformat()
            })
            
            # Notify other sessions
            await self.channel_layer.group_send(
                f'user_{self.user.id}',
                {
                    'type': 'session_update',
                    'action': 'all_invalidated',
                    'except_session_id': current_session_id,
                    'timestamp': timezone.now().isoformat()
                }
            )
        else:
            await self.send_json({
                'type': 'error',
                'code': result.get('code'),
                'message': result.get('message')
            })
    
    async def handle_extend_session(self, data):
        """Handle extending a session"""
        session_id = data.get('session_id')
        days = data.get('days', 30)
        
        if not session_id:
            await self.send_json({
                'type': 'error',
                'code': 'missing_session_id',
                'message': 'Session ID is required'
            })
            return
            
        # Extend session
        result = await self.extend_session(session_id, days)
        
        if result.get('success'):
            await self.send_json({
                'type': 'session_extended',
                'session_id': session_id,
                'expires_at': result.get('expires_at'),
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
    def get_active_sessions(self):
        """Get active sessions for the user"""
        try:
            sessions = UserSession.get_active_sessions(self.user)
            
            return [{
                'id': str(session.id),
                'device_name': session.device_name,
                'ip_address': session.ip_address,
                'created_at': session.created_at.isoformat(),
                'expires_at': session.expires_at.isoformat(),
                'last_activity': session.last_activity.isoformat() if session.last_activity else None
            } for session in sessions]
        except Exception:
            return []
    
    @database_sync_to_async
    def invalidate_session(self, session_id):
        """Invalidate a specific session"""
        try:
            session = UserSession.objects.get(id=session_id, user=self.user)
            session.invalidate()
            
            return {
                'success': True
            }
        except UserSession.DoesNotExist:
            return {
                'success': False,
                'code': 'session_not_found',
                'message': 'Session not found'
            }
        except Exception as e:
            return {
                'success': False,
                'code': 'invalidation_failed',
                'message': str(e)
            }
    
    @database_sync_to_async
    def invalidate_all_sessions(self, current_session_id):
        """Invalidate all sessions except current"""
        try:
            # Verify the current session belongs to the user
            UserSession.objects.get(id=current_session_id, user=self.user)
            
            # Get count of active sessions excluding current
            count = UserSession.objects.filter(
                user=self.user, 
                is_active=True
            ).exclude(id=current_session_id).count()
            
            # Invalidate all other sessions
            UserSession.invalidate_all_sessions(self.user, exclude_id=current_session_id)
            
            return {
                'success': True,
                'count': count
            }
        except UserSession.DoesNotExist:
            return {
                'success': False,
                'code': 'session_not_found',
                'message': 'Current session not found'
            }
        except Exception as e:
            return {
                'success': False,
                'code': 'invalidation_failed',
                'message': str(e)
            }
    
    @database_sync_to_async
    def extend_session(self, session_id, days=30):
        """Extend a session's expiration"""
        try:
            session = UserSession.objects.get(id=session_id, user=self.user)
            session.extend_session(days=days)
            
            return {
                'success': True,
                'expires_at': session.expires_at.isoformat()
            }
        except UserSession.DoesNotExist:
            return {
                'success': False,
                'code': 'session_not_found',
                'message': 'Session not found'
            }
        except Exception as e:
            return {
                'success': False,
                'code': 'extension_failed',
                'message': str(e)
            }
    
    # Notification methods
    
    async def send_active_sessions(self):
        """Send active sessions to the client"""
        sessions = await self.get_active_sessions()
        
        await self.send_json({
            'type': 'active_sessions',
            'sessions': sessions,
            'count': len(sessions),
            'timestamp': timezone.now().isoformat()
        })
    
    # Channel layer event handlers
    
    async def session_update(self, event):
        """Handle session update notification"""
        await self.send_json(event)