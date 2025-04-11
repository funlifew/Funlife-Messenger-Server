from django.urls import path
from . import views

app_name='profiles'
urlpatterns = [
    path("me/", views.ProfileDetailView.as_view(), name='profile'),
    path("friend/<uuid:profile_id>/", views.FriendProfileView.as_view(), name='friend_profile'),
    path("status/update/", views.UpdateProfileStatusView.as_view(), name='update_status'),
]
