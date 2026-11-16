"""Views for the chat app."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from notifications.utils import notify

from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .channels import RabbitMQWebSocketChannel
from .models import ChatSession, ChatSessionMessage, deserialize_user


class ChatSessionView(APIView):
    """Manage chat sessions."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """Create a new chat session."""
        chat_session = ChatSession.objects.create(owner=request.user)

        return Response({
            'status': 'SUCCESS',
            'uri': chat_session.uri,
            'message': 'New chat session created'
        }, status=status.HTTP_201_CREATED)

    def patch(self, request, *args, **kwargs):
        """Allow the chat owner to add a member."""
        chat_session = get_object_or_404(
            ChatSession,
            uri=kwargs['uri']
        )

        if chat_session.owner_id != request.user.id:
            raise PermissionDenied(
                'Only the chat owner can add members.'
            )

        username = request.data.get('username')

        if not username:
            return Response(
                {'username': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        User = get_user_model()
        user = get_object_or_404(User, username=username)

        if user != chat_session.owner:
            chat_session.members.get_or_create(user=user)

        members = [
            deserialize_user(member.user)
            for member in chat_session.members.select_related('user').all()
        ]

        members.insert(0, deserialize_user(chat_session.owner))

        return Response({
            'status': 'SUCCESS',
            'members': members,
            'message': '%s joined the chat' % user.username,
            'user': deserialize_user(user)
        })


class ChatSessionMessageView(APIView):
    """Create and retrieve chat session messages."""

    permission_classes = (permissions.IsAuthenticated,)

    def get_authorized_chat(self, request, uri):
        """Return a chat only if the requester belongs to it."""
        chat_session = get_object_or_404(ChatSession, uri=uri)

        is_owner = chat_session.owner_id == request.user.id
        is_member = chat_session.members.filter(
            user=request.user
        ).exists()

        if not (is_owner or is_member):
            # Avoid revealing whether a private chat exists.
            from rest_framework.exceptions import NotFound
            raise NotFound('Chat session not found.')

        return chat_session

    def get(self, request, *args, **kwargs):
        """Return messages for an authorized chat member."""
        chat_session = self.get_authorized_chat(
            request,
            kwargs['uri']
        )

        messages = [
            message.to_json()
            for message in chat_session.messages.select_related('user').all()
        ]

        return Response({
            'id': chat_session.id,
            'uri': chat_session.uri,
            'messages': messages
        })

    def post(self, request, *args, **kwargs):
        """Create a message in an authorized chat."""
        chat_session = self.get_authorized_chat(
            request,
            kwargs['uri']
        )

        message = request.data.get('message')

        if not isinstance(message, str) or not message.strip():
            return Response(
                {'message': ['A non-empty message is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(message) > 2000:
            return Response(
                {'message': ['Ensure this field has no more than 2000 characters.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        chat_session_message = ChatSessionMessage.objects.create(
            user=request.user,
            chat_session=chat_session,
            message=message
        )

        notification_message = {
            'id': chat_session_message.id,
            'user': deserialize_user(request.user),
            'message': message
        }
        notification_channels = ['websocket']
        if settings.CHAT_RABBITMQ_ENABLED:
            notification_channels.append(RabbitMQWebSocketChannel.name)

        notify(
            source=request.user,
            source_display_name=request.user.get_full_name(),
            category='chat',
            action='Sent',
            obj=chat_session_message,
            short_description='Sent a new message',
            silent=True,
            channels=notification_channels,
            extra_data={
                'uri': chat_session.uri,
                'context': {
                    'channel_layer': 'default',
                    'destination': 'chat_%s' % chat_session.uri,
                    'uri': chat_session.uri,
                    'message': notification_message
                }
            }
        )

        return Response({
            'status': 'SUCCESS',
            'uri': chat_session.uri,
            'id': chat_session_message.id,
            'message': message,
            'user': deserialize_user(request.user)
        }, status=status.HTTP_201_CREATED)


class ChatSessionJoinView(APIView):
    """Join a chat session using its invite URI."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        chat_session = get_object_or_404(
            ChatSession,
            uri=kwargs['uri']
        )

        if chat_session.owner_id != request.user.id:
            chat_session.members.get_or_create(user=request.user)

        return Response({
            'status': 'SUCCESS',
            'uri': chat_session.uri,
            'message': 'Joined chat session'
        })