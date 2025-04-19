from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from urllib.parse import parse_qs

User = get_user_model()

class JWTMiddleware(BaseMiddleware):
    """Custom Middleware for authentication with JWT"""
    async def __call__(self, scope, receive, send):
        """Process the scope and attach the user"""
        # Extract query parameters
        query_params = parse_qs(scope['query_string'].decode())
        token = query_params.get("token", [None])[0]
        
        if token:
            # Verify and authenticate the token
            try:
                scope['user'] = await self.get_user_from_token(token)
            except (InvalidToken, TokenError):
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        """Get the user from the JWT token"""
        try:
            # Get the user's ID from the token
            validated_token = AccessToken(token)
            user_id = validated_token['user_id']
            
            # Get the user from the database
            return User.objects.get(id=user_id)
        except (User.DoesNotExist, InvalidToken):
            return AnonymousUser()
