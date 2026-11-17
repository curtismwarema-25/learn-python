"""WebSocket consumers for Space channel conversations."""

from channels.db import database_sync_to_async
from django.db.models import Q

from chat.consumers import ChatConsumer

from .models import Channel


class SpaceChannelConsumer(ChatConsumer):
    """Reuse chat event delivery while authorizing through Space membership."""

    async def connect(self):
        route = self.scope['url_route']['kwargs']
        self.space_id = route['space_id']
        self.channel_id = route['channel_id']
        self.uri = await self.get_active_channel_uri()
        if self.uri is None:
            await self.close(code=4404)
            return
        await self.start_authenticated_connection()

    @database_sync_to_async
    def get_active_channel_uri(self):
        return (
            Channel.objects
            .filter(
                pk=self.channel_id,
                space_id=self.space_id,
                archived_at__isnull=True
            )
            .values_list('conversation__uri', flat=True)
            .first()
        )

    def _user_can_access_chat(self, user_id, uri):
        return (
            Channel.objects
            .filter(
                pk=self.channel_id,
                space_id=self.space_id,
                conversation__uri=uri,
                archived_at__isnull=True
            )
            .filter(
                Q(space__owner_id=user_id)
                | Q(space__memberships__user_id=user_id)
            )
            .exists()
        )
