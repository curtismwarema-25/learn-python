"""Models for Fuego Spaces and their membership lifecycle."""

from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


User = get_user_model()
SPACE_INVITE_LIFETIME = timedelta(days=7)


class Space(models.Model):
    """A persistent community environment with controlled visibility."""

    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Private'
        DISCOVERABLE = 'discoverable', 'Discoverable'

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    owner = models.ForeignKey(
        User,
        related_name='owned_spaces',
        on_delete=models.PROTECT
    )
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=280, blank=True)
    purpose = models.CharField(max_length=160)
    visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.PRIVATE
    )
    invite_token = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        unique=True
    )
    invite_expires_at = models.DateTimeField(null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    def rotate_invite(self):
        """Create a new seven-day link, invalidating the previous link."""
        self.invite_token = uuid4().hex
        self.invite_expires_at = timezone.now() + SPACE_INVITE_LIFETIME
        self.save(
            update_fields=('invite_token', 'invite_expires_at', 'update_date')
        )

    def revoke_invite(self):
        """Invalidate the current invite link."""
        self.invite_token = None
        self.invite_expires_at = None
        self.save(
            update_fields=('invite_token', 'invite_expires_at', 'update_date')
        )


class Channel(models.Model):
    """A Space conversation backed by the existing chat message stream."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    space = models.ForeignKey(
        Space,
        related_name='channels',
        on_delete=models.PROTECT
    )
    conversation = models.OneToOneField(
        'chat.ChatSession',
        related_name='space_channel',
        on_delete=models.CASCADE
    )
    name = models.SlugField(max_length=50)
    description = models.CharField(max_length=280, blank=True)
    created_by = models.ForeignKey(
        User,
        related_name='created_space_channels',
        on_delete=models.PROTECT
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('space', 'name'),
                name='uniq_channel_name_per_space'
            )
        ]


class Resource(models.Model):
    """A Space-scoped item preserved independently from its discussion."""

    class Type(models.TextChoices):
        LINK = 'link', 'Link'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'
        DELETED = 'deleted', 'Deleted'

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    space = models.ForeignKey(
        Space,
        related_name='resources',
        on_delete=models.CASCADE
    )
    type = models.CharField(
        max_length=16,
        choices=Type.choices,
        default=Type.LINK
    )
    title = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    external_url = models.URLField(max_length=2048, blank=True)
    created_by = models.ForeignKey(
        User,
        related_name='created_space_resources',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)


class ResourceReference(models.Model):
    """A structured reference from a channel message to its Space resource."""

    message = models.ForeignKey(
        'chat.ChatSessionMessage',
        related_name='resource_references',
        on_delete=models.CASCADE
    )
    resource = models.ForeignKey(
        Resource,
        related_name='message_references',
        on_delete=models.PROTECT
    )
    create_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('message', 'resource'),
                name='uniq_resource_reference_per_message'
            )
        ]


class MessageReport(models.Model):
    """A member report for one message in a Space channel."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        REVIEWED = 'reviewed', 'Reviewed'
        DISMISSED = 'dismissed', 'Dismissed'
        ACTIONED = 'actioned', 'Actioned'

    space = models.ForeignKey(Space, related_name='message_reports', on_delete=models.PROTECT)
    channel = models.ForeignKey('Channel', related_name='message_reports', on_delete=models.PROTECT)
    message = models.ForeignKey('chat.ChatSessionMessage', related_name='reports', on_delete=models.PROTECT)
    reported_by = models.ForeignKey(User, related_name='submitted_message_reports', on_delete=models.PROTECT)
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    moderator_notes = models.CharField(max_length=500, blank=True)
    reviewed_by = models.ForeignKey(
        User, related_name='reviewed_message_reports', on_delete=models.PROTECT,
        null=True, blank=True
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('message', 'reported_by'), name='uniq_message_reporter')
        ]
        ordering = ('status', '-create_date', '-id')


