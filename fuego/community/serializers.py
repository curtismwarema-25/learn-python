"""Validated API contracts for the Community domain."""

import re
from django.utils import timezone
from urllib.parse import urlsplit

from rest_framework import serializers

from chat.models import ChatSessionMessageRevision

from .models import (
    Channel,
    KnowledgeVersion,
    PreservedKnowledge,
    Resource,
    Space,
    SpaceJoinRequest,
    SpaceMembership
)
from .permissions import (
    MANAGER_ROLES,
    MODERATOR,
    OWNER,
    get_space_role
)


class SpaceTextValidationMixin:
    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError('A Space name is required.')
        return value.strip()

    def validate_purpose(self, value):
        if not value.strip():
            raise serializers.ValidationError('A Space purpose is required.')
        return value.strip()

    def validate_description(self, value):
        return value.strip()


class SpaceCreateSerializer(SpaceTextValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Space
        fields = ('name', 'description', 'purpose', 'visibility')


class SpaceUpdateSerializer(SpaceTextValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Space
        fields = ('name', 'description', 'purpose', 'visibility')


class SpaceMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Space
        fields = ('id', 'name', 'description', 'purpose')


class SpaceSummarySerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = Space
        fields = (
            'id',
            'name',
            'description',
            'purpose',
            'visibility',
            'role'
        )

    def get_role(self, obj):
        user = self.context['request'].user
        if obj.owner_id == user.pk:
            return OWNER
        prefetched = getattr(obj, '_current_user_memberships', None)
        if prefetched is not None:
            return prefetched[0].role if prefetched else None
        return get_space_role(obj, user)


class SpaceDetailSerializer(SpaceMetadataSerializer):
    visibility = serializers.CharField()
    role = serializers.SerializerMethodField()
    membership_status = serializers.SerializerMethodField()

    class Meta(SpaceMetadataSerializer.Meta):
        fields = SpaceMetadataSerializer.Meta.fields + (
            'visibility',
            'role',
            'membership_status'
        )

    def get_role(self, _obj):
        return self.context.get('role')

    def get_membership_status(self, _obj):
        return self.context.get('membership_status', 'none')


class SpaceMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = SpaceMembership
        fields = ('user_id', 'username', 'role', 'create_date')


class SpaceJoinRequestSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = SpaceJoinRequest
        fields = ('id', 'user_id', 'username', 'status', 'requested_at')


class SpaceRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=SpaceMembership.Role.choices)


class SpaceInviteJoinSerializer(serializers.Serializer):
    token = serializers.CharField(min_length=1, max_length=32)


class SpaceOwnershipTransferSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)


class ChannelCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ('name', 'description')

    def validate_name(self, value):
        return value.strip().lower()

    def validate_description(self, value):
        return value.strip()


class ChannelUpdateSerializer(serializers.ModelSerializer):
    archived = serializers.BooleanField(required=False)

    class Meta:
        model = Channel
        fields = ('name', 'description', 'archived')

    def validate_name(self, value):
        return value.strip().lower()

    def validate_description(self, value):
        return value.strip()

    def update(self, instance, validated_data):
        archived = validated_data.pop('archived', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if archived is not None:
            instance.archived_at = timezone.now() if archived else None
        instance.save()
        return instance


class ChannelSerializer(serializers.ModelSerializer):
    archived = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )

    class Meta:
        model = Channel
        fields = (
            'id',
            'name',
            'description',
            'archived',
            'created_by_username',
            'create_date',
            'update_date'
        )

    def get_archived(self, obj):
        return obj.archived_at is not None


class PreservedKnowledgeCreateSerializer(serializers.Serializer):
    message_id = serializers.IntegerField(min_value=1)


class KnowledgeCorrectionSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=2000)
    explanation = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_content(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Corrected content is required.')
        return value

    def validate_explanation(self, value):
        return value.strip()


class KnowledgeVersionSerializer(serializers.ModelSerializer):
    source_message_id = serializers.IntegerField(read_only=True)
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeVersion
        fields = (
            'id',
            'version_number',
            'content',
            'explanation',
            'source_message_id',
            'created_by_username',
            'create_date',
            'is_current'
        )

    def get_is_current(self, obj):
        return obj.knowledge.current_version_id == obj.pk


class PreservedKnowledgeSerializer(serializers.ModelSerializer):
    source_message_id = serializers.IntegerField(read_only=True)
    source_message = serializers.SerializerMethodField()
    preserved_by_username = serializers.CharField(
        source='preserved_by.username',
        read_only=True
    )
    withdrawn_by_username = serializers.CharField(
        source='withdrawn_by.username',
        read_only=True,
        allow_null=True
    )
    can_withdraw = serializers.SerializerMethodField()
    can_correct = serializers.SerializerMethodField()
    current_version = KnowledgeVersionSerializer(read_only=True, allow_null=True)
    version_count = serializers.SerializerMethodField()

    class Meta:
        model = PreservedKnowledge
        fields = (
            'id',
            'status',
            'source_message_id',
            'source_message',
            'preserved_by_username',
            'preserved_at',
            'withdrawn_at',
            'withdrawn_by_username',
            'can_withdraw',
            'can_correct',
            'current_version',
            'version_count'
        )

    def get_source_message(self, obj):
        message = obj.source_message
        channel = message.chat_session.space_channel
        return {
            'content': message.message,
            'author': message.user.username,
            'created_at': message.create_date,
            'channel_id': str(channel.id),
            'channel_name': channel.name
        }

    def get_can_withdraw(self, obj):
        role = self.context.get('space_role')
        user = self.context['request'].user
        return role in MANAGER_ROLES or obj.preserved_by_id == user.pk

    def get_can_correct(self, obj):
        role = self.context.get('space_role')
        user = self.context['request'].user
        return (
            obj.status in (
                PreservedKnowledge.Status.ACTIVE,
                PreservedKnowledge.Status.NEEDS_REVIEW
            )
            and (
                role in MANAGER_ROLES
                or obj.preserved_by_id == user.pk
                or obj.source_message.user_id == user.pk
            )
        )

    def get_version_count(self, obj):
        return getattr(obj, 'version_count', obj.versions.count())


class ResourceLinkValidationMixin:
    url = serializers.URLField(
        source='external_url',
        max_length=2048,
        required=False
    )

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('A resource title is required.')
        return value

    def validate_description(self, value):
        return value.strip()

    def validate_url(self, value):
        parts = urlsplit(value)
        if (
            parts.scheme.lower() not in {'http', 'https'}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
        ):
            raise serializers.ValidationError(
                'Use an HTTP or HTTPS URL without embedded credentials.'
            )
        return value.strip()


class ResourceCreateSerializer(
    ResourceLinkValidationMixin,
    serializers.ModelSerializer
):
    title = serializers.CharField(max_length=160)
    url = serializers.URLField(
        source='external_url',
        max_length=2048
    )

    class Meta:
        model = Resource
        fields = ('title', 'description', 'url')

    def validate_url(self, value):
        if not value:
            raise serializers.ValidationError('A resource URL is required.')
        return super().validate_url(value)


class ResourceUpdateSerializer(
    ResourceLinkValidationMixin,
    serializers.ModelSerializer
):
    status = serializers.ChoiceField(
        choices=(
            (Resource.Status.ACTIVE, 'Active'),
            (Resource.Status.ARCHIVED, 'Archived')
        ),
        required=False
    )

    class Meta:
        model = Resource
        fields = ('title', 'description', 'url', 'status')


class ResourceSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    source_domain = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    creator_username = serializers.CharField(
        source='created_by.username',
        read_only=True,
        allow_null=True
    )
    can_edit = serializers.SerializerMethodField()
    can_archive = serializers.SerializerMethodField()
    can_restore = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = (
            'id',
            'type',
            'title',
            'description',
            'url',
            'source_domain',
            'creator_username',
            'status',
            'deleted_at',
            'create_date',
            'update_date',
            'can_edit',
            'can_archive',
            'can_restore',
            'can_delete'
        )

    def get_source_domain(self, obj):
        return urlsplit(obj.external_url).hostname if obj.external_url else None

    def get_url(self, obj):
        return obj.external_url or None

    def get_title(self, obj):
        return (
            'Resource removed'
            if obj.status == Resource.Status.DELETED
            else obj.title
        )

    def _role_and_request(self, obj):
        request = self.context['request']
        role = self.context.get('space_role')
        if role is None:
            role = get_space_role(obj.space, request.user)
        return role, request.user

    def get_can_edit(self, obj):
        role, user = self._role_and_request(obj)
        return (
            obj.status != Resource.Status.DELETED
            and (role in MANAGER_ROLES or obj.created_by_id == user.pk)
        )

    def get_can_archive(self, obj):
        role, user = self._role_and_request(obj)
        return (
            obj.status == Resource.Status.ACTIVE
            and (
                role in MANAGER_ROLES
                or role == MODERATOR
                or obj.created_by_id == user.pk
            )
        )

    def get_can_restore(self, obj):
        role, user = self._role_and_request(obj)
        return (
            obj.status == Resource.Status.ARCHIVED
            and (role in MANAGER_ROLES or obj.created_by_id == user.pk)
        )

    def get_can_delete(self, obj):
        role, _user = self._role_and_request(obj)
        return (
            obj.status != Resource.Status.DELETED
            and role in MANAGER_ROLES
        )


class ChannelMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    resource_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        max_length=20
    )

    def validate_message(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('A non-empty message is required.')
        return value

    def validate_resource_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError(
                'A resource may be referenced only once per message.'
            )
        return value


class ChannelMessageUpdateSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)

    def validate_message(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('A non-empty message is required.')
        return value


class MessageRevisionSerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(
        source='changed_by.username',
        read_only=True
    )

    class Meta:
        model = ChatSessionMessageRevision
        fields = (
            'id',
            'revision_number',
            'content',
            'changed_by_username',
            'create_date'
        )

_SEARCH_TERM_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


class SpaceSearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(max_length=200)
    content_type = serializers.ChoiceField(
        choices=(
            ('all', 'All'),
            ('discussions', 'Discussions'),
            ('knowledge', 'Preserved knowledge'),
            ('resources', 'Resources')
        ),
        default='all'
    )
    channel_id = serializers.UUIDField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(
        min_value=1,
        max_value=50,
        default=20
    )

    def validate_q(self, value):
        normalized = ' '.join(value.split())
        if not _SEARCH_TERM_PATTERN.search(normalized):
            raise serializers.ValidationError(
                'Enter at least one letter or number to search.'
            )
        return normalized

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if start_date is not None and end_date is not None and start_date > end_date:
            raise serializers.ValidationError({
                'end_date': 'End date must not be before the start date.'
            })
        return attrs
