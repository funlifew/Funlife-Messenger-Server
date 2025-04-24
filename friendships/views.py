from rest_framework import views, generics, status, permissions
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Friendship, FriendshipStatus
from .serializers import (
    FriendshipSerializer,
    FriendRequestSerializer,
    FriendProfileSerializer,
    FriendRequestActionSerializer
)
from profiles.models import Profile

from security_logs.utils import SecurityLogger
from security_logs.models import EventType

User = get_user_model()

class FriendListView(generics.ListAPIView):
    """List all friends of the authenticated user"""
    serializer_class = FriendProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return list of friends for the authenticated user"""
        return Friendship.get_user_friends(self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        print(serializer.data)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })

class FriendRequestBaseView(generics.ListAPIView):
    """Base class for friend request list views"""
    serializer_class = FriendshipSerializer
    permission_classes = [permissions.IsAuthenticated]

class PendingFriendRequestsView(FriendRequestBaseView):
    """List pending friend requests received by the user"""
    def get_queryset(self):
        """Return pending friend requests for the user"""
        return Friendship.get_pending_requests(self.request.user)

class SentFriendRequestsView(FriendRequestBaseView):
    """List friend requests sent by the user"""
    def get_queryset(self):
        """Return friend requests sent by the user"""
        return Friendship.get_sent_requests(self.request.user)

class BlockedUsersView(generics.ListAPIView):
    """List users blocked by the authenticated user"""
    serializer_class = FriendProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return list of users blocked by the authenticated user"""
        blocked_ids = Friendship.get_blocked_users(self.request.user)
        return User.objects.filter(id__in=blocked_ids)

class SendFriendRequestView(views.APIView):
    """Send a friend request to another user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = FriendRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            friend = serializer.friend
            
            # Create friendship with PENDING status
            friendship = Friendship.objects.create(
                user=request.user,
                friend=friend,
                status=FriendshipStatus.PENDING
            )
            
            # After successfully creating friendship
            SecurityLogger.log_friend_event(
                user=request.user,
                friend=friend,  # This should be the friend object from your code
                event_type=EventType.FRIEND_REQUEST_SENT,
                request=request
            )
            return Response({
                'message': f'Friend request sent to {friend.username}',
                'friendship': FriendshipSerializer(friendship).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ManageFriendRequestView(views.APIView):
    """Accept, reject, or block a friend request"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, action):
        """Handle friend request actions"""
        # Validate action parameter
        valid_actions = {'accept', 'reject', 'block', 'unblock', 'cancel', 'unfriend'}
        if action not in valid_actions:
            return Response(
                {'error': f'Invalid action. Must be one of: {", ".join(valid_actions)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = FriendRequestActionSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        friendship = serializer.friendship
        user = request.user
        
        # Process the action
        try:
            result, message = self._process_action(action, friendship, user)
            
            if result:
                return Response({'message': message}, status=status.HTTP_200_OK)
            else:
                return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response(
                {'error': f'Error processing action: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _process_action(self, action, friendship, user):
        """Process the requested friendship action"""
        # Get the target user (the other person in the friendship)
        target_user = friendship.friend if friendship.user == user else friendship.user
        
        # Execute the requested action
        if action == 'accept':
            if friendship.friend == user and friendship.status == FriendshipStatus.PENDING:
                return friendship.accept(), f"Friend request from {friendship.user.username} accepted"
            return False, "You can only accept pending requests sent to you"
            
        elif action == 'reject':
            if friendship.friend == user and friendship.status == FriendshipStatus.PENDING:
                return friendship.reject(), f"Friend request from {friendship.user.username} rejected"
            return False, "You can only reject pending requests sent to you"
            
        elif action == 'block':
            result = friendship.block()
            return result, f"User {target_user.username} has been blocked"
            
        elif action == 'unblock':
            if friendship.status == FriendshipStatus.BLOCKED and friendship.user == user:
                return friendship.unblock(), f"User {friendship.friend.username} has been unblocked"
            return False, "You can only unblock users that you have blocked"
            
        elif action == 'cancel':
            if friendship.user == user and friendship.status == FriendshipStatus.PENDING:
                friendship.delete()
                return True, f"Friend request to {friendship.friend.username} cancelled"
            return False, "You can only cancel pending requests that you sent"
            
        elif action == 'unfriend':
            if friendship.status == FriendshipStatus.ACCEPTED:
                friendship.delete()
                return True, f"You are no longer friends with {target_user.username}"
            return False, "You can only unfriend users that are your friends"
        
        # Should never reach here due to earlier validation
        return False, "Invalid action"

class SearchFriendsView(generics.ListAPIView):
    """Search for users to add as friends"""
    serializer_class = FriendProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Search for users by username or display name"""
        query = self.request.query_params.get('q', '')
        if not query or len(query) < 3:
            return User.objects.none()
        
        # Search in username and profile display_name
        return User.objects.filter(
            Q(username__icontains=query) | 
            Q(profile__display_name__icontains=query)
        ).exclude(id=self.request.user.id)
        
    def list(self, request, *args, **kwargs):
        """Custom list implementation with additional metadata"""
        queryset = self.get_queryset()
        
        # Add pagination if needed
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(queryset, many=True)
        
        # Return with metadata
        return Response({
            'query': request.query_params.get('q', ''),
            'count': len(serializer.data),
            'results': serializer.data
        })