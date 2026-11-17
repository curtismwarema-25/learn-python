from datetime import timedelta
from uuid import uuid4

from django.db import migrations, models
from django.utils import timezone


def create_invites_for_existing_chats(apps, schema_editor):
    ChatSession = apps.get_model('chat', 'ChatSession')
    database = schema_editor.connection.alias
    expires_at = timezone.now() + timedelta(days=7)

    for chat_session in ChatSession.objects.using(database).iterator():
        chat_session.invite_token = uuid4().hex
        chat_session.invite_expires_at = expires_at
        chat_session.save(
            using=database,
            update_fields=('invite_token', 'invite_expires_at')
        )


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_alter_chatsession_uri_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatsession',
            name='invite_token',
            field=models.CharField(
                blank=True,
                max_length=32,
                null=True,
                unique=True
            ),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='invite_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            create_invites_for_existing_chats,
            migrations.RunPython.noop
        ),
    ]
