"""
ASGI config for config project.
"""

import os
import django

# Set the Django settings module before importing any other Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()  # <-- Add this line to configure Django settings

# Now import the rest of your modules
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from messagings.middlewares import JWTMiddleware
import messagings.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        JWTMiddleware(
            URLRouter(
                messagings.routing.websocket_urlpatterns
            )
        )
    ),
})