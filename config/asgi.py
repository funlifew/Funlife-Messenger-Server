"""
ASGI config for config project.
"""

import os
import django
from django.core.asgi import get_asgi_application

# Set the Django settings module before importing any other Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()  # Configure Django settings

# Now import the rest of your modules
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from messagings.middlewares import JWTAuthMiddleware
import messagings.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(
            URLRouter(
                messagings.routing.websocket_urlpatterns
            )
        )
    ),
})