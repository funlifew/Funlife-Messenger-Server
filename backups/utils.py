# backups/utils.py
import json
import hashlib
import base64
from django.contrib.auth import get_user_model
from messagings.models import Message
from friendships.models import Friendship
from profiles.models import Profile
from django.db.models import Q
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os

User = get_user_model()

class BackupGenerator:
    """Utility class for generating user backup data"""
    
    @staticmethod
    def collect_user_data(user):
        """Collect all user data for backup"""
        # Basic user data
        user_data = {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'is_verified': user.is_verified,
            'created_at': user.created_at.isoformat(),
            'updated_at': user.updated_at.isoformat(),
        }
        
        # Get user profile
        try:
            profile = user.profile
            profile_data = {
                'id': str(profile.id),
                'display_name': profile.display_name or user.username,
                'status': profile.status,
                'bio': profile.bio,
                'created_at': profile.created_at.isoformat(),
                'updated_at': profile.updated_at.isoformat(),
            }
        except Profile.DoesNotExist:
            profile_data = {}
        
        # Get friends
        friends_data = []
        friends = Friendship.get_user_friends(user)
        
        for friend in friends:
            # Get friendship
            friendship = Friendship.get_friendship(user, friend)
            if not friendship:
                continue
                
            # Get friend's profile
            try:
                friend_profile = friend.profile
                profile_info = {
                    'display_name': friend_profile.display_name or friend.username,
                    'status': friend_profile.status,
                    'bio': friend_profile.bio
                }
            except Profile.DoesNotExist:
                profile_info = {}
            
            friend_data = {
                'id': str(friend.id),
                'username': friend.username,
                'status': friendship.status,
                'created_at': friendship.created_at.isoformat(),
                'profile': profile_info
            }
            
            friends_data.append(friend_data)
        
        # Get messages (both sent and received)
        messages_data = []
        messages = Message.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).order_by('created_at')
        
        for message in messages:
            message_data = {
                'id': str(message.id),
                'sender': message.sender.username,
                'receiver': message.receiver.username,
                'encrypted_content': message.encrypted_content,
                'is_read': message.is_read,
                'is_delivered': message.is_delivered,
                'created_at': message.created_at.isoformat(),
            }
            
            # Add delivery/read timestamps if available
            if message.delivered_at:
                message_data['delivered_at'] = message.delivered_at.isoformat()
            
            if message.read_at:
                message_data['read_at'] = message.read_at.isoformat()
            
            messages_data.append(message_data)
        
        # Compile all data
        backup_data = {
            'user': user_data,
            'profile': profile_data,
            'friends': friends_data,
            'messages': messages_data
        }
        
        return backup_data
    
    @staticmethod
    def encrypt_backup_data(data, public_key=None):
        """
        Encrypt backup data for the user
        
        Args:
            data (dict): The data to encrypt
            public_key (str): User's public key in PEM format
        
        Returns:
            str: JSON string with encrypted data
        """
        # Convert data to JSON string
        data_json = json.dumps(data)
        data_bytes = data_json.encode('utf-8')
        
        if not public_key and hasattr(User, 'public_key'):
            # Try to get the user's public key if not provided
            public_key = User.public_key
        
        if public_key:
            # Use asymmetric encryption if public key is available
            try:
                # Load public key
                public_key_obj = serialization.load_pem_public_key(
                    public_key.encode('utf-8'),
                    backend=default_backend()
                )
                
                # Generate a random AES session key
                session_key = os.urandom(32)  # 256-bit key
                
                # Generate a random IV for AES
                iv = os.urandom(16)  # 128-bit IV
                
                # Use AES to encrypt the data
                cipher = Cipher(
                    algorithms.AES(session_key),
                    modes.CBC(iv),
                    backend=default_backend()
                )
                encryptor = cipher.encryptor()
                
                # Pad the data to a multiple of AES block size (16 bytes)
                padded_data = BackupGenerator._pad(data_bytes)
                
                # Encrypt the data
                ciphertext = encryptor.update(padded_data) + encryptor.finalize()
                
                # Encrypt the session key with the public key
                encrypted_session_key = public_key_obj.encrypt(
                    session_key,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
                
                # Encode binary data as base64 for JSON compatibility
                encrypted_payload = {
                    'encrypted_session_key': base64.b64encode(encrypted_session_key).decode('utf-8'),
                    'iv': base64.b64encode(iv).decode('utf-8'),
                    'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
                }
                
                return json.dumps(encrypted_payload)
            
            except Exception as e:
                # Fall back to AES-only encryption if public key encryption fails
                print(f"Error with public key encryption: {str(e)}")
                return BackupGenerator._encrypt_with_aes_only(data_bytes)
        else:
            # Use AES-only encryption if no public key is available
            return BackupGenerator._encrypt_with_aes_only(data_bytes)
    
    @staticmethod
    def _encrypt_with_aes_only(data_bytes):
        """Encrypt data using AES with a derived key"""
        # Generate a random salt
        salt = os.urandom(16)
        
        # Derive a key from a fixed passphrase (in production, use a strong user-provided passphrase)
        # WARNING: This is a simplified approach. In production, use a proper key derivation function
        key = hashlib.pbkdf2_hmac('sha256', b'funlife-backup-secret', salt, 100000, 32)
        
        # Generate random IV
        iv = os.urandom(16)
        
        # Create AES cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Pad the data
        padded_data = BackupGenerator._pad(data_bytes)
        
        # Encrypt the data
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # Create payload
        encrypted_payload = {
            'method': 'aes-only',
            'salt': base64.b64encode(salt).decode('utf-8'),
            'iv': base64.b64encode(iv).decode('utf-8'),
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
        }
        
        return json.dumps(encrypted_payload)
    
    @staticmethod
    def _pad(data):
        """PKCS#7 padding for data"""
        block_size = 16
        padding_length = block_size - (len(data) % block_size)
        padding = bytes([padding_length] * padding_length)
        return data + padding
    
    @staticmethod
    def _unpad(padded_data):
        """Remove PKCS#7 padding"""
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]
    
    @staticmethod
    def calculate_checksum(data_str):
        """Calculate SHA-256 checksum of data"""
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
    
    @staticmethod
    def prepare_backup(user, session_id=None):
        """
        Prepare backup data for a user
        
        Returns:
            dict: Backup data ready for API submission
        """
        # Collect user data
        backup_data = BackupGenerator.collect_user_data(user)
        
        # Encrypt data (with real encryption)
        encrypted_data = BackupGenerator.encrypt_backup_data(backup_data, user.public_key if hasattr(user, 'public_key') else None)
        
        # Calculate size and checksum
        size = len(encrypted_data.encode('utf-8'))
        checksum = BackupGenerator.calculate_checksum(encrypted_data)
        
        return {
            'encrypted_data': encrypted_data,
            'size': size,
            'checksum': checksum,
            'session_id': session_id
        }