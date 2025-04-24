# backups/api.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Backup
from .utils import BackupGenerator
from .serializers import BackupCreateSerializer, BackupSerializer

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from security_logs.utils import SecurityLogger
from security_logs.models import EventType

import json
import base64

class PrepareBackupView(APIView):
    """API endpoint to prepare backup data"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Generate backup data for the user"""
        try:
            session_id = request.data.get('session_id')
            
            # Generate backup data
            backup_data = BackupGenerator.prepare_backup(request.user, session_id)
            
            # Return data for client to process
            return Response({
                'message': 'Backup data prepared successfully',
                'data': backup_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to prepare backup: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DecryptBackupView(APIView):
    """API endpoint for backup decryption"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Decrypt backup data using provided private key
        
        This is for true end-to-end encryption. The client
        provides their private key to decrypt the backup.
        """
        backup_id = request.data.get('backup_id')
        private_key_pem = request.data.get('private_key')
        
        if not backup_id or not private_key_pem:
            return Response({
                'error': 'Backup ID and private key are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get the backup
            backup = Backup.objects.get(id=backup_id, user=request.user)
            
            # Parse the encrypted payload
            encrypted_payload = json.loads(backup.encrypted_data)
            
            # Check if this is asymmetric encryption
            if 'encrypted_session_key' not in encrypted_payload:
                return Response({
                    'error': 'This backup was not encrypted with a public key'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                # Load private key
                private_key = serialization.load_pem_private_key(
                    private_key_pem.encode('utf-8'),
                    password=None,
                    backend=default_backend()
                )
                
                # Extract components
                encrypted_session_key = base64.b64decode(encrypted_payload['encrypted_session_key'])
                iv = base64.b64decode(encrypted_payload['iv'])
                ciphertext = base64.b64decode(encrypted_payload['ciphertext'])
                
                # Decrypt the session key
                session_key = private_key.decrypt(
                    encrypted_session_key,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
                
                # Decrypt the data with AES
                cipher = Cipher(
                    algorithms.AES(session_key),
                    modes.CBC(iv),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                
                # Decrypt and unpad
                padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
                plaintext = self._unpad(padded_plaintext)
                
                # Parse the JSON data
                backup_data = json.loads(plaintext.decode('utf-8'))
                
                # Log the successful decryption
                SecurityLogger.log_account_event(
                    user=request.user,
                    event_type=EventType.BACKUP_DECRYPT,
                    request=request,
                    details={"backup_id": str(backup.id)}
                )
                
                # Generate HTML
                html_content = self._generate_backup_html(backup_data)
                
                # Return HTML content as a string (client can save it)
                return Response({
                    'message': 'Backup decrypted successfully',
                    'html_content': html_content
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'error': f'Failed to decrypt: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Backup.DoesNotExist:
            return Response({
                'error': 'Backup not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def _unpad(self, padded_data):
        """Remove PKCS#7 padding"""
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]
    
    def _generate_backup_html(self, backup_data):
        """Generate HTML representation of backup data"""
        # Context for template rendering
        context = {
            'user_data': backup_data.get('user', {}),
            'profile_data': backup_data.get('profile', {}),
            'messages': backup_data.get('messages', []),
            'friends': backup_data.get('friends', []),
            'created_at': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            'message_count': len(backup_data.get('messages', [])),
            'friend_count': len(backup_data.get('friends', [])),
        }
        
        # Render the HTML template with the context
        return render_to_string('backups/backup_template.html', context)