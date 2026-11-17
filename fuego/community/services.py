"""Community operations that span Spaces and the chat message store."""

from django.db import transaction

from chat.models import ChatSession
from chat.services import create_chat_message

from .models import Channel, ResourceReference


DEFAULT_CHANNEL_NAME = 'general'
DEFAULT_CHANNEL_DESCRIPTION = 'General conversation for this Space.'


def resource_reference_to_json(resource):
    return {
        'id': str(resource.pk),
        'title': (
            'Resource removed'
            if resource.status == resource.Status.DELETED
            else resource.title
        ),
        'status': resource.status
    }


def channel_message_to_json(message):
    payload = message.to_json()
    payload['resources'] = [
        resource_reference_to_json(reference.resource)
        for reference in message.resource_references.all()
    ]
    return payload


def create_channel_message(channel, user, message, resources):
    if not resources:
        return create_chat_message(
            channel.conversation,
            user,
            message,
            publish_to_rabbitmq=False
        )

    with transaction.atomic():
        chat_message = create_chat_message(
            channel.conversation,
            user,
            message,
            publish_to_rabbitmq=False,
            message_extra_data={
                'resources': [
                    resource_reference_to_json(resource)
                    for resource in resources
                ]
            },
            defer_notification=True
        )
        ResourceReference.objects.bulk_create([
            ResourceReference(message=chat_message, resource=resource)
            for resource in resources
        ])
    return chat_message


@transaction.atomic
def create_channel(space, created_by, name, description=''):
    """Create a channel and its private conversation record together."""
    conversation = ChatSession.objects.create(owner=space.owner)
    return Channel.objects.create(
        space=space,
        conversation=conversation,
        name=name,
        description=description,
        created_by=created_by
    )


def ensure_default_channel(space):
    """Create the initial general channel when a Space has no channels."""
    if not space.channels.exists():
        return create_channel(
            space=space,
            created_by=space.owner,
            name=DEFAULT_CHANNEL_NAME,
            description=DEFAULT_CHANNEL_DESCRIPTION
        )
    return None
