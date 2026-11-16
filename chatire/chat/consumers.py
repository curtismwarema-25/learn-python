"""WebSocket consumers for chat messages."""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q

from .models import ChatSession


class ChatConsumer(AsyncWebsocketConsumer):
    """Deliver messages only to authenticated chat participants."""

    async def connect(self):
        self.uri = self.scope['url_route']['kwargs']['uri']
        user = self.scope['user']

        if (
            not user.is_authenticated
            or not await self.user_can_access_chat(user.pk, self.uri)
        ):
            await self.close(code=4403)
            return

        self.group_name = 'chat_%s' % self.uri
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def notifs_websocket_message(self, event):
        """Forward django-notifs websocket events to the connected client."""
        await self.send(text_data=event['message'])

    @database_sync_to_async
    def user_can_access_chat(self, user_id, uri):
        return (
            ChatSession.objects
            .filter(uri=uri)
            .filter(
                Q(owner_id=user_id) | Q(members__user_id=user_id)
            )
            .exists()
        )
