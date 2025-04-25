from .base import BaseConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from backups.models import Backup
from django.db.models import Q

class BackupConsumer(BaseConsumer):
    """Consumer for backup-related events"""
    
    # Handler methods
    
    async def handle_prepare_backup(self, data):
        """Handle preparing a backup"""
        session_id = data.get('session_id')
        
        if not session_id:
            await self.send_json({
                'type': 'error',
                'code': 'missing_session_id',
                'message': 'Session ID is required'
            })
            return
            
        # Start backup preparation
        await self.send_json({
            'type': 'backup_preparation_started',
            'timestamp': timezone.now().isoformat()
        })
        
        # Prepare backup data
        result = await self.prepare_backup_data(session_id)
        
        if result.get('success'):
            await self.send_json({
                'type': 'backup_preparation_completed',
                'data': result.get('data'),
                'checksum': result.get('checksum'),
                'size': result.get('size'),
                'timestamp': timezone.now().isoformat()
            })
        else:
            await self.send_json({
                'type': 'error',
                'code': result.get('code'),
                'message': result.get('message')
            })
    
    async def handle_create_backup(self, data):
        """Handle creating a backup"""
        encrypted_data = data.get('encrypted_data')
        checksum = data.get('checksum')
        size = data.get('size')
        session_id = data.get('session_id')
        
        if not all([encrypted_data, checksum, size, session_id]):
            await self.send_json({
                'type': 'error',
                'code': 'missing_parameters',
                'message': 'Required parameters missing'
            })
            return
            
        # Create backup
        result = await self.create_backup(encrypted_data, checksum, size, session_id)
        
        if result.get('success'):
            await self.send_json({
                'type': 'backup_created',
                'backup_id': result.get('backup_id'),
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
    def prepare_backup_data(self, session_id):
        """Prepare backup data"""
        try:
            from backups.utils import BackupGenerator
            
            # Generate backup data
            backup_data = BackupGenerator.prepare_backup(self.user, session_id)
            
            return {
                'success': True,
                'data': backup_data.get('encrypted_data'),
                'checksum': backup_data.get('checksum'),
                'size': backup_data.get('size')
            }
        except Exception as e:
            return {
                'success': False,
                'code': 'preparation_failed',
                'message': str(e)
            }
    
    @database_sync_to_async
    def create_backup(self, encrypted_data, checksum, size, session_id):
        """Create a backup in the database"""
        try:
            from user_sessions.models import UserSession
            
            try:
                session = UserSession.objects.get(id=session_id, user=self.user)
            except UserSession.DoesNotExist:
                return {
                    'success': False,
                    'code': 'session_not_found',
                    'message': 'Session not found'
                }
            
            # Create backup
            backup = Backup.objects.create(
                user=self.user,
                session=session,
                encrypted_data=encrypted_data,
                checksum=checksum,
                size=size
            )
            
            return {
                'success': True,
                'backup_id': str(backup.id)
            }
        except Exception as e:
            return {
                'success': False,
                'code': 'creation_failed',
                'message': str(e)
            }