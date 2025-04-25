import json, logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth import get_user_model


# User model
User = get_user_model()
# install logging
logger = logging.getLogger(__name__)

class BaseConsumer(AsyncJsonWebsocketConsumer):
    """Base WebSocket consumer with common functionality"""
    
    async def connect(self):
        """Handle websocket connection"""
        # Get authenticated user
        self.user = self.scope['user']
        
        # Reject anonymous users
        if self.user.is_anonymous:
            logger.warning("Anonymous Connection Attempt Rejected.")
            await self.close(code=403)
            return
        
        # Setup user's personal notification group
        self.user_group_name = f"user_{self.user.id}"
        
        # Join user's personal group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        # Log connection
        logger.info(f"Websocket Connected: {self.user.username}")
        
        # Accept the connection
        await self.accept()
        
        # Send connection confirmation
        await self.send_json({
            'type': 'connection_established',
            'user_id': str(self.user.id),
            'timestamp': timezone.now().isoformat(),
        })
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        
        # Leave user's group
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            
        # Log disconnection if authenticated
        if hasattr(self, 'user'):
            logger.info(f"WebSocket Disconnected: {self.user.username} (code: {close_code})")
    
    async def receive(self, text_data=None):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            
            # Extract message type and call appropirate handler
            message_type = data.get("type")
            handler_name = f"handle_{message_type}"
            
            # Check if we have handler for this message type
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                await handler(data)
            else:
                logger.warning(f"No handler for message type: {message_type}")
                await self.send_json({
                    'type': 'error',
                    'code': 'unknown_message_type',
                    'message': f"Unknown message type: {message_type}"
                })
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON message")
            await self.send_json({
                'type': 'error',
                'code': 'invalid_json',
                'message': 'Invalid JSON message'
            })
        except Exception as e:
            logger.exception("Error processing message")
            await self.send_json({
                'type': 'error',
                'code': 'server_error',
                'message': str(e)
            })
    
    async def send_json(self, content):
        """Send JSON data to the client"""
        await self.send(text_data=json.dumps(content))
    
    # Common handlers method
    async def handle_ping(self, data):
        """Handle ping messages to keep connection alive"""
        await self.send_json({
            'type': 'pong',
            'timestamp': timezone.now().isoformat()
        })
    
    # Channel layer event handlers
    async def error_message(self, event):
        """Send error message to client"""
        await self.send_json({
            'type': 'error',
            'code': event.get('code', 'unknown_error'),
            'message': event.get('message', 'An error occurred')
        })