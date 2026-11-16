"""WebSocket URL routes for the chat app."""

from django.urls import path

from .consumers import ChatConsumer


websocket_urlpatterns = [
    path('ws/chats/<str:uri>/', ChatConsumer.as_asgi()),
]
