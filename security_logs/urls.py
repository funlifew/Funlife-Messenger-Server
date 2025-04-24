from django.urls import path
from . import views

app_name = 'security_logs'

urlpatterns = [
    path('logs/', views.SecurityLogListView.as_view(), name='log_list'),
    path('me/', views.UserSecurityLogView.as_view(), name='user_logs'),
    path('activity/', views.UserSecurityActivityView.as_view(), name='user_activity'),
    path('suspicious/', views.SuspiciousActivityView.as_view(), name='suspicious_activity'),
    path('ip/<str:ip_address>/', views.IPAddressLogsView.as_view(), name='ip_logs'),
]