import logging
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from urllib.parse import parse_qs
from security_logs.models import SecurityLog, EventType

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


class WebSocketAuthMiddleware(BaseMiddleware):
    """Authenticate WebSocket connections using JWT"""
    
    async def __call__(self, scope, receive, send):
        """Process the scope and authenticate the user"""
        # Extract query parameters from scope
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        # Extract the token
        token = query_params.get('token', [None])[0]
        
        if token:
            # Authenticate with token
            scope['user'] = await self.authenticate_token(token, scope)
        else:
            # No token provided
            scope['user'] = AnonymousUser()
            logger.warning(f"WebSocket connection attempted without token: {scope.get('path', '')}")
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def authenticate_token(self, token, scope):
        """Authenticate the JWT token and return a user"""
        try:
            # Validate token
            validated_token = AccessToken(token)
            
            # Get user from token payload
            user_id = validated_token.get('user_id')
            if not user_id:
                logger.warning("Token does not contain user_id")
                return AnonymousUser()
            
            # Get the user
            try:
                user = User.objects.get(id=user_id)
                
                # Log successful WebSocket connection
                client_ip = self._get_client_ip(scope)
                device_info = self._get_device_info(scope)
                
                # Log as security event
                SecurityLog.log_event(
                    event_type=EventType.API_ACCESS,
                    user=user,
                    ip_address=client_ip,
                    device_info=device_info,
                    details={
                        'path': scope.get('path', ''),
                        'type': 'websocket_connect'
                    }
                )
                
                return user
                
            except User.DoesNotExist:
                logger.warning(f"User with ID {user_id} not found")
                return AnonymousUser()
                
        except (InvalidToken, TokenError) as e:
            logger.warning(f"Invalid token: {str(e)}")
            return AnonymousUser()
        except Exception as e:
            logger.exception(f"Error authenticating WebSocket token: {str(e)}")
            return AnonymousUser()
    
    def _get_client_ip(self, scope):
        """Extract client IP from scope"""
        try:
            # Try to get from headers first (for proxies)
            headers = dict(scope.get('headers', []))
            x_forwarded_for = headers.get(b'x-forwarded-for', b'').decode()
            
            if x_forwarded_for:
                return x_forwarded_for.split(',')[0].strip()
            
            # Fallback to client address
            client = scope.get('client', None)
            if client:
                return client[0]  # (host, port) tuple
        except:
            pass
        
        return None
    
    def _get_device_info(self, scope):
        """Extract device info from scope"""
        try:
            headers = dict(scope.get('headers', []))
            user_agent = headers.get(b'user-agent', b'').decode()
            
            return {
                'user_agent': user_agent,
                'path': scope.get('path', ''),
                'connection_type': 'websocket'
            }
        except:
            return None