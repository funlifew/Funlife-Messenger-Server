from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from .models import OTP, OTPPurpose
from django.utils.translation import gettext_lazy as _

User = get_user_model()

def get_user(user_id):
    return User.objects.filter(id=user_id).first()

def check_user_banned(user):
    """Check if a user is banned and raise appropriate error if so"""
    if user.is_banned:
        ban_minutes = max(1, (user.ban_until - timezone.now()).seconds // 60)
        raise serializers.ValidationError(
            _(f"Account is temporarily locked. Try again in {ban_minutes} minutes.")
        )


def validate_user_password(user, password):
    """Validate a password against user attributes"""
    try:
        is_valid, errors = User.objects.validate_password(
            user.username, 
            user.email, 
            password
        )
        if not is_valid:
            raise serializers.ValidationError(errors)
        return True
    except Exception as e:
        raise serializers.ValidationError(str(e))

def delete_all_user_otps(user_id):
    """Delete previous user otps"""
    user = get_user(user_id)
    if not user:
        return None
    return OTP.objects.filter(user=user, purpose=OTPPurpose.VERIFICATION).delete()

def create_new_otp(user_id):
    """Create a new otp for user who has not verified"""
    user = get_user(user_id)
    delete_all_user_otps(user_id)
    return OTP.objects.create(
        user = user,
        purpose=OTPPurpose.VERIFICATION,
    )

def validate_otp(otp_id, code, purpose=None, check_used=True, check_expired=True):
    """Validate an OTP code"""
    try:
        query_params = {'id': otp_id}
        if purpose:
            query_params['purpose'] = purpose
            
        otp = OTP.objects.get(**query_params)
        
        if check_used and otp.is_used:
            raise serializers.ValidationError(_("This code has already been used."))
            
        if check_expired and otp.is_expire:
            raise serializers.ValidationError(_("This code has expired."))
            
        if not otp.verify(code):
            raise serializers.ValidationError(_("Invalid verification code."))
            
        return otp
        
    except OTP.DoesNotExist:
        raise serializers.ValidationError(_("Invalid verification code."))

class UserSerializer(serializers.ModelSerializer):
    """User Serializer"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_verified', 'role', 'is_2fa_enabled', 'created_at']
        read_only_fields = ['id', 'username', 'email', 'role', 'is_superuser', 'is_staff', 'created_at']

class RegisterSerializer(serializers.ModelSerializer):
    """Registration serializer without password confirmation"""
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True}
        }
    
    def create(self, validated_data):
        """Create and return a new User"""
        try:
            user = User.objects.create_user(
                username = validated_data['username'],
                email = validated_data['email'],
                password=validated_data['password']
            )
            return user
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

class LoginSerializer(serializers.Serializer):
    """Login serializer to authenticate users"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            raise serializers.ValidationError(_("Must include 'username' and 'password'."))

        try:
            # First check if the user is exists and isn't banned
            user = User.objects.get(username=username)
            
            check_user_banned(user)
            
            # Attempt authentication
            user = authenticate(username=username, password=password)
            
            if not user:
                # Failed login attempts
                try:
                    user = User.objects.get(username=username)
                    user.increment_failed()
                    attempts_left = max(0, 5 - user.login_failed_attempts)
                    raise serializers.ValidationError(
                        _(f"Invalid credentials. {attempts_left} attempts remaining.")
                    )
                except User.DoesNotExist:
                    # Don't reveal that the user doesn't exist
                    raise serializers.ValidationError(_("Invalid credentials."))
                
            # Authentication is successfull
            user.reset_failures()
            
            # Make sure user is properly activated
            if not user.is_active:
                raise serializers.ValidationError(_("User account is disabled."))
            
            if not user.is_verified:
                if not user.is_verified:
                    otp = create_new_otp(user.id)
                    user.increment_failed()
                    raise serializers.ValidationError({
                        "verification_required": True,
                        "message": "You have to verify first",
                        "otp_id": str(otp.id)
                    })
            
            # Set the authenticated user on the serializer
            data['user'] = user
            return user
        except User.DoesNotExist:
            # Don't reveal that the user doesn't exist
            raise serializers.ValidationError(_("Invalid credentials."))

class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change endpoint"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    
    def validate_old_password(self, value):
        """Validate that the old password is correct"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Current password is incorrect"))
        return value
    
    def validate_new_password(self, value):
        """Validate that the new password meets requirements"""
        user = self.context['request'].user
        validate_user_password(user, value)
        return value
    
    def save(self):
        """Set the new password"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset"""
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Validate that a user with this email exists"""
        try:
            user = User.objects.get(email=value)
            check_user_banned(user)
            self.context['user'] = user
            return value
        except User.DoesNotExist:
            raise ValidationError("User not found.")

class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming a password reset with OTP"""
    otp_id = serializers.UUIDField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    new_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        """Validate OTP and new password"""
        otp = validate_otp(data['otp_id'], data['code'], purpose=OTPPurpose.RESET_PASSWORD)
        user = otp.user
        
        validate_user_password(user, data['new_password'])
        
        data['user'] = user
        data['otp'] = otp
        return data

class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification"""
    otp_id = serializers.UUIDField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    
    def validate(self, data):
        """Validate OTP code for email verification"""
        otp = validate_otp(data['otp_id'], data['code'], purpose=OTPPurpose.VERIFICATION)
        data['otp'] = otp
        return data

class OTPSerializer(serializers.ModelSerializer):
    """Serializer for OTP objects"""
    class Meta:
        model = OTP
        fields = ['id', 'purpose', 'created_at', 'expires_at', 'is_used']
        read_only_fields = ['id', 'created_at', 'expires_at', 'is_used']


class OTPVerificationSerializer(serializers.Serializer):
    """Serializer for OTP verification"""
    otp_id = serializers.UUIDField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate(self, data):
        """Validate OTP code"""
        otp = validate_otp(data['otp_id'], data['code'])
        data['otp'] = otp
        return data

class TwoFactorSetupSerializer(serializers.Serializer):
    """Serializer for setting up 2FA"""
    enable = serializers.BooleanField(required=True)
    code = serializers.CharField(required=False, min_length=6, max_length=6)
    
    def validate(self, data):
        """Validate 2FA setup data"""
        user = self.context['request'].user
        enable = data.get('enable', False)
        
        # If enabling 2FA, code is required to verify setup
        if enable and user.is_2fa_enabled:
            raise serializers.ValidationError(_("Two-factor authentication is already enabled."))
            
        # If disabling 2FA, code is required to verify
        if not enable and not user.is_2fa_enabled:
            raise serializers.ValidationError(_("Two-factor authentication is already disabled."))
            
        # If disabling, verify with code
        if not enable and 'code' not in data:
            raise serializers.ValidationError(_("Verification code is required to disable 2FA."))
            
        return data

class TwoFactorVerifySerializer(serializers.Serializer):
    """Serializer for 2FA verification during login"""
    otp_id = serializers.UUIDField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    
    def validate(self, data):
        """Validate 2FA code"""
        otp = validate_otp(data['otp_id'], data['code'], purpose=OTPPurpose.TWO_FACTOR)
        data['user'] = otp.user
        return data