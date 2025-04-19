from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import UserSession
from .serializers import UserSessionSerializer, SessionUpdateSerializer

# Create your views here.
class UserSessionListView(generics.ListAPIView):
    """List all active sessions for the current user"""
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return all active sessions for the current user"""
        return UserSession.get_active_sessions(self.request.user)

class UserSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View, update or delete a specific session"""
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Get the session, ensuring it belongs to the current user"""
        session_id = self.kwargs.get("session_id")
        return get_object_or_404(UserSession, id=session_id, user=self.request.user)

    def update(self, request, *args, **kwargs):
        """Update session properties"""
        session = self.get_object()
        serializer = SessionUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            # Update expires_at if provided
            if 'expires_at' in serializer.validated_data:
                session.expires_at = serializer.validated_data['expires_at']
            
            # Update is_active if provided
            if 'is_active' in serializer.validated_data:
                session.is_active = serializer.validated_data['is_active']
                # If deactivating, log it as a logout
                if not session.is_active:
                    # Log the logout event (you could add a security log here)
                    pass
            
            session.save()
            return Response(UserSessionSerializer(session).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """Invalidate the session instead of deleting it"""
        session = self.get_object()
        session.invalidate()
        return Response({"message": "Session logged out successfully"}, status=status.HTTP_200_OK)

class InvalidateAllSessionsView(APIView):
    """Invalidate all sessions except the current one"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Invalidate all sessions except the current one"""
        current_session_id = request.data.get('current_session_id')
        
        if not current_session_id:
            return Response(
                {"error": "current_session_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify the session belongs to the user
        try:
            current_session = UserSession.objects.get(
                id=current_session_id, 
                user=request.user,
                is_active=True
            )
        except UserSession.DoesNotExist:
            return Response(
                {"error": "Invalid session ID"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Invalidate all other sessions
        UserSession.invalidate_all_sessions(request.user, exclude_id=current_session_id)
        
        return Response({
            "message": "All other sessions have been logged out"
        })

class ExtendSessionView(APIView):
    """Extend the current session's expiration time"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Extend the session expiration"""
        session_id = request.data.get('session_id')
        days = request.data.get('days', 30)  # Default to 30 days
        
        try:
            days = int(days)
            if days <= 0 or days > 365:  # Set reasonable limits
                return Response(
                    {"error": "Days must be between 1 and 365"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid days value"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not session_id:
            return Response(
                {"error": "session_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get and extend the session
        try:
            session = UserSession.objects.get(
                id=session_id, 
                user=request.user,
                is_active=True
            )
            session.extend_session(days=days)
            
            return Response({
                "message": f"Session extended by {days} days",
                "session": UserSessionSerializer(session).data
            })
            
        except UserSession.DoesNotExist:
            return Response(
                {"error": "Invalid session ID"}, 
                status=status.HTTP_404_NOT_FOUND
            )

class UpdateActivityView(APIView):
    """Update the last activity timestamp for a session"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Update the last activity timestamp"""
        session_id = request.data.get('session_id')
        
        if not session_id:
            return Response(
                {"error": "session_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update the session activity
        try:
            session = UserSession.objects.get(
                id=session_id, 
                user=request.user,
                is_active=True
            )
            session.update_activity()
            
            return Response({
                "message": "Session activity updated",
                "last_activity": session.last_activity
            })
            
        except UserSession.DoesNotExist:
            return Response(
                {"error": "Invalid session ID"}, 
                status=status.HTTP_404_NOT_FOUND
            )