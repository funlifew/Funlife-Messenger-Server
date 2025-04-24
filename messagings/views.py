from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Max, OuterRef, Subquery
from .models import Message, TypingStatus
from .serializers import (
    MessageSerializer,
    MessageCreateSerializer,
    ConversationSerializer,
    ConversationSummarySerializer, 
    TypingStatusSerializer,
    TypingStatusUpdateSerializer,
    KeyPairGenerationSerializer,
    PublicKeySerializer
)
from friendships.models import Friendship
from security_logs.utils import SecurityLogger
from security_logs.models import EventType

User = get_user_model()

class SendMessageView(generics.CreateAPIView):
    """Create a new encrypted message"""
    serializer_class = MessageCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        """Save the sender with the message"""
        return serializer.save()
        
    def create(self, request, *args, **kwargs):
        """Create a new message with detailed response"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = self.perform_create(serializer)
        
        # After successfully sending a message
        SecurityLogger.log_message_event(
            user=request.user,
            message_id=message.id,  # This should be your message object ID
            event_type=EventType.MESSAGE_SEND,
            request=request
        )
        
        # Return the created message
        return Response({
            'message': 'Message sent successfully',
            'data': MessageSerializer(message).data if message else serializer.data
        }, status=status.HTTP_201_CREATED)

class ConversationListView(generics.ListAPIView):
    """Get messages between the current user and another user"""
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get conversation with another user"""
        user = self.request.user
        other_user_id = self.kwargs.get('user_id')
        other_user = get_object_or_404(User, id=other_user_id)
        
        # Check if they are friends
        if not Friendship.are_friends(user, other_user):
            return Message.objects.none()
            
        # Mark received messages as delivered
        undelivered_messages = Message.objects.filter(
            sender=other_user,
            receiver=user,
            is_delivered=False
        )
        
        for message in undelivered_messages:
            message.mark_as_delivered()
            
        # Get the conversation
        return Message.get_conversation(user, other_user)
    
    def list(self, request, *args, **kwargs):
        """List messages with additional metadata"""
        queryset = self.get_queryset()
        
        # Get pagination parameters
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        
        # Apply pagination
        messages = queryset[offset:offset+limit]
        
        # Serialize the messages
        serializer = self.get_serializer(messages, many=True)
        
        return Response({
            'count': queryset.count(),
            'next': offset + limit if offset + limit < queryset.count() else None,
            'previous': offset - limit if offset > 0 else None,
            'results': serializer.data
        })

class MarkMessageReadView(APIView):
    """Mark a message as read"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, message_id):
        """Mark a specific message as read"""
        user = request.user
        
        try:
            # Find the message
            message = Message.objects.get(id=message_id, receiver=user)
            
            # Mark as read
            message.mark_as_read()
            
            return Response({
                'message': 'Message marked as read',
                'data': MessageSerializer(message).data
            })
            
        except Message.DoesNotExist:
            return Response({
                'error': 'Message not found'
            }, status=status.HTTP_404_NOT_FOUND)

class MarkAllMessagesReadView(APIView):
    """Mark all messages from a user as read"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, user_id):
        """Mark all messages from a specific user as read"""
        current_user = request.user
        
        try:
            other_user = User.objects.get(id=user_id)
            
            # Check if they are friends
            if not Friendship.are_friends(current_user, other_user):
                return Response({
                    'error': 'User not found in your friends list'
                }, status=status.HTTP_404_NOT_FOUND)
                
            # Get all unread messages
            unread_messages = Message.objects.filter(
                sender=other_user,
                receiver=current_user,
                is_read=False
            )
            
            # Mark all as read
            count = 0
            for message in unread_messages:
                message.mark_as_read()
                count += 1
                
            return Response({
                'message': f'Marked {count} messages as read'
            })
            
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

class ConversationSummaryView(generics.ListAPIView):
    """Get all conversation summaries for the current user"""
    serializer_class = ConversationSummarySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get all conversations for the current user"""
        user = self.request.user
        return Message.get_conversations_summary(user)
    
    def list(self, request, *args, **kwargs):
        """List conversation summaries"""
        conversations = self.get_queryset()
        serializer = self.get_serializer(conversations, many=True)
        
        return Response({
            'count': len(conversations),
            'results': serializer.data
        })

class TypingStatusUpdateView(APIView):
    """Update typing status"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Set typing status for a recipient"""
        serializer = TypingStatusUpdateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            user = request.user
            recipient = serializer.recipient
            is_typing = serializer.validated_data['is_typing']
            
            # Update typing status
            status_obj = TypingStatus.set_typing(user, recipient, is_typing)
            
            if status_obj:
                return Response({
                    'message': 'Typing status updated',
                    'data': TypingStatusSerializer(status_obj).data
                })
            else:
                return Response({
                    'error': 'Could not update typing status'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TypingStatusView(APIView):
    """Get typing status for a specific user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, user_id):
        """Get typing status from a specific user"""
        user = request.user
        
        try:
            other_user = User.objects.get(id=user_id)
            
            # Check if they are friends
            if not Friendship.are_friends(user, other_user):
                return Response({
                    'error': 'User not found in your friends list'
                }, status=status.HTTP_404_NOT_FOUND)
                
            # Get typing status
            typing_status = TypingStatus.get_status(other_user, user)
            
            if typing_status:
                return Response({
                    'is_typing': typing_status.is_typing,
                    'timestamp': typing_status.timestamp
                })
            else:
                return Response({
                    'is_typing': False
                })
                
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

class GenerateKeyPairView(APIView):
    """Generate a new encryption key pair for the user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Generate new encryption keys"""
        serializer = KeyPairGenerationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            
            try:
                # Generate new keys
                private_key = user.generate_keys()
                
                return Response({
                    'message': 'Key pair generated successfully',
                    'private_key': private_key,
                    'warning': 'Store this private key securely! We will not store it for you.'
                })
            except Exception as e:
                return Response({
                    'error': f'Failed to generate keys: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetPublicKeyView(APIView):
    """Get the public key for a user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Get public key for a specific user"""
        serializer = PublicKeySerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            target_user = serializer.user
            
            # Check if they are friends
            if not Friendship.are_friends(request.user, target_user):
                return Response({
                    'error': 'User not found in your friends list'
                }, status=status.HTTP_404_NOT_FOUND)
                
            # Return the public key
            if target_user.public_key:
                return Response({
                    'user_id': str(target_user.id),
                    'username': target_user.username,
                    'public_key': target_user.public_key
                })
            else:
                return Response({
                    'error': 'User has not set up encryption'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeleteMessageView(APIView):
    """Soft delete a message"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, message_id):
        """Delete a message"""
        user = request.user
        
        try:
            # Find the message
            message = Message.objects.get(
                Q(sender=user) | Q(receiver=user),
                id=message_id
            )
            
            # Soft delete the message
            message.soft_delete()
            
            return Response({
                'message': 'Message deleted successfully'
            })
            
        except Message.DoesNotExist:
            return Response({
                'error': 'Message not found'
            }, status=status.HTTP_404_NOT_FOUND)