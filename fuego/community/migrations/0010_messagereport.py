from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chat', '0004_chatsessionmessage_deleted_at_and_more'),
        ('community', '0009_knowledgeindexingjob_embedding_attempt_count_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(max_length=500)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('reviewed', 'Reviewed'), ('dismissed', 'Dismissed'), ('actioned', 'Actioned')], default='pending', max_length=10)),
                ('moderator_notes', models.CharField(blank=True, max_length=500)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='message_reports', to='community.channel')),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='reports', to='chat.chatsessionmessage')),
                ('reported_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='submitted_message_reports', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='reviewed_message_reports', to=settings.AUTH_USER_MODEL)),
                ('space', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='message_reports', to='community.space')),
            ],
            options={'ordering': ('status', '-create_date', '-id')},
        ),
        migrations.AddConstraint(
            model_name='messagereport',
            constraint=models.UniqueConstraint(fields=('message', 'reported_by'), name='uniq_message_reporter'),
        ),
    ]
