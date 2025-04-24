# backups/views.py
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import HttpResponse
from django.utils import timezone
from django.template.loader import render_to_string
from .models import Backup
from .serializers import (
    BackupSerializer,
    BackupCreateSerializer,
    BackupDownloadSerializer
)
from security_logs.utils import SecurityLogger
from security_logs.models import EventType
import hashlib
import json
import base64

class BackupListView(generics.ListAPIView):
    """List all backups for the current user"""
    serializer_class = BackupSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return all backups for the current user"""
        return Backup.objects.filter(user=self.request.user)

class CreateBackupView(generics.CreateAPIView):
    """Create a new backup"""
    serializer_class = BackupCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        """Create backup and log the event"""
        backup = serializer.save()
        
        # Log backup creation
        SecurityLogger.log_account_event(
            user=self.request.user,
            event_type=EventType.BACKUP_CREATE,
            request=self.request,
            details={"backup_id": str(backup.id), "size": backup.size}
        )
        
        return backup
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        backup = self.perform_create(serializer)
        
        return Response({
            "message": "Backup created successfully",
            "backup": BackupSerializer(backup).data
        }, status=status.HTTP_201_CREATED)

class DownloadBackupView(APIView):
    """Download backup data as HTML file"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Process backup download request"""
        serializer = BackupDownloadSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            backup = serializer.backup
            
            try:
                # Decrypt backup data (client would normally do this with their private key)
                # For demonstration, we'll assume the data is just base64 encoded JSON
                try:
                    encrypted_data = backup.encrypted_data
                    # In a real app, you'd handle proper decryption here
                    # For simplicity, we'll just assume it's JSON data
                    backup_data = json.loads(encrypted_data)
                except:
                    return Response({
                        "error": "Could not decrypt backup data"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Generate HTML from backup data
                html_content = self.generate_backup_html(backup_data)
                
                # Log the download
                SecurityLogger.log_account_event(
                    user=request.user,
                    event_type=EventType.BACKUP_DOWNLOAD,
                    request=request,
                    details={"backup_id": str(backup.id)}
                )
                
                # Return HTML content as a downloadable file
                response = HttpResponse(html_content, content_type='text/html')
                response['Content-Disposition'] = f'attachment; filename="funlife_backup_{backup.created_at.strftime("%Y%m%d_%H%M")}.html"'
                return response
                
            except Exception as e:
                return Response({
                    "error": f"Error generating backup: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def generate_backup_html(self, backup_data):
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

class DeleteBackupView(generics.DestroyAPIView):
    """Delete a backup"""
    serializer_class = BackupSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Only allow users to delete their own backups"""
        return Backup.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        """Log deletion and delete the backup"""
        backup_id = str(instance.id)
        instance.delete()
        
        # Log backup deletion
        SecurityLogger.log_account_event(
            user=self.request.user,
            event_type=EventType.BACKUP_DELETE,
            request=self.request,
            details={"backup_id": backup_id}
        )