"""
ASGI config for fuego project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuego.settings')

django_asgi_application = get_asgi_application()

from chat.routing import websocket_urlpatterns
from community.routing import websocket_urlpatterns as community_websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_application,
    'websocket': URLRouter(
        [*websocket_urlpatterns, *community_websocket_urlpatterns]
    ),
})
