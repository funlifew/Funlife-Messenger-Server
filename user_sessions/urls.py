from django.urls import path
from . import views

app_name = 'user_sessions'

urlpatterns = [
    path('', views.UserSessionListView.as_view(), name='session_list'),
    path('<uuid:session_id>/', views.UserSessionDetailView.as_view(), name='session_detail'),
    path('invalidate-all/', views.InvalidateAllSessionsView.as_view(), name='invalidate_all'),
    path('extend/', views.ExtendSessionView.as_view(), name='extend_session'),
    path('update-activity/', views.UpdateActivityView.as_view(), name='update_activity'),
]