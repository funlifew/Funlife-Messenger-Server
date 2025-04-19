from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from config.asgi import application
import json
import uuid
import time
from .models import Message, TypingStatus
from friendships.models import Friendship, FriendshipStatus
from utils.encryption import E2EEncryption

User = get_user_model()

class MessageModelTests(TestCase):
    """Test the Message model functionality"""
    
    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='e3[leS1!9rHd',
            is_verified=True
        )
        
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='e3[leS1!9rHd',
            is_verified=True
        )
        
        # Create friendship
        self.friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        # Generate encryption keys
        self.user1_private_key, self.user1.public_key = E2EEncryption.generate_key_pair()
        self.user1.save()
        
        self.user2_private_key, self.user2.public_key = E2EEncryption.generate_key_pair()
        self.user2.save()
        
        # Create a test message
        self.message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            encrypted_content=json.dumps({
                'encrypted_session_key': 'dGVzdGtleQ==',  # base64 "testkey"
                'iv': 'dGVzdGl2',  # base64 "testiv"
                'ciphertext': 'dGVzdGNpcGhlcnRleHQ='  # base64 "testciphertext"
            })
        )
    
    def test_message_creation(self):
        """Test that a message can be created properly"""
        self.assertEqual(self.message.sender, self.user1)
        self.assertEqual(self.message.receiver, self.user2)
        self.assertFalse(self.message.is_read)
        self.assertFalse(self.message.is_delivered)
        self.assertIsNotNone(self.message.created_at)
    
    def test_message_str_representation(self):
        """Test the string representation of a message"""
        expected_str = f"Message from {self.user1.username} to {self.user2.username}"
        self.assertEqual(str(self.message), expected_str)
    
    def test_mark_as_delivered(self):
        """Test marking a message as delivered"""
        self.assertFalse(self.message.is_delivered)
        self.assertIsNone(self.message.delivered_at)
        
        result = self.message.mark_as_delivered()
        
        self.assertTrue(result)
        self.assertTrue(self.message.is_delivered)
        self.assertIsNotNone(self.message.delivered_at)
        
        # Calling again should return False (no change)
        result = self.message.mark_as_delivered()
        self.assertFalse(result)
    
    def test_mark_as_read(self):
        """Test marking a message as read"""
        self.assertFalse(self.message.is_read)
        self.assertIsNone(self.message.read_at)
        
        result = self.message.mark_as_read()
        
        self.assertTrue(result)
        self.assertTrue(self.message.is_read)
        self.assertIsNotNone(self.message.read_at)
        
        # Read should also imply delivered
        self.assertTrue(self.message.is_delivered)
        self.assertIsNotNone(self.message.delivered_at)
        
        # Calling again should return False (no change)
        result = self.message.mark_as_read()
        self.assertFalse(result)
    
    def test_get_conversation(self):
        """Test retrieving a conversation between two users"""
        # Create additional messages
        Message.objects.create(
            sender=self.user2,
            receiver=self.user1,
            encrypted_content=json.dumps({
                'encrypted_session_key': 'dGVzdGtleQ==',
                'iv': 'dGVzdGl2',
                'ciphertext': 'dGVzdGNpcGhlcnRleHQ='
            })
        )
        
        # Get conversation
        conversation = Message.get_conversation(self.user1, self.user2)
        
        # Should return 2 messages
        self.assertEqual(conversation.count(), 2)
    
    def test_get_unread_count(self):
        """Test retrieving the unread message count"""
        # Create additional unread messages
        Message.objects.create(
            sender=self.user2,
            receiver=self.user1,
            encrypted_content=json.dumps({
                'encrypted_session_key': 'dGVzdGtleQ==',
                'iv': 'dGVzdGl2',
                'ciphertext': 'dGVzdGNpcGhlcnRleHQ='
            })
        )
        
        # Check unread count for user1
        unread_count = Message.get_unread_count(self.user1)
        self.assertEqual(unread_count, 1)
        
        # Mark message as read
        message = Message.objects.get(sender=self.user2, receiver=self.user1)
        message.mark_as_read()
        
        # Check count again
        unread_count = Message.get_unread_count(self.user1)
        self.assertEqual(unread_count, 0)
    
    def test_get_conversations_summary(self):
        """Test retrieving conversation summaries"""
        # Create a third user with a message to user1
        user3 = User.objects.create_user(
            username='testuser3',
            email='test3@example.com',
            password='e3[leS1!9rHd',
            is_verified=True
        )
        
        # Create friendship with user3
        Friendship.objects.create(
            user=self.user1,
            friend=user3,
            status=FriendshipStatus.ACCEPTED
        )
        
        # Generate key for user3
        user3_private_key, user3.public_key = E2EEncryption.generate_key_pair()
        user3.save()
        
        # Create message from user3 to user1
        Message.objects.create(
            sender=user3,
            receiver=self.user1,
            encrypted_content=json.dumps({
                'encrypted_session_key': 'dGVzdGtleQ==',
                'iv': 'dGVzdGl2',
                'ciphertext': 'dGVzdGNpcGhlcnRleHQ='
            })
        )
        
        # Get conversation summaries for user1
        summaries = Message.get_conversations_summary(self.user1)
        
        # Should have 2 conversations
        self.assertEqual(len(summaries), 2)
    
    def test_soft_delete(self):
        """Test soft deletion of messages"""
        # Add soft delete fields if they don't exist in your model yet
        if not hasattr(self.message, 'is_deleted'):
            self.skipTest("Soft delete not implemented")
        
        self.assertFalse(self.message.is_deleted)
        self.assertIsNone(self.message.deleted_at)
        
        result = self.message.soft_delete()
        
        self.assertTrue(result)
        self.assertTrue(self.message.is_deleted)
        self.assertIsNotNone(self.message.deleted_at)


