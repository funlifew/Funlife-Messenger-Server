from django.apps import AppConfig


class FriendshipsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'friendships'
    
    def ready(self):
        """Import signals when app is ready"""
        import friendships.signals #NOQA