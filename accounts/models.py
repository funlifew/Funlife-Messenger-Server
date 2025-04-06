from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from utils.password_validator import PasswordValidator
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from datetime import timedelta
from django.conf import settings
from enum import Enum
import uuid



# Create your models here.

class Roles(Enum):
    USER="user"
    ADMIN="admin"

class Auth(Enum):
    LOGIN = "login"
    FORGET = "forget"

class UserManager(BaseUserManager, PermissionsMixin):
    """Customize User Manager"""
    def create_user(self, username, email, password=None, **extra_fields):
        """Create and Save a new user"""
        self.check_for_username_email(username, email)
        self.check_for_password(password)
        password = self.validate_password(username, email, password)
        user = self.create(username, email, password, **extra_fields)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        self.check_for_username_email(username, email)
        self.check_for_password(password)
        password = self.validate_password(username, email, password)
        user = self.create(username, email, password, role="superuser", **extra_fields)
        return user
    
    def check_for_username_email(self, username=None, email=None):
        if not email:
            raise ValidationError("Email is required.")
        
        if not username:
            raise ValidationError("Username is required.")
    
    def check_for_password(self, password=None):
        """checking for password"""
        if not password:
            return ValidationError("Password is required.")
        
    def validate_password(self, username, email, password=None):
        """validating password"""
        is_valid, errors = PasswordValidator.validate(password, username, email)
        if not is_valid:
            raise ValidationError(" - ".join(errors))
        
        if PasswordValidator.is_password_pwned(password):
            raise ValidationError("Password is leaked on sessions databases, please choose a more secure password.")

        return password
    
    def create(self, username, email, password, role="user", **extra_fields):
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            **extra_fields,
        )
        user.set_password(password)
        
        
        if role == "superuser":
            user.is_superuser=True
            user.is_staff=True
            user.is_verified=True
            user.role=Roles.ADMIN
        
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    ROLES = (
        ("user", "User"),
        ("admin", "Admin"),
    )
    USERNAME_REGEX_VALIDATOR = RegexValidator(
        regex=r'^[a-zA-Z0-9._]+$',
        message='Username just contains words, numbers and underscore (_) and dot (.)',
        code='invalid_username'
    )
    
    username = models.CharField(
        max_length=60, 
        unique=True,
        validators=[
            USERNAME_REGEX_VALIDATOR
        ]
    )
    email = models.EmailField(unique=True)
    
    # validation fields
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    role = models.CharField(max_length=10, choices=ROLES, default='user')

    # Security fields
    login_failed_attempts = models.IntegerField(default=0)
    ban_until = models.DateTimeField(null=True, blank=True)
    forget_attempts = models.IntegerField(default=0)
    public_key = models.TextField(blank=True, null=True)
    is_2fa_enabled = models.BooleanField(default=False)
    
    # time fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    
    def __str__(self):
        return self.username

    # Help methods
    
    @property
    def is_banned(self):
        """Checking for ban"""
        return self.ban_until and self.ban_until > timezone.now()
    
    def ban_user(self, year=None, hours=None, minutes=5):
        """banning a user with for a speciefic hours"""
        self.ban_until = timezone.now() + timedelta(
            days=year * 365,
            hours=hours,
            minutes=minutes
        )
        self.save()
    
    
    def unban_user(self):
        """unbanning a user"""
        self.ban_until = None
        self.login_failed_attempts = 0
        self.forget_attempts=0
        self.save()
    
    def increment_failed(self, type=Auth.LOGIN):
        """increment when authentication credentials was wrong"""
        self.check_for_increment(type)
        self.check_for_attempts()
        self.save()
    
    
    def check_for_increment(self, type=Auth.LOGIN):
        if type == Auth.LOGIN:
            self.login_failed_attempts += 1
        elif type == Auth.FORGET:
            self.forget_attempts += 1

    def check_for_attempts(self):
        if self.login_failed_attempts >= settings.MAX_AUTH_TRIES or self.forget_attempts >= settings.MAX_AUTH_TRIES:
            self.ban_user(minutes=20)
    
    def reset_failures(self):
        """Resetting when credentials was ok"""
        self.login_failed_attempts = 0
        self.forget_attempts = 0
        self.save()

class OTP(models.Model):
    PURPOSES = (
        ("2fa", '2FA'),
        ("registration", "Registration"),
        ("verification", "Verification")
    )
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6, null=True, blank=True)
    purpose = models.CharField(choices=PURPOSES)
    refreshes_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    refreshes_attempts = models.IntegerField(default=0)