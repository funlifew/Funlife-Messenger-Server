from .base import BaseConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from friendships.models import Friendship, FriendshipStatus
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

User = get_user_model()

class FriendConsumer(BaseConsumer):
    """Consumer for friend-related events"""
    
    # Handler methods
    
    async def handle_friend_request(self, data):
        """Handle sending a friend request"""
        username = data.get('username')
        if not username:
            await self.send_json({
                'type': 'error',
                'code': 'missing_username',
                'message': 'Username is required'
            })
            return
            
        # Check if user exists and create friendship
        result = await self.create_friend_request(username)
        
        if result.get('success'):
            friendship = result.get('friendship')
            await self.send_json({
                'type': 'friend_request_sent',
                'friend_username': username,
                'friendship_id': friendship.get('id'),
                'timestamp': timezone.now().isoformat()
            })
            
            # Notify the recipient
            await self.channel_layer.group_send(
                f'user_{friendship.get("friend_id")}',
                {
                    'type': 'friend_request_received',
                    'user_id': str(self.user.id),
                    'username': self.user.username,
                    'friendship_id': friendship.get('id'),
                    'timestamp': timezone.now().isoformat()
                }
            )
        else:
            await self.send_json({
                'type': 'error',
                'code': result.get('code'),
                'message': result.get('message')
            })
    
    async def handle_friend_response(self, data):
        """Handle accepting or rejecting a friend request"""
        friendship_id = data.get('friendship_id')
        action = data.get('action')  # 'accept', 'reject', 'block'
        
        if not friendship_id or not action:
            await self.send_json({
                'type': 'error',
                'code': 'missing_parameters',
                'message': 'Friendship ID and action are required'
            })
            return
            
        # Process the response
        result = await self.process_friend_response(friendship_id, action)
        
        if result.get('success'):
            friendship = result.get('friendship')
            
            # Send response to the requester
            await self.channel_layer.group_send(
                f'user_{friendship.get("user_id")}',
                {
                    'type': 'friend_request_updated',
                    'friendship_id': friendship_id,
                    'status': friendship.get('status'),
                    'username': self.user.username,
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            # Send confirmation to current user
            await self.send_json({
                'type': 'friend_response_sent',
                'friendship_id': friendship_id,
                'action': action,
                'timestamp': timezone.now().isoformat()
            })
        else:
            await self.send_json({
                'type': 'error',
                'code': result.get('code'),
                'message': result.get('message')
            })
    
    async def handle_block_user(self, data):
        """Handle blocking a user"""
        user_id = data.get('user_id')
        
        if not user_id:
            await self.send_json({
                'type': 'error',
                'code': 'missing_user_id',
                'message': 'User ID is required'
            })
            return
            
        # Process the block
        result = await self.block_user(user_id)
        
        if result.get('success'):
            await self.send_json({
                'type': 'user_blocked',
                'user_id': user_id,
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
    def create_friend_request(self, username):
        """Create a new friend request"""
        try:
            # Find the user
            friend = User.objects.filter(username=username).first()
            
            if not friend:
                return {
                    'success': False,
                    'code': 'user_not_found',
                    'message': 'User not found'
                }
            
            # Check if trying to friend self
            if friend == self.user:
                return {
                    'success': False,
                    'code': 'cannot_friend_self',
                    'message': 'You cannot send a friend request to yourself'
                }
            
            # Check if friendship already exists
            existing = Friendship.get_friendship(self.user, friend)
            if existing:
                status = existing.status
                
                if status == FriendshipStatus.ACCEPTED:
                    return {
                        'success': False,
                        'code': 'already_friends',
                        'message': 'You are already friends with this user'
                    }
                elif status == FriendshipStatus.PENDING:
                    if existing.user == self.user:
                        return {
                            'success': False,
                            'code': 'request_already_sent',
                            'message': 'Friend request already sent'
                        }
                    else:
                        return {
                            'success': False,
                            'code': 'request_already_received',
                            'message': 'This user has already sent you a friend request'
                        }
                elif status == FriendshipStatus.BLOCKED:
                    return {
                        'success': False,
                        'code': 'user_blocked',
                        'message': 'Unable to send friend request'
                    }
            
            # Create the friendship
            friendship = Friendship.objects.create(
                user=self.user,
                friend=friend,
                status=FriendshipStatus.PENDING
            )
            
            return {
                'success': True,
                'friendship': {
                    'id': str(friendship.id),
                    'user_id': str(friendship.user.id),
                    'friend_id': str(friendship.friend.id),
                    'status': friendship.status
                }
            }
        
        except Exception as e:
            return {
                'success': False,
                'code': 'request_failed',
                'message': str(e)
            }
    
    @database_sync_to_async
    def process_friend_response(self, friendship_id, action):
        """Process a response to a friend request"""
        try:
            friendship = Friendship.objects.get(id=friendship_id)
            
            # Verify this user is the recipient
            if friendship.friend != self.user:
                return {
                    'success': False,
                    'code': 'not_recipient',
                    'message': 'You are not the recipient of this friend request'
                }
            
            # Process based on action
            if action == 'accept':
                friendship.status = FriendshipStatus.ACCEPTED
                friendship.save()
            elif action == 'reject':
                friendship.status = FriendshipStatus.REJECTED
                friendship.save()
            elif action == 'block':
                friendship.status = FriendshipStatus.BLOCKED
                friendship.save()
            else:
                return {
                    'success': False,
                    'code': 'invalid_action',
                    'message': 'Invalid action specified'
                }
            
            return {
                'success': True,
                'friendship': {
                    'id': str(friendship.id),
                    'user_id': str(friendship.user.id),
                    'friend_id': str(friendship.friend.id),
                    'status': friendship.status
                }
            }
        
        except Friendship.DoesNotExist:
            return {
                'success': False,
                'code': 'friendship_not_found',
                'message': 'Friend request not found'
            }
        except Exception as e:
            return {
                'success': False,
                'code': 'process_failed',
                'message': str(e)
            }
    
    @database_sync_to_async
    def block_user(self, user_id):
        """Block a user"""
        try:
            target_user = User.objects.get(id=user_id)
            
            # Get existing friendship if any
            friendship = Friendship.get_friendship(self.user, target_user)
            
            if friendship:
                # Update existing friendship to blocked
                friendship.status = FriendshipStatus.BLOCKED
                
                # Ensure current user is the blocker
                if friendship.user != self.user:
                    # Swap user and friend to ensure correct blocking direction
                    friendship.user, friendship.friend = friendship.friend, friendship.user
                
                friendship.save()
            else:
                # Create new friendship with blocked status
                friendship = Friendship.objects.create(
                    user=self.user,
                    friend=target_user,
                    status=FriendshipStatus.BLOCKED
                )
            
            return {
                'success': True,
                'friendship_id': str(friendship.id)
            }
        
        except User.DoesNotExist:
            return {
                'success': False,
                'code': 'user_not_found',
                'message': 'User not found'
            }
        except Exception as e:
            return {
                'success': False,
                'code': 'block_failed',
                'message': str(e)
            }
    
    # Channel layer event handlers
    
    async def friend_request_received(self, event):
        """Handle friend request received event"""
        await self.send_json(event)
    
    async def friend_request_updated(self, event):
        """Handle friend request updated event"""
        await self.send_json(event)