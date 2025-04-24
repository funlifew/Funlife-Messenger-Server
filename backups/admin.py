from django.contrib import admin
from .models import Backup

@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    """Admin configuration for Backup model"""
    list_display = ('id', 'user', 'size', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user', 'session', 'encrypted_data', 'checksum', 'size', 'created_at')
    
    def has_add_permission(self, request):
        """Prevent adding backups through admin"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent changing backups through admin"""
        return False