from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views


app_name='accounts'
urlpatterns = [
    path("register/", views.RegisterView.as_view(), name='register'),
    path("login/", views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Email Verification
    path('verify-email/', views.EmailVerificationView.as_view(), name='verify_email'),
    
    # Password Management
    path("password/reset-request/", views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password/reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path("password/change/", views.ChangePasswordView.as_view(), name='change_password'),
    
    # Two-Factor authentication
    path('2fa/setup/', views.TwoFactorSetupView.as_view(), name='two_factor_setup'),
    path('2fa/verify/', views.TwoFactorVerifyView.as_view(), name='two_factor_verify'),
    
    # OTP Management
    path('otp/refresh/', views.OTPRefreshView.as_view(), name='otp_refresh'),
    
    # User's Profile
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
]
