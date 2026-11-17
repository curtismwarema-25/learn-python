"""Validated API contracts for the Community domain."""

from django.utils import timezone

from rest_framework import serializers

from .models import Channel, Space, SpaceJoinRequest, SpaceMembership
from .permissions import OWNER, get_space_role


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
