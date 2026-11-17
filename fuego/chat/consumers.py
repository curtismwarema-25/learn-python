"""WebSocket consumers for chat messages."""

import asyncio
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q
from rest_framework.authtoken.models import Token

from .models import ChatSession


AUTHENTICATION_TIMEOUT_SECONDS = 5


class ChatConsumer(AsyncWebsocketConsumer):
    """Deliver messages only to currently authorized chat participants."""

    async def connect(self):
        self.uri = self.scope['url_route']['kwargs']['uri']
        await self.start_authenticated_connection()

    async def start_authenticated_connection(self):
        self.group_name = 'chat_%s' % self.uri
        self.authenticated = False
        await self.accept()
        self.auth_timeout_task = asyncio.create_task(
            self.close_if_unauthenticated()
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'auth_timeout_task'):
            self.auth_timeout_task.cancel()
        if self.authenticated:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data=None, bytes_data=None):
        if not self.authenticated:
            try:
                payload = json.loads(text_data or '')
            except (TypeError, ValueError):
                await self.close(code=4401)
                return

            if (
                not isinstance(payload, dict)
                or payload.get('type') != 'authenticate'
                or not isinstance(payload.get('token'), str)
                or not payload['token']
            ):
                await self.close(code=4401)
                return

            token_key = payload['token']
            user = await self.get_user_for_token(token_key)
            if user is None:
                await self.close(code=4401)
                return
            if not await self.user_can_access_chat(user.pk, self.uri):
                await self.close(code=4403)
                return

            self.user_id = user.pk
            self.token_key = token_key
            self.authenticated = True
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            self.auth_timeout_task.cancel()
            await self.send(text_data=json.dumps({'type': 'authenticated'}))
            return

        if not await self.connection_is_authorized(
            self.token_key,
            self.user_id,
            self.uri
        ):
            await self.close(code=4403)

    async def notifs_websocket_message(self, event):
        """Forward django-notifs websocket events to the connected client."""
        if not self.authenticated or not await self.connection_is_authorized(
            self.token_key,
            self.user_id,
            self.uri
        ):
            await self.close(code=4403)
            return
        await self.send(text_data=event['message'])

    async def close_if_unauthenticated(self):
        await asyncio.sleep(AUTHENTICATION_TIMEOUT_SECONDS)
        if not self.authenticated:
            await self.close(code=4401)

    @database_sync_to_async
    def get_user_for_token(self, token_key):
        token = (
            Token.objects
            .select_related('user')
            .filter(key=token_key)
            .first()
        )
        if token is None or not token.user.is_active:
            return None
        return token.user

    @database_sync_to_async
    def user_can_access_chat(self, user_id, uri):
        return self._user_can_access_chat(user_id, uri)

    def _user_can_access_chat(self, user_id, uri):
        return (
            ChatSession.objects
            .filter(uri=uri, space_channel__isnull=True)
            .filter(
                Q(owner_id=user_id) | Q(members__user_id=user_id)
            )
            .exists()
        )

    @database_sync_to_async
    def connection_is_authorized(self, token_key, user_id, uri):
        token_is_valid = Token.objects.filter(
            key=token_key,
            user_id=user_id,
            user__is_active=True
        ).exists()
        return token_is_valid and self._user_can_access_chat(user_id, uri)
