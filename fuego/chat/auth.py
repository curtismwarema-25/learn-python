"""Authentication middleware for chat WebSocket connections."""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token


class TokenAuthMiddleware:
    """Resolve a DRF token supplied in the WebSocket query string."""

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        query = parse_qs(scope.get('query_string', b'').decode('utf-8'))
        token_key = query.get('token', [''])[0]
        scope['user'] = await self.get_user(token_key)
        return await self.application(scope, receive, send)

    @database_sync_to_async
    def get_user(self, token_key):
        if not token_key:
            return AnonymousUser()

        try:
            token = Token.objects.select_related('user').get(key=token_key)
        except Token.DoesNotExist:
            return AnonymousUser()

        if not token.user.is_active:
            return AnonymousUser()

        return token.user
