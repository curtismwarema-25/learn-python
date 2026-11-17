"""Views for the chat app."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatSession, deserialize_user
from .services import create_chat_message


def _direct_chat_or_404(uri):
    return get_object_or_404(
        ChatSession.objects.filter(space_channel__isnull=True),
        uri=uri
    )


class ChatSessionView(APIView):
    """Manage chat sessions."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """Create a new chat session."""
        with transaction.atomic():
            chat_session = ChatSession.objects.create(owner=request.user)
            chat_session.rotate_invite()

        return Response({
            'status': 'SUCCESS',
            'uri': chat_session.uri,
            'message': 'New chat session created'
        }, status=status.HTTP_201_CREATED)

    def patch(self, request, *args, **kwargs):
        """Allow the chat owner to add a member."""
        chat_session = _direct_chat_or_404(kwargs['uri'])

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
        chat_session = _direct_chat_or_404(uri)

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

        chat_session_message = create_chat_message(
            chat_session,
            request.user,
            message
        )

        return Response({
            'status': 'SUCCESS',
            'uri': chat_session.uri,
            'id': chat_session_message.id,
            'message': message,
            'user': deserialize_user(request.user)
        }, status=status.HTTP_201_CREATED)


class ChatSessionJoinView(APIView):
    """Join a chat session using its separate invite token."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        token = request.data.get('token')
        if not isinstance(token, str) or not token:
            return Response(
                {'token': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        chat_session = get_object_or_404(
            ChatSession.objects.filter(space_channel__isnull=True),
            invite_token=token
        )

        if (
            chat_session.invite_expires_at is None
            or chat_session.invite_expires_at <= timezone.now()
        ):
            raise NotFound('Invite link is invalid or expired.')

        if chat_session.owner_id != request.user.id:
            chat_session.members.get_or_create(user=request.user)

        return Response({
            'status': 'SUCCESS',
            'uri': chat_session.uri,
            'message': 'Joined chat session'
        })


class ChatSessionInviteView(APIView):
    """View and manage an owner's revocable invite link."""

    permission_classes = (permissions.IsAuthenticated,)

    def get_authorized_chat(self, request, uri):
        chat_session = _direct_chat_or_404(uri)
        if (
            chat_session.owner_id != request.user.id
            and not chat_session.members.filter(user=request.user).exists()
        ):
            raise NotFound('Chat session not found.')
        return chat_session

    def require_owner(self, chat_session, user):
        if chat_session.owner_id != user.id:
            raise PermissionDenied('Only the chat owner can manage invites.')

    def invite_response(self, chat_session, can_manage):
        active = (
            can_manage
            and chat_session.invite_token
            and chat_session.invite_expires_at
            and chat_session.invite_expires_at > timezone.now()
        )
        return {
            'can_manage': can_manage,
            'token': chat_session.invite_token if active else None,
            'expires_at': (
                chat_session.invite_expires_at if can_manage else None
            ),
        }

    def get(self, request, *args, **kwargs):
        chat_session = self.get_authorized_chat(request, kwargs['uri'])
        can_manage = chat_session.owner_id == request.user.id
        return Response(self.invite_response(chat_session, can_manage))

    def post(self, request, *args, **kwargs):
        chat_session = self.get_authorized_chat(request, kwargs['uri'])
        self.require_owner(chat_session, request.user)
        chat_session.rotate_invite()
        return Response(self.invite_response(chat_session, True))

    def delete(self, request, *args, **kwargs):
        chat_session = self.get_authorized_chat(request, kwargs['uri'])
        self.require_owner(chat_session, request.user)
        chat_session.revoke_invite()
        return Response(self.invite_response(chat_session, True))