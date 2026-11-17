"""API views for Fuego Spaces."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from chat.models import ChatSession, ChatSessionMessage

from rest_framework import permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Channel,
    Resource,
    ResourceReference,
    Space,
    SpaceJoinRequest,
    SpaceMembership
)
from .permissions import (
    ADMINISTRATOR,
    MANAGER_ROLES,
    MEMBER,
    MODERATOR,
    OWNER,
    get_space_role
)
from .serializers import (
    ChannelCreateSerializer,
    ChannelMessageCreateSerializer,
    ChannelSerializer,
    ChannelUpdateSerializer,
    ResourceCreateSerializer,
    ResourceSerializer,
    ResourceUpdateSerializer,
    SpaceCreateSerializer,
    SpaceDetailSerializer,
    SpaceJoinRequestSerializer,
    SpaceMembershipSerializer,
    SpaceMetadataSerializer,
    SpaceInviteJoinSerializer,
    SpaceOwnershipTransferSerializer,
    SpaceRoleUpdateSerializer,
    SpaceSummarySerializer,
    SpaceUpdateSerializer
)
from .services import (
    channel_message_to_json,
    create_channel,
    create_channel_message,
    ensure_default_channel,
    resource_reference_to_json
)


User = get_user_model()


def _space_or_404(space_id, for_update=False):
    spaces = Space.objects.select_related('owner')
    if for_update:
        spaces = spaces.select_for_update()
    return get_object_or_404(spaces, pk=space_id)


def _require_space_member(space, user):
    role = get_space_role(space, user)
    if role is None:
        raise NotFound('Space not found.')
    return role


def _require_space_manager(space, user):
    role = _require_space_member(space, user)
    if role not in MANAGER_ROLES:
        raise PermissionDenied('Only the Space owner or an administrator can do this.')
    return role


def _space_detail_response(space, request):
    role = get_space_role(space, request.user)
    pending_request = None
    if request.user.is_authenticated and role is None:
        pending_request = (
            SpaceJoinRequest.objects
            .filter(
                space=space,
                user=request.user,
                status=SpaceJoinRequest.Status.PENDING
            )
            .exists()
        )
    membership_status = (
        'owner' if role == OWNER
        else 'member' if role is not None
        else 'pending' if pending_request
        else 'none'
    )
    serializer = SpaceDetailSerializer(
        space,
        context={
            'request': request,
            'role': role,
            'membership_status': membership_status
        }
    )
    return Response(serializer.data)


class SpaceDirectoryView(APIView):
    """List discoverable Spaces publicly and create Spaces when signed in."""

    def get_permissions(self):
        permission = (
            permissions.AllowAny
            if self.request.method == 'GET'
            else permissions.IsAuthenticated
        )
        return [permission()]

    def get(self, _request, *args, **kwargs):
        spaces = Space.objects.filter(
            visibility=Space.Visibility.DISCOVERABLE
        ).order_by('name', 'id')
        return Response(SpaceMetadataSerializer(spaces, many=True).data)

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = SpaceCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            space = serializer.save(owner=request.user)
            ensure_default_channel(space)
        return Response(
            SpaceDetailSerializer(
                space,
                context={
                    'request': request,
                    'role': OWNER,
                    'membership_status': 'owner'
                }
            ).data,
            status=status.HTTP_201_CREATED
        )


class MySpacesView(APIView):
    """List Spaces owned by or joined by the authenticated user."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        memberships = SpaceMembership.objects.filter(user=request.user)
        spaces = (
            Space.objects
            .filter(Q(owner=request.user) | Q(memberships__user=request.user))
            .distinct()
            .prefetch_related(
                Prefetch(
                    'memberships',
                    queryset=memberships,
                    to_attr='_current_user_memberships'
                )
            )
            .order_by('name', 'id')
        )
        return Response(
            SpaceSummarySerializer(
                spaces,
                many=True,
                context={'request': request}
            ).data
        )


