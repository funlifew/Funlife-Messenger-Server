from django.utils import timezone
from .models import UserSession
import logging

logger = logging.getLogger(__name__)

class SessionActivityMiddleware:
    """Middleware to update session activity timestamp on each request"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request
        if request.user.is_authenticated:
            # Only update session activity for authenticated users
            session_id = request.META.get('HTTP_X_SESSION_ID')
            if session_id:
                try:
                    # Update the session activity
                    session = UserSession.objects.get(
                        id=session_id,
                        user=request.user,
                        is_active=True
                    )
                    session.update_activity()
                except Exception as e:
                    # Log error but don't interrupt request
                    logger.warning(f"Error updating session activity: {e}")
        
        # Process the response
        response = self.get_response(request)
        return response