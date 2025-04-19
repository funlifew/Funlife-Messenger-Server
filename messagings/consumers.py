import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message, TypingStatus
from friendships.models import Friendship
from django.utils import timezone
from django.db.models import Q

User = get_user_model()

class MessageConsumer(AsyncWebsocketConsumer):
    """Websocket consumer for real-time messaging"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        print("WebSocket connection attempt")
        
        self.user = self.scope['user']
        print(f"User from scope: {self.user.username if not self.user.is_anonymous else 'Anonymous'}")
        
        # Anonymous users can't connect
        if self.user.is_anonymous:
            print("Rejecting anonymous user")
            await self.close(code=4003)  # Custom code for unauthorized
            return
        
        # Get User ID from the URL route
        self.room_name = self.scope['url_route']['kwargs']['user_id']
        print(f"Target user_id from URL: {self.room_name}")
        self.room_group_name = f'chat_{self.room_name}'
        
        # Check if target user exists
        other_user = await self.get_user_by_id(self.room_name)
        if not other_user:
            print(f"Target user not found: {self.room_name}")
            await self.close(code=4004)
            return
            
        print(f"Target user found: {other_user.username}")
        
        # Store the other user
        self.other_user = other_user
        
        # Join user's personal notification group
        self.user_group_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        print(f"Accepting connection for {self.user.username}")
        await self.accept()
        print("Connection accepted")
        
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave the room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        # Leave the user's personal group
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            
        # Update typing status to False
        if hasattr(self, 'other_user'):
            await self.update_typing_status(False)
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'message':
                # Handle new message
                await self.handle_new_message(data)
            elif message_type == 'typing':
                # Handle typing status update
                await self.handle_typing_status(data)
            elif message_type == 'read':
                # Handle message read status update
                await self.handle_read_status(data)
            elif message_type == 'delete':
                # Handle message deletion
                await self.handle_delete_message(data)
            
        except json.JSONDecodeError:
            pass

    async def handle_delete_message(self, data):
        """Handle message deletion request"""
        message_id = data.get('message_id')
        
        if not message_id:
            return
        
        # Delete message in database
        success = await self.delete_message(message_id)
        
        if success:
            # Notify both users about the deletion
            deletion_notification = {
                'type': 'message_deleted',
                'message_id': message_id,
                'deleted_by': str(self.user.id),
                'timestamp': timezone.now().isoformat()
            }
            
            # Notify the other user
            await self.channel_layer.group_send(
                f'user_{self.other_user.id}',
                deletion_notification
            )
            
            # Notify the current user
            await self.channel_layer.group_send(
                f'user_{self.user.id}',
                deletion_notification
            )

    async def message_deleted(self, event):
        """Send message deletion notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
            'deleted_by': event['deleted_by'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def delete_message(self, message_id):
        """Delete a message in the database"""
        try:
            message = Message.objects.get(
                Q(sender=self.user) | Q(receiver=self.user),
                id=message_id
            )
            return message.soft_delete()
        except Message.DoesNotExist:
            return False
    
    async def handle_new_message(self, data):
        async def handle_new_message(self, data):
            """Handle a new message from the client"""
            encrypted_content = data.get('encrypted_content')
            
            if not encrypted_content:
                return
            
            # Check if users are friends BEFORE creating the message
            are_friends = await self.are_friends(self.user, self.other_user)
            if not are_friends:
                # Send error message back to client
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Cannot send message: users are not friends',
                    'code': 'not_friends'
                }))
                return
            
            # Create message in database
            message = await self.create_message(encrypted_content)
            
            if message:
                # Create message payload
                message_payload = {
                    'type': 'chat_message',
                    'message_id': str(message.id),
                    'sender_id': str(self.user.id),
                    'sender_username': self.user.username,
                    'receiver_id': str(self.other_user.id),
                    'encrypted_content': encrypted_content,
                    'created_at': message.created_at.isoformat(),
                }
                
                # Send message to recipient's personal group
                await self.channel_layer.group_send(
                    f'user_{self.other_user.id}',
                    message_payload
                )
                
                # Also send a confirmation to the sender's group
                sender_payload = message_payload.copy()
                sender_payload['is_sent'] = True  # Add flag to indicate this is sent confirmation
                await self.channel_layer.group_send(
                    f'user_{self.user.id}',
                    sender_payload
                )
    
    async def handle_typing_status(self, data):
        """Handle typing status update"""
        is_typing = data.get('is_typing', False)
        
        # Check if users are friends
        are_friends = await self.are_friends(self.user, self.other_user)
        if not are_friends:
            # Silently ignore typing status from non-friends
            return
        
        # Update typing status in database
        await self.update_typing_status(is_typing)
        
        # Broadcast typing status to other user
        await self.channel_layer.group_send(
            f'user_{self.other_user.id}',  # Send to the other user's personal group
            {
                'type': 'typing_status',
                'user_id': str(self.user.id),
                'username': self.user.username,
                'is_typing': is_typing,
                'recipient_id': str(self.other_user.id)
            }
        )
    
    
    async def handle_read_status(self, data):
        """Handle message read status update"""
        message_id = data.get('message_id')
        
        if not message_id:
            return
        
        # Update read status in database
        success = await self.mark_message_read(message_id)
        
        if success:
            # Broadcast read status to sender
            await self.channel_layer.group_send(
                f'user_{self.other_user.id}',  # Send to the other user's personal group
                {
                    'type': 'read_receipt',
                    'message_id': message_id,
                    'user_id': str(self.user.id),
                    'username': self.user.username
                }
            )
    
    async def chat_message(self, event):
        """Send message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'receiver_id': event['receiver_id'],
            'encrypted_content': event['encrypted_content'],
            'created_at': event['created_at']
        }))
    
    async def typing_status(self, event):
        """Send typing status to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing'],
            'recipient_id': event['recipient_id']
        }))
    
    async def read_receipt(self, event):
        """Send read receipt to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'username': event['username']
        }))
    
    # Database access methods
    
    @database_sync_to_async
    def get_user_by_id(self, user_id):
        """Get a user by ID"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @database_sync_to_async
    def are_friends(self, user1, user2):
        """Check if two users are friends or if it's the same user"""
        # Allow connection to self (for testing purposes)
        if user1.id == user2.id:
            print(f"Self-connection detected for user {user1.username}")
            return True
            
        # Original friendship check
        return Friendship.are_friends(user1, user2)
    
    @database_sync_to_async
    def create_message(self, encrypted_content):
        """Create a new message in the database"""
        try:
            return Message.objects.create(
                sender=self.user,
                receiver=self.other_user,
                encrypted_content=encrypted_content
            )
        except Exception:
            return None
    
    @database_sync_to_async
    def update_typing_status(self, is_typing):
        """Update typing status in the database"""
        TypingStatus.set_typing(self.user, self.other_user, is_typing)
    
    @database_sync_to_async
    def mark_message_read(self, message_id):
        """Mark a message as read"""
        try:
            message = Message.objects.get(
                id=message_id,
                sender=self.other_user,
                receiver=self.user
            )
            return message.mark_as_read()
        except Message.DoesNotExist:
            return False
    
    async def _check_for_user_anonymous(self):
        """Anonymous users cannot be connected to server"""
        if self.user.is_anonymous:
            return await self.close()