import json
from django.utils.deprecation import MiddlewareMixin
from .models import SecurityLog, EventType, SeverityLevel
from .utils import SecurityLogger

class SecurityLoggingMiddleware(MiddlewareMixin):
    """Middleware for logging security-related events"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
        
    def process_request(self, request):
        """Process the request before it reaches the view"""
        # We'll just pass for now as we'll process after the view
        pass
        
    def process_response(self, request, response):
        """Process the response after the view has been called"""
        # Log API access for authenticated users (except for common URLs)
        if (hasattr(request, 'user') and 
            request.user.is_authenticated and 
            request.path.startswith('/api/') and
            not request.path.startswith('/api/auth/token/refresh/')):
            
            # Skip logging for certain endpoints to avoid excessive logging
            skip_paths = [
                '/api/messages/',
                '/api/sessions/update-activity/'
            ]
            
            # Check if the path starts with any of the skip paths
            if not any(request.path.startswith(path) for path in skip_paths):
                # Log API access
                SecurityLogger.log_account_event(
                    user=request.user,
                    event_type=EventType.API_ACCESS,
                    request=request,
                    details={
                        'path': request.path,
                        'method': request.method,
                        'status_code': response.status_code
                    }
                )
        
        # Log unauthorized access attempts
        if response.status_code == 401:  # Unauthorized
            try:
                # Try to get user if available (might be AnonymousUser)
                user = request.user if request.user.is_authenticated else None
                
                SecurityLogger.log_authentication(
                    user=user,
                    success=False,
                    request=request,
                    details={
                        'path': request.path,
                        'method': request.method,
                        'status_code': 401,
                        'reason': 'Unauthorized access attempt'
                    }
                )
            except Exception:
                # Don't let logging errors affect the response
                pass
                
        # Log forbidden access attempts
        elif response.status_code == 403:  # Forbidden
            try:
                # User is likely authenticated for a 403
                user = request.user if request.user.is_authenticated else None
                
                SecurityLogger.log_suspicious_activity(
                    user=user,
                    activity_type='forbidden_access',
                    request=request,
                    details={
                        'path': request.path,
                        'method': request.method,
                        'status_code': 403,
                        'reason': 'Forbidden access attempt'
                    }
                )
            except Exception:
                # Don't let logging errors affect the response
                pass
                
        # Log rate limit exceeded
        elif response.status_code == 429:  # Too Many Requests
            try:
                # User might be authenticated or not
                user = request.user if request.user.is_authenticated else None
                
                SecurityLogger.log_account_event(
                    user=user,
                    event_type=EventType.RATE_LIMIT_EXCEEDED,
                    request=request,
                    severity=SeverityLevel.WARNING,
                    details={
                        'path': request.path,
                        'method': request.method,
                        'status_code': 429,
                        'reason': 'Rate limit exceeded'
                    }
                )
            except Exception:
                # Don't let logging errors affect the response
                pass
            
        # Log backup download attempts
        elif request.path.startswith('/api/backups/download/'):
            try:
                user = request.user if request.user.is_authenticated else None
                if user:
                    SecurityLogger.log_account_event(
                        user=user,
                        event_type=EventType.BACKUP_ACCESS,
                        request=request,
                        details={
                            'path': request.path,
                            'method': request.method,
                            'status_code': response.status_code
                        }
                    )
            except Exception:
                # Don't let logging errors affect the response
                pass
        
        return response