from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from backups.models import Backup
from security_logs.models import SecurityLog, EventType

class Command(BaseCommand):
    help = 'Clean up old backups to save storage space'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete backups older than this many days'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only show what would be deleted without actually deleting'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find old backups
        old_backups = Backup.objects.filter(created_at__lt=cutoff_date)
        count = old_backups.count()
        
        self.stdout.write(f"Found {count} backups older than {days} days")
        
        if count == 0:
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no backups will be deleted"))
            for backup in old_backups:
                self.stdout.write(f"Would delete: {backup} (created {backup.created_at})")
        else:
            # Delete backups and log the action
            for backup in old_backups:
                user = backup.user
                backup_id = str(backup.id)
                
                # Log the deletion
                SecurityLog.log_event(
                    event_type=EventType.BACKUP_DELETE,
                    user=user,
                    severity=1,  # WARNING level
                    details={
                        'reason': 'automatic_cleanup',
                        'backup_id': backup_id,
                        'age_days': days
                    }
                )
                
                # Delete the backup
                backup.delete()
                
                self.stdout.write(f"Deleted: {backup_id} (user: {user.username})")
            
            self.stdout.write(self.style.SUCCESS(f"Successfully deleted {count} old backups"))