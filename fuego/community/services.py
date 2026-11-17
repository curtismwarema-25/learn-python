"""Community operations that span Spaces and the chat message store."""

from django.db import transaction

from chat.models import ChatSession

from .models import Channel


DEFAULT_CHANNEL_NAME = 'general'
DEFAULT_CHANNEL_DESCRIPTION = 'General conversation for this Space.'


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
