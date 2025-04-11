from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.utils import timezone
from .models import Profile
from .serializers import ProfileSerializer

# Create your views here.
class ProfileDetailView(generics.RetrieveUpdateAPIView):
    """User's Profile showing up and also update included"""
    serializer_class=ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        # Return the profile of the logged-in user
        return self.request.user.profile
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    

class FriendProfileView(generics.RetrieveAPIView):
    """View a friend's profile"""
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        profile_id = self.kwargs.get('profile_id')
        try:
            # TODO: After friendship part
            # For now, simple implementation just retrieving by ID
            profile = Profile.objects.get(id=profile_id)
            # TODO: Check if the user is friends with this profile's user
            return profile
        except Profile.DoesNotExist:
            return Response(
                {"error": "Profile not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

class UpdateProfileStatusView(APIView):
    """Update the user's status message"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        profile = request.user.profile
        status_message = request.data.get('status')
        
        if not status_message:
            return Response(
                {"error": "Status message is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        profile.status = status_message
        profile.save(update_fields=['status'])
        
        return Response({
            "message": "Status updated successfully",
            "status": profile.status
        })