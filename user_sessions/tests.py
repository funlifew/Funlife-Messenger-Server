# user_sessions/tests.py
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import UserSession
from datetime import timedelta
import json
import uuid

User = get_user_model()

class UserSessionModelTests(TestCase):
    """Test the UserSession model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='e3[leS1!9rHd',
            is_verified=True
        )
        
        # Create a sample session
        self.session = UserSession.objects.create(
            user=self.user,
            ip_address='127.0.0.1',
            device_info=json.dumps({
                'browser': 'Chrome',
                'os': 'Windows',
                'name': 'Chrome on Windows'
            })
        )
    
    def test_session_creation(self):
        """Test creating a session"""
        self.assertEqual(self.session.user, self.user)
        self.assertEqual(self.session.ip_address, '127.0.0.1')
        self.assertTrue(self.session.is_active)
        self.assertIsNotNone(self.session.expires_at)
        
        # Test device_name property
        self.assertEqual(self.session.device_name, 'Chrome on Windows')
    
    def test_is_expired(self):
        """Test the is_expired property"""
        # Session should not be expired yet
        self.assertFalse(self.session.is_expired)
        
        # Set expiration in the past
        self.session.expires_at = timezone.now() - timedelta(days=1)
        self.session.save()
        
        # Session should now be expired
        self.assertTrue(self.session.is_expired)
    
    def test_update_activity(self):
        """Test updating the last activity timestamp"""
        old_activity = self.session.last_activity
        
        # Wait a moment to ensure time difference
        import time
        time.sleep(0.1)
        
        # Update activity
        self.session.update_activity()
        
        # Check that timestamp was updated
        self.assertNotEqual(self.session.last_activity, old_activity)
    
    def test_extend_session(self):
        """Test extending a session"""
        old_expires = self.session.expires_at
        
        # Extend by 10 days
        self.session.extend_session(days=10)
        
        # Check new expiration time (should be about 10 days later)
        self.assertGreater(self.session.expires_at, old_expires + timedelta(days=9))
    
    def test_invalidate(self):
        """Test invalidating a session"""
        self.assertTrue(self.session.is_active)
        
        # Invalidate session
        self.session.invalidate()
        
        # Check that session is no longer active
        self.assertFalse(self.session.is_active)
    
    def test_get_active_sessions(self):
        """Test getting active sessions for a user"""
        # Create another active session
        UserSession.objects.create(
            user=self.user,
            ip_address='192.168.1.1',
            device_info=json.dumps({'browser': 'Firefox'})
        )
        
        # Create an inactive session
        inactive = UserSession.objects.create(
            user=self.user,
            ip_address='10.0.0.1',
            device_info=json.dumps({'browser': 'Safari'})
        )
        inactive.is_active = False
        inactive.save()
        
        # Create an expired session
        expired = UserSession.objects.create(
            user=self.user,
            ip_address='8.8.8.8',
            device_info=json.dumps({'browser': 'Edge'})
        )
        expired.expires_at = timezone.now() - timedelta(days=1)
        expired.save()
        
        # Get active sessions
        active_sessions = UserSession.get_active_sessions(self.user)
        
        # Should have 2 active sessions
        self.assertEqual(active_sessions.count(), 2)
        
        # Check that inactive and expired sessions are not included
        self.assertNotIn(inactive, active_sessions)
        self.assertNotIn(expired, active_sessions)

class UserSessionAPITests(TestCase):
    """Test the user session API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='e3[leS1!9rHd',
            is_verified=True
        )
        
        # Create a sample session
        self.session = UserSession.objects.create(
            user=self.user,
            ip_address='127.0.0.1',
            device_info=json.dumps({
                'browser': 'Chrome',
                'os': 'Windows',
                'name': 'Chrome on Windows'
            })
        )
        
        # Create another session for the same user
        self.session2 = UserSession.objects.create(
            user=self.user,
            ip_address='192.168.1.1',
            device_info=json.dumps({
                'browser': 'Firefox',
                'os': 'Linux',
                'name': 'Firefox on Linux'
            })
        )
        
        # Create an API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_list_sessions(self):
        """Test listing user sessions"""
        url = reverse('user_sessions:session_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Verify session data is present
        session_ids = [s['id'] for s in response.data]
        self.assertIn(str(self.session.id), session_ids)
        self.assertIn(str(self.session2.id), session_ids)
    
    def test_get_session_detail(self):
        """Test retrieving a specific session"""
        url = reverse('user_sessions:session_detail', args=[self.session.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.session.id))
        self.assertEqual(response.data['device_name'], 'Chrome on Windows')
    
    def test_update_session(self):
        """Test updating a session"""
        url = reverse('user_sessions:session_detail', args=[self.session.id])
        
        # Update the session's active status
        data = {'is_active': False}
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_active'])
        
        # Verify in database
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_active)
    
    def test_delete_session(self):
        """Test deleting (invalidating) a session"""
        url = reverse('user_sessions:session_detail', args=[self.session.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify session is invalidated, not deleted
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_active)
    
    def test_invalidate_all_sessions(self):
        """Test invalidating all sessions except current"""
        url = reverse('user_sessions:invalidate_all')
        
        # Invalidate all except session2
        data = {'current_session_id': str(self.session2.id)}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify session1 is invalidated
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_active)
        
        # Verify session2 is still active
        self.session2.refresh_from_db()
        self.assertTrue(self.session2.is_active)
    
    def test_extend_session(self):
        """Test extending a session"""
        url = reverse('user_sessions:extend_session')
        
        # Capture original expiration
        original_expires = self.session.expires_at
        
        # Extend session by 15 days
        data = {
            'session_id': str(self.session.id),
            'days': 15
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify session is extended
        self.session.refresh_from_db()
        self.assertGreater(
            self.session.expires_at,
            original_expires + timedelta(days=14)
        )
    
    def test_update_activity(self):
        """Test updating a session's activity timestamp"""
        url = reverse('user_sessions:update_activity')
        
        # Capture original activity timestamp
        original_activity = self.session.last_activity
        
        # Wait a moment to ensure timestamp difference
        import time
        time.sleep(0.1)
        
        # Update activity
        data = {'session_id': str(self.session.id)}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify activity timestamp is updated
        self.session.refresh_from_db()
        self.assertNotEqual(self.session.last_activity, original_activity)