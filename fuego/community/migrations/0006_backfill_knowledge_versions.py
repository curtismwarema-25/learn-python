from django.db import migrations


def create_initial_versions(apps, schema_editor):
    PreservedKnowledge = apps.get_model('community', 'PreservedKnowledge')
    KnowledgeVersion = apps.get_model('community', 'KnowledgeVersion')

    for knowledge in PreservedKnowledge.objects.filter(current_version__isnull=True).iterator():
        version = KnowledgeVersion.objects.create(
            knowledge_id=knowledge.pk,
            source_message_id=knowledge.source_message_id,
            version_number=1,
            content=knowledge.source_message.message,
            created_by_id=knowledge.preserved_by_id
        )
        PreservedKnowledge.objects.filter(pk=knowledge.pk).update(
            current_version_id=version.pk
        )


class Migration(migrations.Migration):
    dependencies = [
        ('community', '0005_knowledgeversion_preservedknowledge_current_version_and_more'),
    ]

    operations = [
        migrations.RunPython(create_initial_versions, migrations.RunPython.noop),
    ]
