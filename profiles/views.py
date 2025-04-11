from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from .serializers import ProfileSerializer
from django.utils import timezone

# Create your views here.
class ProfileView(APIView):
    """User's Profile showing up"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = ProfileSerializer()
        return Response()