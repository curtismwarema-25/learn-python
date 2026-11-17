"""Shared message persistence and notification operations."""

from django.conf import settings
from django.db import transaction

from notifications.utils import notify

from .channels import RabbitMQWebSocketChannel
from .models import ChatSessionMessage, deserialize_user


def create_chat_message(
    chat_session,
    user,
    message,
    *,
    publish_to_rabbitmq=True,
    message_extra_data=None,
    defer_notification=False
):
    chat_message = ChatSessionMessage.objects.create(
        user=user,
        chat_session=chat_session,
        message=message
    )
    notification_channels = ['websocket']
    if publish_to_rabbitmq and settings.CHAT_RABBITMQ_ENABLED:
        notification_channels.append(RabbitMQWebSocketChannel.name)

    message_data = {
        'id': chat_message.id,
        'user': deserialize_user(user),
        'message': message
    }
    if message_extra_data:
        message_data.update(message_extra_data)

    def publish_notification():
        notify(
            source=user,
            source_display_name=user.get_full_name(),
            category='chat',
            action='Sent',
            obj=chat_message,
            short_description='Sent a new message',
            silent=True,
            channels=notification_channels,
            extra_data={
                'uri': chat_session.uri,
                'context': {
                    'channel_layer': 'default',
                    'destination': 'chat_%s' % chat_session.uri,
                    'uri': chat_session.uri,
                    'message': message_data
                }
            }
        )

    if defer_notification:
        transaction.on_commit(publish_notification)
    else:
        publish_notification()
    return chat_message
