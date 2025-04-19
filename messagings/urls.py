from django.urls import path
from . import views

app_name = 'messagings'

urlpatterns = [
    # Message sending and viewing
    path('send/', views.SendMessageView.as_view(), name='send_message'),
    path('conversation/<uuid:user_id>/', views.ConversationListView.as_view(), name='conversation'),
    path('conversations/', views.ConversationSummaryView.as_view(), name='conversation_summaries'),
    
    # Message status updates
    path('read/<uuid:message_id>/', views.MarkMessageReadView.as_view(), name='mark_read'),
    path('read-all/<uuid:user_id>/', views.MarkAllMessagesReadView.as_view(), name='mark_all_read'),
    path('delete/<uuid:message_id>/', views.DeleteMessageView.as_view(), name='delete_message'),
    
    # Typing status
    path('typing/update/', views.TypingStatusUpdateView.as_view(), name='update_typing_status'),
    path('typing/<uuid:user_id>/', views.TypingStatusView.as_view(), name='get_typing_status'),
    
    # Encryption key management
    path('keys/generate/', views.GenerateKeyPairView.as_view(), name='generate_keys'),
    path('keys/public/', views.GetPublicKeyView.as_view(), name='get_public_key'),
]