from django.urls import path
from . import views, api

app_name = 'backups'

urlpatterns = [
    path('', views.BackupListView.as_view(), name='backup_list'),
    path('create/', views.CreateBackupView.as_view(), name='create_backup'),
    path('download/', views.DownloadBackupView.as_view(), name='download_backup'),
    path('<uuid:pk>/', views.DeleteBackupView.as_view(), name='delete_backup'),
    path('prepare/', api.PrepareBackupView.as_view(), name='prepare_backup'),
    path('decrypt/', api.DecryptBackupView.as_view(), name='decrypt_backup'),
]