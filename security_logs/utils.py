import json
from django.utils import timezone
from .models import SecurityLog, EventType, SeverityLevel

class SecurityLogger:
    """
    Utility class for logging security events from anywhere in the application
    """
    
    @staticmethod
    def _extract_device_info(request):
        """Extract device info from a request object"""
        if not request:
            return None
            
        return {
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'path': request.path,
            'method': request.method
        }
    
    @staticmethod
    def _extract_ip_address(request):
        """Extract IP address from a request object"""
        if not request:
            return None
            
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @classmethod
    def log_authentication(cls, user, success=True, request=None, details=None):
        """Log authentication events (login/failed login)"""
        event_type = EventType.LOGIN if success else EventType.FAILED_LOGIN
        severity = SeverityLevel.INFO if success else SeverityLevel.WARNING
        
        ip_address = cls._extract_ip_address(request)
        device_info = cls._extract_device_info(request)
        
        event_details = {
            'success': success,
            'timestamp': timezone.now().isoformat()
        }
        
        if details:
            event_details.update(details)
        
        return SecurityLog.log_event(
            event_type=event_type,
            user=user,
            ip_address=ip_address,
            device_info=device_info,
            severity=severity,
            details=event_details
        )
    
    @classmethod
    def log_account_event(cls, user, event_type, request=None, details=None, severity=SeverityLevel.INFO):
        """Log account-related events"""
        ip_address = cls._extract_ip_address(request)
        device_info = cls._extract_device_info(request)
        
        event_details = {
            'timestamp': timezone.now().isoformat()
        }
        
        if details:
            event_details.update(details)
        
        return SecurityLog.log_event(
            event_type=event_type,
            user=user,
            ip_address=ip_address,
            device_info=device_info,
            severity=severity,
            details=event_details
        )
    
    @classmethod
    def log_session_event(cls, user, session_id, event_type, request=None, details=None):
        """Log session-related events"""
        ip_address = cls._extract_ip_address(request)
        device_info = cls._extract_device_info(request)
        
        event_details = {
            'session_id': str(session_id),
            'timestamp': timezone.now().isoformat()
        }
        
        if details:
            event_details.update(details)
        
        return SecurityLog.log_event(
            event_type=event_type,
            user=user,
            ip_address=ip_address,
            device_info=device_info,
            severity=SeverityLevel.INFO,
            details=event_details
        )
    
    @classmethod
    def log_friend_event(cls, user, friend, event_type, request=None, details=None):
        """Log friendship-related events"""
        ip_address = cls._extract_ip_address(request)
        device_info = cls._extract_device_info(request)
        
        event_details = {
            'friend_id': str(friend.id),
            'friend_username': friend.username,
            'timestamp': timezone.now().isoformat()
        }
        
        if details:
            event_details.update(details)
        
        return SecurityLog.log_event(
            event_type=event_type,
            user=user,
            ip_address=ip_address,
            device_info=device_info,
            severity=SeverityLevel.INFO,
            details=event_details
        )
    
    @classmethod
    def log_message_event(cls, user, message_id, event_type, request=None, details=None):
        """Log message-related events"""
        ip_address = cls._extract_ip_address(request)
        device_info = cls._extract_device_info(request)
        
        event_details = {
            'message_id': str(message_id),
            'timestamp': timezone.now().isoformat()
        }
        
        if details:
            event_details.update(details)
        
        return SecurityLog.log_event(
            event_type=event_type,
            user=user,
            ip_address=ip_address,
            device_info=device_info,
            severity=SeverityLevel.INFO,
            details=event_details
        )
    
    @classmethod
    def log_suspicious_activity(cls, user, activity_type, request=None, details=None):
        """Log suspicious activity"""
        ip_address = cls._extract_ip_address(request)
        device_info = cls._extract_device_info(request)
        
        event_details = {
            'activity_type': activity_type,
            'timestamp': timezone.now().isoformat()
        }
        
        if details:
            event_details.update(details)
        
        return SecurityLog.log_event(
            event_type=EventType.SUSPICIOUS_ACTIVITY,
            user=user,
            ip_address=ip_address,
            device_info=device_info,
            severity=SeverityLevel.WARNING,
            details=event_details
        )