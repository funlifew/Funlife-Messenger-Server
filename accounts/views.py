from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import OTP, OTPPurpose
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    EmailVerificationSerializer,
    OTPSerializer,
    OTPVerificationSerializer,
    TwoFactorSetupSerializer,
    TwoFactorVerifySerializer,
)
from user_sessions.models import UserSession
import pyotp

User = get_user_model

# Some helper functions
def get_tokens_for_user(user):
    """Generate JWT Tokens for authenticated user"""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }

def create_user_session(user, request):
    """Create new session for an user"""
    # Extract IP and User Agent
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    ip_address = request.META.get("REMOTE_ADDR", "")
    
    # Create session
    session = UserSession.objects.create(
        user=user,
        ip_address = ip_address
    )
    
    # Store device info
    session.store_device_info(user_agent=user_agent)
    
    return session

# Create your views here.

class RegisterView(generics.CreateAPIView):
    """Handle User registration"""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # OTP creation
        otp = OTP.objects.create(user=user, purpose=OTPPurpose.REGISTRATION)

        return Response({
            'message': 'User registered successfully. Please verify your email.',
            'otp_id': str(otp.id),
            'code': otp.code  # Only for testing! Remove in production
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    """Handle User Login"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get authenticated user
        user = serializer.validated_data['user']
        
        # check if 2FA is enabled
        if user.is_2fa_enabled:
            otp = self._create_user_2fa(user)
            return Response({
                '2fa_required': True,
                'otp_id': str(otp.id),
                'code': otp.code,  # Only for testing! Remove in production
                'message': 'Two-factor authentication required.'
            }, status=status.HTTP_200_OK)
        
        # create user session
        session = create_user_session(user, request)
        
        # generate JWT token
        tokens = get_tokens_for_user(user)
        
        return Response({
            'message': 'Login successful',
            'tokens': tokens,
            'user': UserSerializer(user).data,
            'session_id': str(session.id)
        }, status=status.HTTP_200_OK)
    
    def _create_user_2fa(self, user):
        self._delete_all_user_2fa_otps(user)
        return OTP.objects.create(user=user, purpose=OTPPurpose.TWO_FACTOR)

    def _delete_all_user_2fa_otps(self, user):
        return OTP.objects.filter(user=user, purpose=OTPPurpose.TWO_FACTOR).delete()

class TwoFactorVerifyView(APIView):
    """Handle 2FAs"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = TwoFactorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # get user from validated OTP
        user = serializer.validated_data['user']
        
        # create a session
        session = create_user_session(user, request)
        
        # generate JWT token for user
        tokens = get_tokens_for_user(user)
        
        return Response({
            'message': 'Two-factor authentication successful',
            'tokens': tokens,
            'user': UserSerializer(user).data,
            'session_id': str(session.id)
        }, status=status.HTTP_200_OK)

class LogoutView(APIView):
    """Handle user logout"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Get session ID from request if provided
        session_id = request.data.get('session_id')
        
        if session_id:
            # Invalidate specific session
            try:
                session = UserSession.objects.get(id=session_id, user=request.user)
                session.invalidate()
                return Response({'message': 'Session logged out successfully'}, status=status.HTTP_200_OK)
            except UserSession.DoesNotExist:
                return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Invalidate all user sessions
            UserSession.invalidate_all_sessions(request.user)
            return Response({'message': 'All sessions logged out successfully'}, status=status.HTTP_200_OK)


class EmailVerificationView(APIView):
    """Verify user email with OTP"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get the OTP and mark it as used
        otp = serializer.validated_data['otp']
        user = otp.user
        
        # Update user verification status
        user.is_verified = True
        user.save()
        
        return Response({
            'message': 'Email verification successful',
            'email': user.email
        }, status=status.HTTP_200_OK)
class PasswordResetRequestView(APIView):
    """Request password reset (forgot password)"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get user from context (set during validation)
        user = serializer.context.get('user')
        
        if user:
            # Generate reset OTP
            otp = OTP.objects.create(user=user, purpose=OTPPurpose.RESET_PASSWORD)
            
            # In production, send this via email
            # For testing, include in response
            return Response({
                'message': 'Password reset link sent to your email',
                'otp_id': str(otp.id),
                'code': otp.code  # Only for testing! Remove in production
            }, status=status.HTTP_200_OK)
        else:
            # Don't reveal if email exists or not for security
            return Response({
                'message': 'If this email is registered, a reset link has been sent.'
            }, status=status.HTTP_200_OK)