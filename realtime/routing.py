from django.urls import path, re_path
from .consumers.profile import ProfileConsumer
from .consumers.friend import FriendConsumer
from .consumers.message import MessageConsumer
from .consumers.notification import NotificationConsumer
from .consumers.backup import BackupConsumer
from .consumers.session import SessionConsumer
from .consumers.security import SecurityConsumer

websocket_urlpatterns = [
    # Profile WebSocket
    path('ws/profile/', ProfileConsumer.as_asgi()),
    
    # Friend WebSocket
    path('ws/friends/', FriendConsumer.as_asgi()),
    
    # Message WebSocket - requires target user ID
    re_path(r'ws/messages/(?P<user_id>[^/]+)/', MessageConsumer.as_asgi()),
    
    # Notification WebSocket
    path('ws/notifications/', NotificationConsumer.as_asgi()),
    
    # Backup WebSocket
    path('ws/backups/', BackupConsumer.as_asgi()),
    
    # Session WebSocket
    path('ws/sessions/', SessionConsumer.as_asgi()),
    
    # Security WebSocket
    path('ws/security/', SecurityConsumer.as_asgi()),
]