class PreservedKnowledge(models.Model):
    """A traceable, Space-scoped preservation of one channel message."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        NEEDS_REVIEW = 'needs_review', 'Needs review'
        SOURCE_DELETED = 'source_deleted', 'Source deleted'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    space = models.ForeignKey(
        Space,
        related_name='preserved_knowledge',
        on_delete=models.PROTECT
    )
    source_message = models.OneToOneField(
        'chat.ChatSessionMessage',
        related_name='preserved_knowledge',
        on_delete=models.PROTECT
    )
    preserved_by = models.ForeignKey(
        User,
        related_name='preserved_knowledge',
        on_delete=models.PROTECT
    )
    status = models.CharField(
        max_length=14,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    preserved_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawn_by = models.ForeignKey(
        User,
        related_name='withdrawn_knowledge',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    current_version = models.ForeignKey(
        'KnowledgeVersion',
        related_name='current_knowledge',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status__in=('active', 'needs_review', 'source_deleted'),
                        withdrawn_at__isnull=True
                    )
                    | models.Q(status='withdrawn', withdrawn_at__isnull=False)
                ),
                name='knowledge_withdrawal_fields_consistent'
            )
        ]


class KnowledgeVersion(models.Model):
    """Immutable snapshot of one preserved knowledge record."""

    knowledge = models.ForeignKey(
        PreservedKnowledge,
        related_name='versions',
        on_delete=models.PROTECT
    )
    source_message = models.ForeignKey(
        'chat.ChatSessionMessage',
        related_name='knowledge_versions',
        on_delete=models.PROTECT
    )
    version_number = models.PositiveIntegerField()
    content = models.TextField(max_length=2000)
    explanation = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        User,
        related_name='created_knowledge_versions',
        on_delete=models.PROTECT
    )
    create_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('knowledge', 'version_number'),
                name='uniq_knowledge_version_number'
            )
        ]


class KnowledgeIndexingJob(models.Model):
    """Materialization state for one immutable knowledge version."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        INDEXED = 'indexed', 'Indexed'
        FAILED = 'failed', 'Failed'
        OBSOLETE = 'obsolete', 'Obsolete'

    class EmbeddingStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETE = 'complete', 'Complete'
        FAILED = 'failed', 'Failed'
        OBSOLETE = 'obsolete', 'Obsolete'

    knowledge = models.ForeignKey(
        PreservedKnowledge,
        related_name='indexing_jobs',
        on_delete=models.PROTECT
    )
    version = models.ForeignKey(
        KnowledgeVersion,
        related_name='indexing_jobs',
        on_delete=models.PROTECT
    )
    space = models.ForeignKey(
        Space,
        related_name='knowledge_indexing_jobs',
        on_delete=models.PROTECT
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    attempt_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    embedding_status = models.CharField(
        max_length=10,
        choices=EmbeddingStatus.choices,
        default=EmbeddingStatus.PENDING
    )
    embedding_provider = models.CharField(max_length=80, blank=True)
    embedding_model = models.CharField(max_length=120, blank=True)
    embedding_attempt_count = models.PositiveIntegerField(default=0)
    embedding_error = models.TextField(blank=True)
    embedding_started_at = models.DateTimeField(null=True, blank=True)
    embedding_completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('knowledge', 'version'),
                name='uniq_knowledge_indexing_job_version'
            )
        ]
        indexes = [
            models.Index(fields=('space', 'status'), name='knowledge_job_space_status')
        ]


class KnowledgeIndexChunk(models.Model):
    """Database-backed retrieval unit, ready for a future embedding field."""

    job = models.ForeignKey(
        KnowledgeIndexingJob,
        related_name='chunks',
        on_delete=models.PROTECT
    )
    space = models.ForeignKey(
        Space,
        related_name='knowledge_index_chunks',
        on_delete=models.PROTECT
    )
    knowledge = models.ForeignKey(
        PreservedKnowledge,
        related_name='index_chunks',
        on_delete=models.PROTECT
    )
    version = models.ForeignKey(
        KnowledgeVersion,
        related_name='index_chunks',
        on_delete=models.PROTECT
    )
    source_message = models.ForeignKey(
        'chat.ChatSessionMessage',
        related_name='knowledge_index_chunks',
        on_delete=models.PROTECT
    )
    chunk_index = models.PositiveIntegerField()
    content = models.TextField(max_length=1200)
    start_offset = models.PositiveIntegerField()
    end_offset = models.PositiveIntegerField()
    source_author = models.CharField(max_length=150)
    source_channel_id = models.UUIDField()
    source_message_created_at = models.DateTimeField()
    create_date = models.DateTimeField(auto_now_add=True)
    invalidated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('job', 'chunk_index'),
                name='uniq_index_chunk_position'
            )
        ]
        indexes = [
            models.Index(
                fields=('space', 'knowledge', 'version'),
                name='knowledge_chunk_lookup'
            )
        ]


class KnowledgeChunkEmbedding(models.Model):
    """A replaceable vector materialization for one indexed chunk."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        READY = 'ready', 'Ready'
        FAILED = 'failed', 'Failed'
        OBSOLETE = 'obsolete', 'Obsolete'

    chunk = models.ForeignKey(
        KnowledgeIndexChunk,
        related_name='embeddings',
        on_delete=models.PROTECT
    )
    space = models.ForeignKey(
        Space,
        related_name='knowledge_chunk_embeddings',
        on_delete=models.PROTECT
    )
    knowledge_version = models.ForeignKey(
        KnowledgeVersion,
        related_name='chunk_embeddings',
        on_delete=models.PROTECT
    )
    provider = models.CharField(max_length=80)
    model = models.CharField(max_length=120)
    dimensions = models.PositiveIntegerField()
    vector = models.JSONField(default=list)
    status = models.CharField(
        max_length=8,
        choices=Status.choices,
        default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('chunk', 'provider', 'model'),
                name='uniq_chunk_embedding_provider_model'
            )
        ]
        indexes = [
            models.Index(
                fields=('space', 'knowledge_version', 'status'),
                name='embedding_space_version_status'
            )
        ]


class SpaceMembership(models.Model):
    """An active non-owner member of a Space."""

    class Role(models.TextChoices):
        ADMINISTRATOR = 'administrator', 'Administrator'
        MODERATOR = 'moderator', 'Moderator'
        MEMBER = 'member', 'Member'

    space = models.ForeignKey(
        Space,
        related_name='memberships',
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User,
        related_name='space_memberships',
        on_delete=models.PROTECT
    )
    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.MEMBER
    )
    create_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('space', 'user'),
                name='uniq_space_membership_user'
            )
        ]


class SpaceJoinRequest(models.Model):
    """A request by an authenticated user to join a discoverable Space."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        DENIED = 'denied', 'Denied'
        CANCELLED = 'cancelled', 'Cancelled'

    space = models.ForeignKey(
        Space,
        related_name='join_requests',
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User,
        related_name='space_join_requests',
        on_delete=models.PROTECT
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        related_name='reviewed_space_join_requests',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('space', 'user'),
                name='uniq_space_join_request_user'
            )
        ]