class SpaceDetailView(APIView):
    """Read public metadata or manage an accessible Space."""

    def get_permissions(self):
        permission = (
            permissions.AllowAny
            if self.request.method == 'GET'
            else permissions.IsAuthenticated
        )
        return [permission()]

    def get(self, request, *args, **kwargs):
        space = _space_or_404(kwargs['space_id'])
        role = get_space_role(space, request.user)
        if space.visibility == Space.Visibility.PRIVATE and role is None:
            raise NotFound('Space not found.')
        return _space_detail_response(space, request)

    def patch(self, request, *args, **kwargs):
        with transaction.atomic():
            space = _space_or_404(kwargs['space_id'], for_update=True)
            _require_space_manager(space, request.user)
            serializer = SpaceUpdateSerializer(
                space,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            space = serializer.save()
        return _space_detail_response(space, request)

    def delete(self, request, *args, **kwargs):
        with transaction.atomic():
            space = _space_or_404(kwargs['space_id'], for_update=True)
            if space.owner_id != request.user.id:
                raise PermissionDenied('Only the Space owner can delete it.')
            channel_sessions = ChatSession.objects.filter(
                space_channel__space=space
            )
            if ChatSessionMessage.objects.filter(
                chat_session__in=channel_sessions
            ).exists():
                return Response(
                    {
                        'detail': (
                            'A Space with channel message history cannot be '
                            'deleted. Archive channels to preserve their history.'
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )
            if Resource.objects.filter(
                space=space,
                status__in=(Resource.Status.ACTIVE, Resource.Status.ARCHIVED)
            ).exists():
                return Response(
                    {
                        'detail': (
                            'A Space with active or archived resources cannot '
                            'be deleted. Delete its resources first.'
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )
            channel_sessions.delete()
            space.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SpaceChannelsView(APIView):
    """List a member's Space channels or create one as a manager."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        space = _space_or_404(kwargs['space_id'])
        _require_space_member(space, request.user)
        channels = (
            Channel.objects
            .filter(space=space)
            .select_related('created_by')
            .order_by('name', 'id')
        )
        return Response(ChannelSerializer(channels, many=True).data)

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            space = _space_or_404(kwargs['space_id'], for_update=True)
            _require_space_manager(space, request.user)
            serializer = ChannelCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            if Channel.objects.filter(
                space=space,
                name=serializer.validated_data['name']
            ).exists():
                raise ValidationError({
                    'name': ['A channel with this name already exists.']
                })
            channel = create_channel(
                space=space,
                created_by=request.user,
                **serializer.validated_data
            )
        return Response(
            ChannelSerializer(channel).data,
            status=status.HTTP_201_CREATED
        )


class SpaceChannelDetailView(APIView):
    """Read or manage a channel within its parent Space."""

    permission_classes = (permissions.IsAuthenticated,)

    def get_channel(self, request, space_id, channel_id):
        channel = get_object_or_404(
            Channel.objects.select_related(
                'space',
                'conversation',
                'created_by'
            ),
            pk=channel_id,
            space_id=space_id
        )
        _require_space_member(channel.space, request.user)
        return channel

    def get(self, request, *args, **kwargs):
        channel = self.get_channel(
            request,
            kwargs['space_id'],
            kwargs['channel_id']
        )
        return Response(ChannelSerializer(channel).data)

    def patch(self, request, *args, **kwargs):
        with transaction.atomic():
            channel = get_object_or_404(
                Channel.objects.select_for_update().select_related('space'),
                pk=kwargs['channel_id'],
                space_id=kwargs['space_id']
            )
            _require_space_manager(channel.space, request.user)
            serializer = ChannelUpdateSerializer(
                channel,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            name = serializer.validated_data.get('name', channel.name)
            if Channel.objects.filter(
                space=channel.space,
                name=name
            ).exclude(pk=channel.pk).exists():
                raise ValidationError({
                    'name': ['A channel with this name already exists.']
                })
            channel = serializer.save()
        return Response(ChannelSerializer(channel).data)

    def delete(self, request, *args, **kwargs):
        with transaction.atomic():
            channel = get_object_or_404(
                Channel.objects.select_for_update().select_related('space'),
                pk=kwargs['channel_id'],
                space_id=kwargs['space_id']
            )
            _require_space_manager(channel.space, request.user)
            if channel.conversation.messages.exists():
                return Response(
                    {
                        'detail': (
                            'Channels with messages cannot be deleted. '
                            'Archive the channel to preserve its history.'
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )
            channel.conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SpaceChannelMessagesView(APIView):
    """Read or send messages through a channel's existing chat stream."""

    permission_classes = (permissions.IsAuthenticated,)

    def get_channel(self, request, space_id, channel_id):
        channel = get_object_or_404(
            Channel.objects.select_related('space', 'conversation'),
            pk=channel_id,
            space_id=space_id
        )
        _require_space_member(channel.space, request.user)
        return channel

    def get(self, request, *args, **kwargs):
        channel = self.get_channel(
            request,
            kwargs['space_id'],
            kwargs['channel_id']
        )
        messages = [
            channel_message_to_json(message)
            for message in channel.conversation.messages
            .select_related('user')
            .prefetch_related(
                Prefetch(
                    'resource_references',
                    queryset=ResourceReference.objects
                    .select_related('resource')
                    .order_by('create_date', 'id')
                )
            )
            .order_by('create_date', 'id')
        ]
        return Response({
            'id': str(channel.id),
            'name': channel.name,
            'messages': messages
        })

    def post(self, request, *args, **kwargs):
        channel = self.get_channel(
            request,
            kwargs['space_id'],
            kwargs['channel_id']
        )
        if channel.archived_at is not None:
            return Response(
                {'detail': 'This channel is archived and read-only.'},
                status=status.HTTP_409_CONFLICT
            )

        serializer = ChannelMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data['message']
        resource_ids = serializer.validated_data.get('resource_ids', [])
        resources_by_id = {
            resource.pk: resource
            for resource in Resource.objects.filter(
                space=channel.space,
                status=Resource.Status.ACTIVE,
                pk__in=resource_ids
            )
        }
        if len(resources_by_id) != len(resource_ids):
            raise ValidationError({
                'resource_ids': [
                    'Choose active resources from this Space.'
                ]
            })
        resources = [resources_by_id[resource_id] for resource_id in resource_ids]

        chat_message = create_channel_message(
            channel,
            request.user,
            message,
            resources
        )
        message_data = chat_message.to_json()
        message_data['resources'] = [
            resource_reference_to_json(resource)
            for resource in resources
        ]
        return Response(message_data, status=status.HTTP_201_CREATED)


class SpaceResourcesView(APIView):
    """List or create Space-scoped link resources."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        space = _space_or_404(kwargs['space_id'])
        role = _require_space_member(space, request.user)
        resources = Resource.objects.filter(space=space)
        requested_status = request.query_params.get('status', 'active')
        if requested_status == Resource.Status.ACTIVE:
            resources = resources.filter(status=Resource.Status.ACTIVE)
        elif requested_status == Resource.Status.ARCHIVED:
            resources = resources.filter(status=Resource.Status.ARCHIVED)
            if role not in {*MANAGER_ROLES, MODERATOR}:
                resources = resources.filter(created_by=request.user)
        else:
            raise ValidationError({
                'status': ['Choose either "active" or "archived".']
            })

        query = request.query_params.get('q', '').strip()
        if query:
            resources = resources.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(external_url__icontains=query)
            )
        resources = resources.select_related('space', 'created_by').order_by(
            '-create_date',
            'id'
        )
        return Response(
            ResourceSerializer(
                resources,
                many=True,
                context={'request': request, 'space_role': role}
            ).data
        )

    def post(self, request, *args, **kwargs):
        space = _space_or_404(kwargs['space_id'])
        role = _require_space_member(space, request.user)
        serializer = ResourceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resource = serializer.save(space=space, created_by=request.user)
        return Response(
            ResourceSerializer(
                resource,
                context={'request': request, 'space_role': role}
            ).data,
            status=status.HTTP_201_CREATED
        )


class SpaceResourceDetailView(APIView):
    """Read or manage one Resource within its owning Space."""

    permission_classes = (permissions.IsAuthenticated,)

    def get_resource(self, request, space_id, resource_id):
        space = _space_or_404(space_id)
        _require_space_member(space, request.user)
        return get_object_or_404(
            Resource.objects.select_related('space', 'created_by'),
            pk=resource_id,
            space=space
        )

    def get(self, request, *args, **kwargs):
        resource = self.get_resource(
            request,
            kwargs['space_id'],
            kwargs['resource_id']
        )
        role = get_space_role(resource.space, request.user)
        return Response(
            ResourceSerializer(
                resource,
                context={'request': request, 'space_role': role}
            ).data
        )

    def patch(self, request, *args, **kwargs):
        resource = self.get_resource(
            request,
            kwargs['space_id'],
            kwargs['resource_id']
        )
        if resource.status == Resource.Status.DELETED:
            raise NotFound('Resource has been deleted.')

        serializer = ResourceUpdateSerializer(
            resource,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        role = get_space_role(resource.space, request.user)
        is_manager = role in MANAGER_ROLES
        is_creator = resource.created_by_id == request.user.pk

        if any(key in values for key in ('title', 'description', 'external_url')):
            if not (is_manager or is_creator):
                raise PermissionDenied(
                    'Only the resource creator or a Space manager can edit it.'
                )
        next_status = values.get('status')
        if next_status == Resource.Status.ARCHIVED and not (
            is_manager or is_creator or role == MODERATOR
        ):
            raise PermissionDenied(
                'Only the creator, a moderator, or a Space manager can archive it.'
            )
        if next_status == Resource.Status.ACTIVE and not (
            is_manager or is_creator
        ):
            raise PermissionDenied(
                'Only the creator or a Space manager can restore it.'
            )

        resource = serializer.save()
        return Response(
            ResourceSerializer(
                resource,
                context={'request': request, 'space_role': role}
            ).data
        )

    def delete(self, request, *args, **kwargs):
        resource = self.get_resource(
            request,
            kwargs['space_id'],
            kwargs['resource_id']
        )
        if get_space_role(resource.space, request.user) not in MANAGER_ROLES:
            raise PermissionDenied(
                'Only the Space owner or an administrator can delete a resource.'
            )
        if resource.status != Resource.Status.DELETED:
            resource.status = Resource.Status.DELETED
            resource.deleted_at = timezone.now()
            resource.title = ''
            resource.description = ''
            resource.external_url = ''
            resource.created_by = None
            resource.save(update_fields=(
                'status',
                'deleted_at',
                'title',
                'description',
                'external_url',
                'created_by',
                'update_date'
            ))
        return Response(status=status.HTTP_204_NO_CONTENT)


class SpaceMembersView(APIView):
    """List members of a Space to its active members."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        space = _space_or_404(kwargs['space_id'])
        _require_space_member(space, request.user)
        members = [
            {
                'user_id': space.owner_id,
                'username': space.owner.username,
                'role': OWNER,
                'create_date': space.create_date
            }
        ]
        memberships = (
            space.memberships
            .select_related('user')
            .order_by('user__username', 'user_id')
        )
        members.extend(
            SpaceMembershipSerializer(membership).data
            for membership in memberships
        )
        return Response(members)


class SpaceMemberDetailView(APIView):
    """Change a member's role or remove them from a Space."""

    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request, *args, **kwargs):
        serializer = SpaceRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data['role']
        with transaction.atomic():
            space = _space_or_404(kwargs['space_id'], for_update=True)
            actor_role = _require_space_manager(space, request.user)
            if kwargs['user_id'] == space.owner_id:
                raise PermissionDenied(
                    'The owner role cannot be changed here.'
                )

            membership = get_object_or_404(
                SpaceMembership.objects.select_related('user').select_for_update(),
                space=space,
                user_id=kwargs['user_id']
            )
            if actor_role == ADMINISTRATOR and (
                membership.role == ADMINISTRATOR
                or new_role == ADMINISTRATOR
            ):
                raise PermissionDenied(
                    'Administrators cannot manage another administrator role.'
                )
            membership.role = new_role
            membership.save(update_fields=('role',))
        return Response(SpaceMembershipSerializer(membership).data)

    def delete(self, request, *args, **kwargs):
        with transaction.atomic():
            space = _space_or_404(kwargs['space_id'], for_update=True)
            actor_role = _require_space_manager(space, request.user)
            user_id = kwargs['user_id']
            if user_id == space.owner_id:
                raise PermissionDenied('The owner cannot be removed.')
            if user_id == request.user.id:
                raise PermissionDenied(
                    'Use the leave endpoint to leave this Space.'
                )

            membership = get_object_or_404(
                SpaceMembership.objects.select_related('user').select_for_update(),
                space=space,
                user_id=user_id
            )
            if actor_role == ADMINISTRATOR and membership.role == ADMINISTRATOR:
                raise PermissionDenied(
                    'Administrators cannot remove another administrator.'
                )
            membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeaveSpaceView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            space = _space_or_404(kwargs['space_id'], for_update=True)
            if space.owner_id == request.user.id:
                raise PermissionDenied(
                    'Transfer ownership before leaving this Space.'
                )
            membership = get_object_or_404(
                SpaceMembership.objects.select_for_update(),
                space=space,
                user=request.user
            )
            membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SpaceJoinRequestsView(APIView):
    """Submit/cancel a request or let managers review the request queue."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        space = _space_or_404(kwargs['space_id'])
        _require_space_manager(space, request.user)
        requests = (
            space.join_requests
            .filter(status=SpaceJoinRequest.Status.PENDING)
            .select_related('user')
            .order_by('requested_at', 'id')
        )
        return Response(
            SpaceJoinRequestSerializer(requests, many=True).data
        )

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            space = _space_or_404(kwargs['space_id'], for_update=True)
            if space.visibility != Space.Visibility.DISCOVERABLE:
                raise NotFound('Space not found.')
            if get_space_role(space, request.user) is not None:
                return Response(
                    {'detail': ['You are already a member of this Space.']},
                    status=status.HTTP_409_CONFLICT
                )

            join_request, _ = SpaceJoinRequest.objects.get_or_create(
                space=space,
                user=request.user,
                defaults={'status': SpaceJoinRequest.Status.PENDING}
            )
            if join_request.status != SpaceJoinRequest.Status.PENDING:
                join_request.status = SpaceJoinRequest.Status.PENDING
                join_request.requested_at = timezone.now()
                join_request.reviewed_at = None
                join_request.reviewed_by = None
                join_request.save(update_fields=(
                    'status',
                    'requested_at',
                    'reviewed_at',
                    'reviewed_by'
                ))
        return Response(
            SpaceJoinRequestSerializer(join_request).data,
            status=status.HTTP_201_CREATED
        )

    def delete(self, request, *args, **kwargs):
        with transaction.atomic():
            space = _space_or_404(kwargs['space_id'], for_update=True)
            join_request = get_object_or_404(
                SpaceJoinRequest.objects.select_for_update(),
                space=space,
                user=request.user,
                status=SpaceJoinRequest.Status.PENDING
            )
            join_request.status = SpaceJoinRequest.Status.CANCELLED
            join_request.save(update_fields=('status',))
        return Response(status=status.HTTP_204_NO_CONTENT)


class SpaceJoinDecisionView(APIView):
    """Approve or deny a pending Space request."""

    permission_classes = (permissions.IsAuthenticated,)
    decision = None

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            space = _space_or_404(kwargs['space_id'], for_update=True)
            _require_space_manager(space, request.user)
            join_request = get_object_or_404(
                SpaceJoinRequest.objects.select_for_update(),
                pk=kwargs['request_id'],
                space=space,
                status=SpaceJoinRequest.Status.PENDING
            )
            if self.decision == 'approve':
                SpaceMembership.objects.get_or_create(
                    space=space,
                    user=join_request.user,
                    defaults={'role': MEMBER}
                )
                join_request.status = SpaceJoinRequest.Status.APPROVED
            else:
                join_request.status = SpaceJoinRequest.Status.DENIED
            join_request.reviewed_at = timezone.now()
            join_request.reviewed_by = request.user
            join_request.save(update_fields=(
                'status',
                'reviewed_at',
                'reviewed_by'
            ))
        return Response(SpaceJoinRequestSerializer(join_request).data)


class SpaceInviteView(APIView):
    """Read, rotate, or revoke a Space's single active invite link."""

    permission_classes = (permissions.IsAuthenticated,)

    def _response(self, space, can_manage):
        active = (
            can_manage
            and space.invite_token
            and space.invite_expires_at
            and space.invite_expires_at > timezone.now()
        )
        return {
            'can_manage': can_manage,
            'token': space.invite_token if active else None,
            'expires_at': (
                space.invite_expires_at if can_manage else None
            )
        }

    def get(self, request, *args, **kwargs):
        space = _space_or_404(kwargs['space_id'])
        role = _require_space_member(space, request.user)
        return Response(self._response(space, role in MANAGER_ROLES))

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            space = _space_or_404(kwargs['space_id'], for_update=True)
            _require_space_manager(space, request.user)
            space.rotate_invite()
        return Response(self._response(space, True))

    def delete(self, request, *args, **kwargs):
        with transaction.atomic():
            space = _space_or_404(kwargs['space_id'], for_update=True)
            _require_space_manager(space, request.user)
            space.revoke_invite()
        return Response(self._response(space, True))


class SpaceInviteJoinView(APIView):
    """Join a Space using an active invite token in the request body."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = SpaceInviteJoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        with transaction.atomic():
            space = get_object_or_404(
                Space.objects.select_for_update(),
                invite_token=token
            )
            if (
                space.invite_expires_at is None
                or space.invite_expires_at <= timezone.now()
            ):
                raise NotFound('Invite link is invalid or expired.')

            if space.owner_id == request.user.id:
                return Response({
                    'space_id': str(space.id),
                    'role': OWNER
                })

            membership, created = SpaceMembership.objects.get_or_create(
                space=space,
                user=request.user,
                defaults={'role': MEMBER}
            )
            if created:
                SpaceJoinRequest.objects.filter(
                    space=space,
                    user=request.user,
                    status=SpaceJoinRequest.Status.PENDING
                ).update(
                    status=SpaceJoinRequest.Status.CANCELLED,
                    reviewed_at=timezone.now()
                )
        return Response({
            'space_id': str(space.id),
            'role': membership.role
        })


class TransferSpaceOwnershipView(APIView):
    """Transfer ownership to an active member."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = SpaceOwnershipTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        with transaction.atomic():
            space = _space_or_404(kwargs['space_id'], for_update=True)
            if space.owner_id != request.user.id:
                raise PermissionDenied(
                    'Only the Space owner can transfer ownership.'
                )
            new_owner_membership = get_object_or_404(
                SpaceMembership.objects.select_related('user').select_for_update(),
                space=space,
                user_id=user_id
            )
            SpaceMembership.objects.update_or_create(
                space=space,
                user=request.user,
                defaults={'role': ADMINISTRATOR}
            )
            new_owner = new_owner_membership.user
            new_owner_membership.delete()
            space.owner = new_owner
            space.save(update_fields=('owner', 'update_date'))
            ChatSession.objects.filter(
                space_channel__space=space
            ).update(owner=new_owner)
        return Response({
            'space_id': str(space.id),
            'owner_id': space.owner_id,
            'owner_username': space.owner.username
        })
