"""Bridge RabbitMQ chat messages to a uWSGI WebSocket connection."""

import json
import os
import time

import pika


WEBSOCKET_AUTH_TIMEOUT_SECONDS = 5


def _receive_token(uwsgi):
    """Receive a token from the first WebSocket frame within a short deadline."""
    deadline = time.monotonic() + WEBSOCKET_AUTH_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            frame = uwsgi.websocket_recv_nb()
        except OSError:
            return None

        if frame:
            try:
                payload = json.loads(frame)
            except (TypeError, ValueError):
                return None

            if (
                isinstance(payload, dict)
                and payload.get('type') == 'authenticate'
                and isinstance(payload.get('token'), str)
                and payload['token']
            ):
                return payload['token']
            return None

        time.sleep(0.01)
    return None


def _is_chat_member(uri, token_key):
    """Allow only an active token owner or chat member to subscribe."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuego.settings')

    import django
    django.setup()

    from django.db.models import Q
    from rest_framework.authtoken.models import Token

    from chat.models import ChatSession

    token = (
        Token.objects.select_related('user')
        .filter(key=token_key)
        .first()
    )
    if token is None or not token.user.is_active:
        return False

    return (
        ChatSession.objects
        .filter(uri=uri, space_channel__isnull=True)
        .filter(
            Q(owner_id=token.user_id)
            | Q(members__user_id=token.user_id)
        )
        .exists()
    )


def application(env, start_response):
    """Subscribe to a chat exchange and forward messages to uWSGI."""
    import uwsgi

    uri = env.get('PATH_INFO', '').rstrip('/').rsplit('/', 1)[-1]

    if not uri:
        body = b'Forbidden'
        start_response('403 Forbidden', [
            ('Content-Type', 'text/plain'),
            ('Content-Length', str(len(body)))
        ])
        return [body]

    uwsgi.websocket_handshake(
        env['HTTP_SEC_WEBSOCKET_KEY'],
        env.get('HTTP_ORIGIN', '')
    )
    token_key = _receive_token(uwsgi)
    if not token_key or not _is_chat_member(uri, token_key):
        return []

    uwsgi.websocket_send(json.dumps({'type': 'authenticated'}))

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=os.environ.get('CHAT_RABBITMQ_HOST', 'localhost')
        )
    )
    channel = None

    try:
        channel = connection.channel()
        channel.exchange_declare(
            exchange=uri,
            exchange_type='fanout'
        )

        result = channel.queue_declare(exclusive=True)
        queue_name = result.method.queue
        channel.queue_bind(exchange=uri, queue=queue_name)

        for method_frame, _, body in channel.consume(
            queue_name,
            inactivity_timeout=30
        ):
            if method_frame is None:
                try:
                    uwsgi.websocket_recv_nb()
                except OSError:
                    break
                continue

            try:
                uwsgi.websocket_send(body)
            except OSError:
                break
            else:
                channel.basic_ack(method_frame.delivery_tag)

        return []
    finally:
        try:
            if channel is not None and channel.is_open:
                channel.cancel()
        finally:
            if connection.is_open:
                connection.close()
