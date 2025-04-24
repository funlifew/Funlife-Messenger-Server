from django.apps import AppConfig


class BackupsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backups'
    
    def ready(self):
        """Import signals when app is ready"""
        import backups.signals