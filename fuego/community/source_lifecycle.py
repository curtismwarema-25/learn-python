"""Transactional lifecycle operations for Space channel source messages."""

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from chat.models import ChatSessionMessage, ChatSessionMessageRevision
from notifications.utils import notify

from .models import PreservedKnowledge
from .indexing import invalidate_knowledge_index
from .services import channel_message_to_json


def _publish_source_event(message, user, payload, action, description):
    def publish():
        notify(
            source=user,
            source_display_name=user.get_full_name(),
            category='chat',
            action=action,
            obj=message,
            short_description=description,
            silent=True,
            channels=['websocket'],
            extra_data={
                'uri': message.chat_session.uri,
                'context': {
                    'channel_layer': 'default',
                    'destination': 'chat_%s' % message.chat_session.uri,
                    'uri': message.chat_session.uri,
                    'message': payload
                }
            }
        )

    transaction.on_commit(publish)


@transaction.atomic
def edit_channel_message(message, user, content):
    """Capture the old source and edit the message atomically."""
    locked = ChatSessionMessage.objects.select_for_update().select_related(
        'chat_session'
    ).get(pk=message.pk)
    if locked.deleted_at is not None:
        raise ValidationError('Deleted messages cannot be edited.')

    latest = locked.revisions.aggregate(latest=Max('revision_number'))['latest'] or 0
    ChatSessionMessageRevision.objects.create(
        message=locked,
        revision_number=latest + 1,
        content=locked.message,
        changed_by=user
    )
    locked.message = content
    locked.save(update_fields=('message', 'update_date'))
    affected = list(PreservedKnowledge.objects.filter(
        source_message=locked,
        status=PreservedKnowledge.Status.ACTIVE
    ))
    PreservedKnowledge.objects.filter(
        pk__in=[knowledge.pk for knowledge in affected]
    ).update(status=PreservedKnowledge.Status.NEEDS_REVIEW)
    for knowledge in affected:
        invalidate_knowledge_index(knowledge)
    _publish_source_event(
        locked,
        user,
        {
            'type': 'message_updated',
            **channel_message_to_json(locked)
        },
        'Edited',
        'A Space channel message was edited'
    )
    return locked


@transaction.atomic
def delete_channel_message(message, user):
    """Soft-delete a source message and suspend dependent knowledge."""
    locked = ChatSessionMessage.objects.select_for_update().select_related(
        'chat_session'
    ).get(pk=message.pk)
    if locked.deleted_at is not None:
        raise ValidationError('This message is already deleted.')

    locked.deleted_at = timezone.now()
    locked.deleted_by = user
    locked.save(update_fields=('deleted_at', 'deleted_by', 'update_date'))
    affected = list(PreservedKnowledge.objects.filter(
        source_message=locked,
        status__in=(
            PreservedKnowledge.Status.ACTIVE,
            PreservedKnowledge.Status.NEEDS_REVIEW
        )
    ))
    PreservedKnowledge.objects.filter(
        pk__in=[knowledge.pk for knowledge in affected]
    ).update(status=PreservedKnowledge.Status.SOURCE_DELETED)
    for knowledge in affected:
        invalidate_knowledge_index(knowledge)
    _publish_source_event(
        locked,
        user,
        {'type': 'message_deleted', 'id': locked.pk},
        'Deleted',
        'A Space channel message was deleted'
    )
    return locked
