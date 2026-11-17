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
