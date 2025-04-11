from django.urls import path
from . import views

app_name = 'friendships'

urlpatterns = [
    # List endpoints
    path('', views.FriendListView.as_view(), name='friend_list'),
    path('pending/', views.PendingFriendRequestsView.as_view(), name='pending_requests'),
    path('sent/', views.SentFriendRequestsView.as_view(), name='sent_requests'),
    path('blocked/', views.BlockedUsersView.as_view(), name='blocked_users'),
    
    # Action endpoints
    path('request/', views.SendFriendRequestView.as_view(), name='send_request'),
    path('action/<str:action>/', views.ManageFriendRequestView.as_view(), name='manage_request'),
    
    # Search users
    path('search/', views.SearchFriendsView.as_view(), name='search_friends'),
]