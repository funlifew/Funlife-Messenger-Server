from .base import BaseConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q
from messagings.models import Message, TypingStatus
from friendships.models import Friendship
from django.contrib.auth import get_user_model

User = get_user_model()

class MessageConsumer(BaseConsumer):
    """Consumer for message-related events"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        await super().connect()
        
        if not hasattr(self, 'user') or self.user.is_anonymous:
            return
        
        # Get the target user ID from URL
        self.target_user_id = self.scope['url_route']['kwargs'].get('user_id')
        
        if not self.target_user_id:
            await self.send_json({
                'type': 'error',
                'code': 'missing_user_id',
                'message': 'Target user ID is required'
            })
            await self.close(code=4004)
            return
        
        # Check if target user exists
        target_user = await self.get_user_by_id(self.target_user_id)
        if not target_user:
            await self.send_json({
                'type': 'error',
                'code': 'user_not_found',
                'message': 'Target user not found'
            })
            await self.close(code=4004)
            return
        
        # Check if users are friends (unless it's self)
        if str(self.user.id) != self.target_user_id:
            are_friends = await self.check_friendship(self.target_user_id)
            if not are_friends:
                await self.send_json({
                    'type': 'error',
                    'code': 'not_friends',
                    'message': 'You are not friends with this user'
                })
                await self.close(code=4004)
                return
        
        # Create conversation group
        self.conversation_group_name = self._get_conversation_group_name(
            str(self.user.id), 
            self.target_user_id
        )
        
        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        
        # Mark messages as delivered
        await self.mark_messages_delivered()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave conversation group
        if hasattr(self, 'conversation_group_name'):
            await self.channel_layer.group_discard(
                self.conversation_group_name,
                self.channel_name
            )
            
        # Clear typing status
        if hasattr(self, 'target_user_id'):
            await self.update_typing_status(False)
            
        await super().disconnect(close_code)
    
    # Handler methods
    
    async def handle_message(self, data):
        """Handle sending a new message"""
        encrypted_content = data.get('encrypted_content')
        
        if not encrypted_content:
            await self.send_json({
                'type': 'error',
                'code': 'missing_content',
                'message': 'Encrypted content is required'
            })
            return
        
        # Create message in database
        result = await self.create_message(encrypted_content)
        
        if result.get('success'):
            message = result.get('message')
            
            # Notify conversation group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message.get('id'),
                    'sender_id': str(self.user.id),
                    'sender_username': self.user.username,
                    'receiver_id': self.target_user_id,
                    'encrypted_content': encrypted_content,
                    'created_at': message.get('created_at')
                }
            )
        else:
            await self.send_json({
                'type': 'error',
                'code': result.get('code'),
                'message': result.get('message')
            })
    
    async def handle_typing(self, data):
        """Handle typing status update"""
        is_typing = data.get('is_typing', False)
        
        # Update typing status in database
        await self.update_typing_status(is_typing)
        
        # Notify conversation group
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'typing_status',
                'user_id': str(self.user.id),
                'username': self.user.username,
                'is_typing': is_typing,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def handle_read(self, data):
        """Handle marking a message as read"""
        message_id = data.get('message_id')
        
        if not message_id:
            await self.send_json({
                'type': 'error',
                'code': 'missing_message_id',
                'message': 'Message ID is required'
            })
            return
        
        # Mark message as read in database
        result = await self.mark_message_read(message_id)
        
        if result.get('success'):
            # Notify conversation group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'read_receipt',
                    'message_id': message_id,
                    'user_id': str(self.user.id),
                    'username': self.user.username,
                    'timestamp': timezone.now().isoformat()
                }
            )
        else:
            await self.send_json({
                'type': 'error',
                'code': result.get('code'),
                'message': result.get('message')
            })
    
    async def handle_delete(self, data):
        """Handle deleting a message"""
        message_id = data.get('message_id')
        
        if not message_id:
            await self.send_json({
                'type': 'error',
                'code': 'missing_message_id',
                'message': 'Message ID is required'
            })
            return
        
        # Delete message in database
        result = await self.delete_message(message_id)
        
        if result.get('success'):
            # Notify conversation group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id,
                    'user_id': str(self.user.id),
                    'username': self.user.username,
                    'timestamp': timezone.now().isoformat()
                }
            )
        else:
            await self.send_json({
                'type': 'error',
                'code': result.get('code'),
                'message': result.get('message')
            })
    
    # Database methods
    
    @database_sync_to_async
    def get_user_by_id(self, user_id):
        """Get a user by ID"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @database_sync_to_async
    def check_friendship(self, user_id):
        """Check if users are friends"""
        try:
            other_user = User.objects.get(id=user_id)
            return Friendship.are_friends(self.user, other_user)
        except User.DoesNotExist:
            return False
    
    @database_sync_to_async
    def create_message(self, encrypted_content):
        """Create a new message"""
        try:
            target_user = User.objects.get(id=self.target_user_id)
            
            # Create message
            message = Message.objects.create(
                sender=self.user,
                receiver=target_user,
                encrypted_content=encrypted_content
            )
            
            return {
                'success': True,
                'message': {
                    'id': str(message.id),
                    'created_at': message.created_at.isoformat()
                }
            }
        except User.DoesNotExist:
            return {
                'success': False,
                'code': 'user_not_found',
                'message': 'Target user not found'
            }
        except Exception as e:
            return {
                'success': False,
                'code': 'message_creation_failed',
                'message': str(e)
            }
    
    @database_sync_to_async
    def update_typing_status(self, is_typing):
        """Update typing status"""
        try:
            target_user = User.objects.get(id=self.target_user_id)
            TypingStatus.set_typing(self.user, target_user, is_typing)
            return True
        except Exception:
            return False
    
    @database_sync_to_async
    def mark_message_read(self, message_id):
        """Mark a message as read"""
        try:
            message = Message.objects.get(
                id=message_id,
                receiver=self.user
            )
            
            success = message.mark_as_read()
            
            return {
                'success': success,
                'timestamp': timezone.now().isoformat() if success else None
            }
        except Message.DoesNotExist:
            return {
                'success': False,
                'code': 'message_not_found',
                'message': 'Message not found'
            }
        except Exception as e:
            return {
                'success': False,
                'code': 'mark_read_failed',
                'message': str(e)
            }
    
    @database_sync_to_async
    def delete_message(self, message_id):
        """Delete a message"""
        try:
            # Find message sent by this user
            message = Message.objects.get(
                id=message_id,
                sender=self.user
            )
            
            # Use soft delete if available
            if hasattr(message, 'soft_delete'):
                success = message.soft_delete()
            else:
                message.delete()
                success = True
            
            return {
                'success': success
            }
        except Message.DoesNotExist:
            return {
                'success': False,
                'code': 'message_not_found',
                'message': 'Message not found or you are not the sender'
            }
        except Exception as e:
            return {
                'success': False,
                'code': 'delete_failed',
                'message': str(e)
            }
    
    @database_sync_to_async
    def mark_messages_delivered(self):
        """Mark messages as delivered when connection is established"""
        try:
            target_user = User.objects.get(id=self.target_user_id)
            
            # Find undelivered messages
            undelivered = Message.objects.filter(
                sender=target_user,
                receiver=self.user,
                is_delivered=False
            )
            
            # Mark all as delivered
            for message in undelivered:
                message.mark_as_delivered()
                
            return True
        except Exception:
            return False
    
    # Utility methods
    
    def _get_conversation_group_name(self, user1_id, user2_id):
        """Get a consistent group name for a conversation between two users"""
        # Sort IDs to ensure the same group name regardless of who initiates
        user_ids = sorted([user1_id, user2_id])
        return f'conversation_{user_ids[0]}_{user_ids[1]}'
    
    # Channel layer event handlers
    
    async def chat_message(self, event):
        """Handle chat message event from channel layer"""
        await self.send_json(event)