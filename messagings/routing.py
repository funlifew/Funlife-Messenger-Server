from django.urls import path, re_path
from . import consumers

websocket_urlpatterns = [
    # Use re_path to accept any format for user_id
    re_path(r'ws/(?P<user_id>[^/]+)/', consumers.MessageConsumer.as_asgi()),
]