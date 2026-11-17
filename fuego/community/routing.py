"""WebSocket URL routes for Space channels."""

from django.urls import path

from .consumers import SpaceChannelConsumer


websocket_urlpatterns = [
    path(
        'ws/spaces/<uuid:space_id>/channels/<uuid:channel_id>/',
        SpaceChannelConsumer.as_asgi()
    ),
]