class TypingStatusModelTests(TestCase):
    """Test the TypingStatus model functionality"""
    
    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='e3[leS1!9rHd',
            is_verified=True
        )
        
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='e3[leS1!9rHd',
            is_verified=True
        )
        
        # Create friendship
        self.friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
    
    def test_typing_status_creation(self):
        """Test creating a typing status"""
        status = TypingStatus.set_typing(self.user1, self.user2, True)
        
        self.assertIsNotNone(status)
        self.assertEqual(status.user, self.user1)
        self.assertEqual(status.recipient, self.user2)
        self.assertTrue(status.is_typing)
        self.assertIsNotNone(status.timestamp)
    
    def test_typing_status_update(self):
        """Test updating a typing status"""
        # Create initial status
        status = TypingStatus.set_typing(self.user1, self.user2, True)
        timestamp = status.timestamp
        
        # Wait a moment to ensure different timestamp
        time.sleep(0.01)
        
        # Update status
        updated_status = TypingStatus.set_typing(self.user1, self.user2, False)
        
        self.assertEqual(updated_status.id, status.id)  # Same object
        self.assertFalse(updated_status.is_typing)      # Updated value
        self.assertNotEqual(updated_status.timestamp, timestamp)  # Updated timestamp
    
    def test_get_status(self):
        """Test retrieving a typing status"""
        # Create status
        TypingStatus.set_typing(self.user1, self.user2, True)
        
        # Retrieve status
        status = TypingStatus.get_status(self.user1, self.user2)
        
        self.assertIsNotNone(status)
        self.assertTrue(status.is_typing)
        
        # Non-existent status returns None
        status = TypingStatus.get_status(self.user2, self.user1)
        self.assertIsNone(status)
    
    def test_friendship_requirement(self):
        """Test that users must be friends to set typing status"""
        # Create a user with no friendship
        user3 = User.objects.create_user(
            username='testuser3',
            email='test3@example.com',
            password='e3[leS1!9rHd',
            is_verified=True
        )
        
        # Try to set typing status
        status = TypingStatus.set_typing(self.user1, user3, True)
        
        # Should return None (not allowed)
        self.assertIsNone(status)


