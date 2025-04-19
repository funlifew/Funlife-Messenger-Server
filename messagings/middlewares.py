import logging
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from urllib.parse import parse_qs

User = get_user_model()
logger = logging.getLogger(__name__)

class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware for JWT authentication in channels
    """
    
    async def __call__(self, scope, receive, send):
        """Process the scope and attach the user"""
        # Extract query parameters
        query_string = scope.get("query_string", b"").decode()
        print(f"Query string: {query_string}")
        
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]
        
        print(f"Token received: {token[:10]}..." if token else "No token")
        
        if token:
            # Verify and authenticate the token
            try:
                user = await self.get_user_from_token(token)
                print(f"Authenticated user: {user.username if not user.is_anonymous else 'Anonymous'}")
                scope['user'] = user
            except Exception as e:
                print(f"Authentication error: {str(e)}")
                scope['user'] = AnonymousUser()
        else:
            print("No token provided, setting anonymous user")
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        """Get the user from the JWT token"""
        try:
            # Get the user's ID from the token
            validated_token = AccessToken(token)
            user_id = validated_token['user_id']
            print(f"Token validated, user_id: {user_id}")
            
            # Get the user from the database
            user = User.objects.get(id=user_id)
            print(f"User found: {user.username}")
            return user
        except InvalidToken as e:
            print(f"Invalid token: {str(e)}")
            return AnonymousUser()
        except TokenError as e:
            print(f"Token error: {str(e)}")
            return AnonymousUser()
        except User.DoesNotExist:
            print(f"User with ID {user_id} not found")
            return AnonymousUser()
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return AnonymousUser()