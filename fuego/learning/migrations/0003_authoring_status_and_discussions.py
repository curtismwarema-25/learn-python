from django.db import migrations, models
import django.db.models.deletion


def mark_existing_published(apps, schema_editor):
    Pathway = apps.get_model('learning', 'LearningPathway')
    Pathway.objects.filter(published=True).update(status='published')


class Migration(migrations.Migration):
    dependencies = [
        ('chat', '0004_chatsessionmessage_deleted_at_and_more'),
        ('community', '0009_knowledgeindexingjob_embedding_attempt_count_and_more'),
        ('learning', '0002_seed_ai_awareness'),
    ]
    operations = [
        migrations.AddField(
            model_name='learningpathway',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='created_learning_pathways', to='auth.user'),
        ),
        migrations.AddField(
            model_name='learningpathway',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('published', 'Published'), ('archived', 'Archived')], default='draft', max_length=10),
        ),
        migrations.CreateModel(
            name='LearningDiscussionLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='learning_discussion_links', to='community.channel')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_learning_discussion_links', to='auth.user')),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discussion_links', to='learning.learninglesson')),
                ('source_message', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='learning_discussion_links', to='chat.chatsessionmessage')),
                ('space', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='learning_discussion_links', to='community.space')),
            ],
            options={'ordering': ('create_date', 'id')},
        ),
        migrations.AddConstraint(
            model_name='learningdiscussionlink',
            constraint=models.UniqueConstraint(fields=('lesson', 'channel', 'source_message'), name='uniq_learning_discussion_link'),
        ),
        migrations.RunPython(mark_existing_published, migrations.RunPython.noop),
    ]