class MessageAPITests(APITestCase):
    """Test the messaging API endpoints"""
    
    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='e3[leS1!9rHd',
            is_verified=True
        )
        
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='e3[leS1!9rHd',
            is_verified=True
        )
        
        # Create friendship
        self.friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        # Generate encryption keys
        self.user1_private_key, self.user1.public_key = E2EEncryption.generate_key_pair()
        self.user1.save()
        
        self.user2_private_key, self.user2.public_key = E2EEncryption.generate_key_pair()
        self.user2.save()
        
        # Create API client
        self.client = APIClient()
        
        # Create test message
        self.message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            encrypted_content=json.dumps({
                'encrypted_session_key': 'dGVzdGtleQ==',
                'iv': 'dGVzdGl2',
                'ciphertext': 'dGVzdGNpcGhlcnRleHQ='
            })
        )
    
    def test_send_message(self):
        """Test sending a message via API"""
        # Login as user1
        self.client.force_authenticate(user=self.user1)
        
        # Prepare message data
        data = {
            'receiver_id': str(self.user2.id),
            'encrypted_content': json.dumps({
                'encrypted_session_key': 'dGVzdGtleQ==',
                'iv': 'dGVzdGl2',
                'ciphertext': 'dGVzdGNpcGhlcnRleHQ='
            })
        }
        
        # Send message
        url = reverse('messagings:send_message')
        response = self.client.post(url, data, format='json')
        
        # Print response for debugging
        print(f"Send message response: {response.status_code} - {response.data}")
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'Message sent successfully')
    
    def test_get_conversation(self):
        """Test retrieving a conversation via API"""
        # Login as user1
        self.client.force_authenticate(user=self.user1)
        
        # Get conversation - update to match your actual URL pattern
        url = reverse('messagings:conversation', kwargs={'user_id': str(self.user2.id)})
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_mark_message_read(self):
        """Test marking a message as read via API"""
        # Login as user2 (receiver)
        self.client.force_authenticate(user=self.user2)
        
        # Mark message as read
        url = reverse('messagings:mark_read', args=[str(self.message.id)])
        response = self.client.post(url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify message is marked as read
        self.message.refresh_from_db()
        self.assertTrue(self.message.is_read)
    
    def test_mark_all_read(self):
        """Test marking all messages as read via API"""
        # Create additional message
        Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            encrypted_content=json.dumps({
                'encrypted_session_key': 'dGVzdGtleQ==',
                'iv': 'dGVzdGl2',
                'ciphertext': 'dGVzdGNpcGhlcnRleHQ='
            })
        )
        
        # Login as user2 (receiver)
        self.client.force_authenticate(user=self.user2)
        
        # Mark all messages as read - update to match your actual URL pattern
        url = reverse('messagings:mark_all_read', kwargs={'user_id': str(self.user1.id)})
        response = self.client.post(url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all messages are marked as read
        unread_count = Message.objects.filter(
            sender=self.user1,
            receiver=self.user2,
            is_read=False
        ).count()
        self.assertEqual(unread_count, 0)
    
    def test_get_conversation_summaries(self):
        """Test retrieving conversation summaries via API"""
        # Login as user1
        self.client.force_authenticate(user=self.user1)
        
        # Get conversation summaries
        url = reverse('messagings:conversation_summaries')
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_update_typing_status(self):
        """Test updating typing status via API"""
        # Login as user1
        self.client.force_authenticate(user=self.user1)
        
        # Update typing status
        data = {
            'recipient_id': str(self.user2.id),
            'is_typing': True
        }
        url = reverse('messagings:update_typing_status')
        response = self.client.post(url, data, format='json')
        
        # Print response for debugging
        print(f"Update typing status response: {response.status_code} - {response.data}")
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify typing status is updated
        status_obj = TypingStatus.get_status(self.user1, self.user2)
        self.assertIsNotNone(status_obj)
        self.assertTrue(status_obj.is_typing)
    
    def test_get_typing_status(self):
        """Test retrieving typing status via API"""
        # Set typing status
        TypingStatus.set_typing(self.user1, self.user2, True)
        
        # Login as user2
        self.client.force_authenticate(user=self.user2)
        
        # Get typing status - update to match your actual URL pattern
        url = reverse('messagings:get_typing_status', kwargs={'user_id': str(self.user1.id)})
        response = self.client.get(url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('is_typing', response.data)
        self.assertTrue(response.data['is_typing'])
    
    def test_generate_keys(self):
        """Test generating encryption keys via API"""
        # Create a user without keys
        user3 = User.objects.create_user(
            username='testuser3',
            email='test3@example.com',
            password='e3[leS1!9rHd',
            is_verified=True
        )
        
        # Login as user3
        self.client.force_authenticate(user=user3)
        
        # Generate keys
        url = reverse('messagings:generate_keys')
        response = self.client.post(url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('private_key', response.data)
        self.assertIn('message', response.data)
        
        # Verify user has a public key
        user3.refresh_from_db()
        self.assertIsNotNone(user3.public_key)
    
    def test_get_public_key(self):
        """Test retrieving a user's public key via API"""
        # Login as user1
        self.client.force_authenticate(user=self.user1)
        
        # Get user2's public key
        data = {
            'user_id': str(self.user2.id)
        }
        url = reverse('messagings:get_public_key')
        response = self.client.post(url, data, format='json')
        
        # Print response for debugging
        print(f"Get public key response: {response.status_code} - {response.data}")
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('public_key', response.data)
        self.assertEqual(response.data['public_key'], self.user2.public_key)
    
    def test_delete_message(self):
        """Test deleting a message via API"""
        # Skip if soft delete not implemented
        if not hasattr(Message, 'soft_delete'):
            self.skipTest("Soft delete not implemented")
            
        # Login as sender
        self.client.force_authenticate(user=self.user1)
        
        # Delete message
        url = reverse('messagings:delete_message', args=[str(self.message.id)])
        response = self.client.post(url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify message is soft deleted
        self.message.refresh_from_db()
        self.assertTrue(self.message.is_deleted)


class WebSocketTests(TransactionTestCase):
    """Test the WebSocket functionality"""
    
    @database_sync_to_async
    def create_user(self, username, email, password):
        """Create a test user"""
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_verified=True
        )
        return user
    
    @database_sync_to_async
    def create_friendship(self, user1, user2):
        """Create a friendship between users"""
        friendship = Friendship.objects.create(
            user=user1,
            friend=user2,
            status=FriendshipStatus.ACCEPTED
        )
        return friendship
    
    @database_sync_to_async
    def generate_keys(self, user):
        """Generate encryption keys for a user"""
        private_key, public_key = E2EEncryption.generate_key_pair()
        user.public_key = public_key
        user.save()
        return private_key
    
    @database_sync_to_async
    def get_message(self, sender, receiver):
        """Get the latest message between two users"""
        return Message.objects.filter(sender=sender, receiver=receiver).order_by('-created_at').first()
    
    @database_sync_to_async
    def get_typing_status(self, user, recipient):
        """Get the typing status between two users"""
        return TypingStatus.get_status(user, recipient)
    
    async def test_websocket_connection(self):
        """Test WebSocket connection and messaging"""
        # Create test users
        user1 = await self.create_user('wsuser1', 'ws1@example.com', 'e3[leS1!9rHd')
        user2 = await self.create_user('wsuser2', 'ws2@example.com', 'e3[leS1!9rHd')
        
        # Create friendship
        await self.create_friendship(user1, user2)
        
        # Generate keys
        await self.generate_keys(user1)
        await self.generate_keys(user2)
        
        # Connect to WebSocket as user1
        communicator1 = WebsocketCommunicator(
            application,
            f"ws/{user2.id}/?token=dummytoken"  # In real app, use JWT token
        )
        communicator1.scope["user"] = user1  # Inject authenticated user
        connected1, _ = await communicator1.connect()
        self.assertTrue(connected1)
        
        # Connect to WebSocket as user2
        communicator2 = WebsocketCommunicator(
            application,
            f"ws/{user1.id}/?token=dummytoken"  # In real app, use JWT token
        )
        communicator2.scope["user"] = user2  # Inject authenticated user
        connected2, _ = await communicator2.connect()
        self.assertTrue(connected2)
        
        # Send a message from user1 to user2
        await communicator1.send_json_to({
            'type': 'message',
            'encrypted_content': json.dumps({
                'encrypted_session_key': 'dGVzdGtleQ==',
                'iv': 'dGVzdGl2',
                'ciphertext': 'dGVzdGNpcGhlcnRleHQ='
            })
        })
        
        # Receive message on user2's connection
        response = await communicator2.receive_json_from(timeout=2)
        self.assertEqual(response['type'], 'message')
        self.assertEqual(response['sender_id'], str(user1.id))
        self.assertEqual(response['receiver_id'], str(user2.id))
        
        # Verify message saved to database
        message = await self.get_message(user1, user2)
        self.assertIsNotNone(message)
        
        # Test typing status
        await communicator1.send_json_to({
            'type': 'typing',
            'is_typing': True
        })
        
        # Receive typing status on user2's connection
        response = await communicator2.receive_json_from(timeout=2)
        self.assertEqual(response['type'], 'typing')
        self.assertEqual(response['user_id'], str(user1.id))
        self.assertTrue(response['is_typing'])
        
        # Verify typing status saved to database
        typing_status = await self.get_typing_status(user1, user2)
        self.assertIsNotNone(typing_status)
        self.assertTrue(typing_status.is_typing)
        
        # Test mark as read
        await communicator2.send_json_to({
            'type': 'read',
            'message_id': str(message.id)
        })
        
        # Receive read receipt on user1's connection
        response = await communicator1.receive_json_from(timeout=2)
        self.assertEqual(response['type'], 'read_receipt')
        self.assertEqual(response['message_id'], str(message.id))
        self.assertEqual(response['user_id'], str(user2.id))
        
        # Close connections
        await communicator1.disconnect()
        await communicator2.disconnect()