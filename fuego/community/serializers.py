"""Validated API contracts for the Community domain."""

from django.utils import timezone
from urllib.parse import urlsplit

from rest_framework import serializers

from .models import (
    Channel,
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
