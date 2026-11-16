"""RabbitMQ notification channel used by the optional uWSGI WebSocket bridge."""

import json

import pika
from django.conf import settings

from notifications.channels import BaseNotificationChannel
from notifications.providers.base import BaseNotificationProvider


class RabbitMQNotificationProvider(BaseNotificationProvider):
    """Publish a chat message to the exchange consumed by the WSGI bridge."""

    name = 'rabbitmq'

    def send(self, payload):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=settings.CHAT_RABBITMQ_HOST)
        )
        try:
            channel = connection.channel()
            channel.exchange_declare(
                exchange=payload['uri'],
                exchange_type='fanout'
            )
            channel.basic_publish(
                exchange=payload['uri'],
                routing_key='',
                body=json.dumps(payload['message']).encode('utf-8')
            )
        finally:
            if connection.is_open:
                connection.close()


class RabbitMQWebSocketChannel(BaseNotificationChannel):
    """Deliver chat messages through RabbitMQ."""

    name = 'rabbitmq'
    providers = ['rabbitmq']

    def build_payload(self, _provider):
        _ = _provider
        return {
            'uri': self.context['uri'],
            'message': self.context['message']
        }