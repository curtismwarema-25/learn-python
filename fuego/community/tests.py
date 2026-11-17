from datetime import timedelta
from unittest.mock import patch

from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from chat.models import ChatSession, ChatSessionMessage
from chat.websocket import _is_chat_member
from fuego.asgi import application

from .models import Channel, Space, SpaceJoinRequest, SpaceMembership
from .permissions import ADMINISTRATOR, MEMBER, MODERATOR, OWNER


User = get_user_model()


class SpaceAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='space_owner',
            email='space-owner@example.com',
            password='TestSpaceOwner123!'
        )
        self.admin = User.objects.create_user(
            username='space_admin',
            email='space-admin@example.com',
            password='TestSpaceAdmin123!'
        )
        self.moderator = User.objects.create_user(
            username='space_moderator',
            email='space-moderator@example.com',
            password='TestSpaceModerator123!'
        )
        self.member = User.objects.create_user(
            username='space_member',
            email='space-member@example.com',
            password='TestSpaceMember123!'
        )
        self.client = APIClient()
        self.space = self.create_space()

    def create_space(self, visibility=Space.Visibility.PRIVATE):
        return Space.objects.create(
            owner=self.owner,
            name='Python Learners',
            description='A place to learn by building.',
            purpose='Share practical Python learning.',
            visibility=visibility
        )

    def detail_url(self, space=None):
        space = space or self.space
        return '/api/spaces/%s/' % space.id

    def test_create_space_defaults_to_private_and_assigns_owner(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            '/api/spaces/',
            {
                'name': 'Data Practice',
                'purpose': 'Practice useful data skills.',
                'description': 'Small practical exercises.'
            },
            format='json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['visibility'], 'private')
        self.assertEqual(response.data['role'], OWNER)
        self.assertEqual(response.data['membership_status'], OWNER)
        created = Space.objects.get(id=response.data['id'])
        self.assertEqual(created.owner, self.owner)

    def test_space_creation_rejects_blank_required_text(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            '/api/spaces/',
            {'name': '  ', 'purpose': 'Useful practice'},
            format='json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.data)

    def test_public_directory_exposes_only_discoverable_metadata(self):
        discoverable = self.create_space(Space.Visibility.DISCOVERABLE)

        response = self.client.get('/api/spaces/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(discoverable.id))
        self.assertEqual(
            set(response.data[0]),
            {'id', 'name', 'description', 'purpose'}
        )

    def test_private_space_is_not_disclosed_to_nonmembers(self):
        self.client.force_authenticate(user=self.member)

        detail = self.client.get(self.detail_url())
        request = self.client.post(
            self.detail_url() + 'requests/',
            {},
            format='json'
        )

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(request.status_code, 404)

    def test_discoverable_space_metadata_is_public_but_roster_is_not(self):
        space = self.create_space(Space.Visibility.DISCOVERABLE)

        detail = self.client.get(self.detail_url(space))
        members = self.client.get(self.detail_url(space) + 'members/')

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['membership_status'], 'none')
        self.assertEqual(members.status_code, 401)

    def test_member_can_request_and_admin_can_approve(self):
        space = self.create_space(Space.Visibility.DISCOVERABLE)
        request_url = self.detail_url(space) + 'requests/'
        self.client.force_authenticate(user=self.member)

        submitted = self.client.post(request_url, {}, format='json')
        self.assertEqual(submitted.status_code, 201)
        self.assertEqual(submitted.data['status'], 'pending')
        self.assertEqual(
            self.client.get(self.detail_url(space) + 'members/').status_code,
            404
        )
        self.assertEqual(
            self.client.get(self.detail_url(space)).data['membership_status'],
            'pending'
        )

        admin_membership = SpaceMembership.objects.create(
            space=space,
            user=self.admin,
            role=ADMINISTRATOR
        )
        self.client.force_authenticate(user=self.admin)
        queue = self.client.get(request_url)
        approved = self.client.post(
            request_url + '%s/approve/' % submitted.data['id']
        )

        self.assertEqual(queue.status_code, 200)
        self.assertEqual(len(queue.data), 1)
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data['status'], 'approved')
        self.assertTrue(
            SpaceMembership.objects.filter(
                space=space,
                user=self.member,
                role=MEMBER
            ).exists()
        )
        self.assertTrue(
            SpaceMembership.objects.filter(pk=admin_membership.pk).exists()
        )

    def test_denied_request_can_be_cancelled_or_resubmitted(self):
        space = self.create_space(Space.Visibility.DISCOVERABLE)
        request_url = self.detail_url(space) + 'requests/'
        self.client.force_authenticate(user=self.member)
        submitted = self.client.post(request_url, {}, format='json')

        self.client.force_authenticate(user=self.owner)
        denied = self.client.post(
            request_url + '%s/deny/' % submitted.data['id']
        )
        self.assertEqual(denied.data['status'], 'denied')

        self.client.force_authenticate(user=self.member)
        resubmitted = self.client.post(request_url, {}, format='json')
        self.assertEqual(resubmitted.status_code, 201)
        self.assertEqual(resubmitted.data['status'], 'pending')

        cancelled = self.client.delete(request_url)
        self.assertEqual(cancelled.status_code, 204)
        self.assertEqual(
            SpaceJoinRequest.objects.get(pk=submitted.data['id']).status,
            SpaceJoinRequest.Status.CANCELLED
        )

    def test_only_owner_and_admin_can_manage_invites(self):
        self.space.rotate_invite()
        invite_url = self.detail_url() + 'invite/'
        SpaceMembership.objects.create(
            space=self.space,
            user=self.admin,
            role=ADMINISTRATOR
        )
        SpaceMembership.objects.create(
            space=self.space,
            user=self.member,
            role=MEMBER
        )

        self.client.force_authenticate(user=self.admin)
        rotated = self.client.post(invite_url)
        self.assertEqual(rotated.status_code, 200)
        self.assertTrue(rotated.data['can_manage'])
        self.assertIsNotNone(rotated.data['token'])

        self.client.force_authenticate(user=self.member)
        visible = self.client.get(invite_url)
        denied = self.client.post(invite_url)
        self.assertEqual(visible.status_code, 200)
        self.assertFalse(visible.data['can_manage'])
        self.assertIsNone(visible.data['token'])
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(user=self.moderator)
        self.assertEqual(self.client.post(invite_url).status_code, 404)

    def test_invite_rotation_and_revoke_prevent_future_joins(self):
        self.space.rotate_invite()
        old_token = self.space.invite_token
        self.client.force_authenticate(user=self.owner)
        invite_url = self.detail_url() + 'invite/'
        rotated = self.client.post(invite_url)
        new_token = rotated.data['token']

        self.client.force_authenticate(user=self.member)
        old_link = self.client.post(
            '/api/spaces/invites/join/',
            {'token': old_token},
            format='json'
        )
        joined = self.client.post(
            '/api/spaces/invites/join/',
            {'token': new_token},
            format='json'
        )
        self.assertEqual(old_link.status_code, 404)
        self.assertEqual(joined.status_code, 200)
        self.assertEqual(joined.data['role'], MEMBER)

        self.client.force_authenticate(user=self.owner)
        revoked = self.client.delete(invite_url)
        self.assertEqual(revoked.status_code, 200)
        self.assertIsNone(revoked.data['token'])

        self.client.force_authenticate(user=self.moderator)
        after_revoke = self.client.post(
            '/api/spaces/invites/join/',
            {'token': new_token},
            format='json'
        )
        self.assertEqual(after_revoke.status_code, 404)

    def test_expired_invite_cannot_be_used(self):
        self.space.rotate_invite()
        token = self.space.invite_token
        self.space.invite_expires_at = timezone.now() - timedelta(seconds=1)
        self.space.save(update_fields=('invite_expires_at',))
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            '/api/spaces/invites/join/',
            {'token': token},
            format='json'
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            SpaceMembership.objects.filter(
                space=self.space,
                user=self.member
            ).exists()
        )

    def test_owner_redeeming_own_invite_does_not_duplicate_membership(self):
        self.space.rotate_invite()
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            '/api/spaces/invites/join/',
            {'token': self.space.invite_token},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], OWNER)
        self.assertEqual(self.space.memberships.count(), 0)

    def test_admin_can_manage_roles_but_cannot_assign_admin(self):
        admin_membership = SpaceMembership.objects.create(
            space=self.space,
            user=self.admin,
            role=ADMINISTRATOR
        )
        member_membership = SpaceMembership.objects.create(
            space=self.space,
            user=self.member,
            role=MEMBER
        )
        self.client.force_authenticate(user=self.admin)
        member_url = self.detail_url() + 'members/%s/' % self.member.id

        changed = self.client.patch(
            member_url,
            {'role': MODERATOR},
            format='json'
        )
        promote_admin = self.client.patch(
            member_url,
            {'role': ADMINISTRATOR},
            format='json'
        )
        change_admin = self.client.patch(
            self.detail_url() + 'members/%s/' % self.admin.id,
            {'role': MEMBER},
            format='json'
        )

        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.data['role'], MODERATOR)
        self.assertEqual(promote_admin.status_code, 403)
        self.assertEqual(change_admin.status_code, 403)
        self.assertTrue(
            SpaceMembership.objects.filter(pk=admin_membership.pk).exists()
        )
        self.assertTrue(
            SpaceMembership.objects.filter(pk=member_membership.pk).exists()
        )

    def test_owner_can_transfer_ownership_and_cannot_leave_before_transfer(self):
        SpaceMembership.objects.create(
            space=self.space,
            user=self.member,
            role=MEMBER
        )
        channel = create_test_channel(self.space, self.owner)
        self.client.force_authenticate(user=self.owner)
        leave_url = self.detail_url() + 'leave/'
        blocked_leave = self.client.post(leave_url)
        transfer = self.client.post(
            self.detail_url() + 'transfer/',
            {'user_id': self.member.id},
            format='json'
        )

        self.assertEqual(blocked_leave.status_code, 403)
        self.assertEqual(transfer.status_code, 200)
        self.space.refresh_from_db()
        self.assertEqual(self.space.owner, self.member)
        self.assertEqual(
            get_space_membership_role(self.space, self.owner),
            ADMINISTRATOR
        )
        self.assertEqual(
            get_space_membership_role(self.space, self.member),
            OWNER
        )
        channel.conversation.refresh_from_db()
        self.assertEqual(channel.conversation.owner, self.member)

    def test_moderator_cannot_change_space_settings_or_membership(self):
        SpaceMembership.objects.create(
            space=self.space,
            user=self.moderator,
            role=MODERATOR
        )
        self.client.force_authenticate(user=self.moderator)

        update = self.client.patch(
            self.detail_url(),
            {'visibility': Space.Visibility.DISCOVERABLE},
            format='json'
        )
        remove_member = self.client.delete(
            self.detail_url() + 'members/%s/' % self.member.id
        )

        self.assertEqual(update.status_code, 403)
        self.assertEqual(remove_member.status_code, 403)

    def test_owner_can_delete_space_but_admin_cannot(self):
        SpaceMembership.objects.create(
            space=self.space,
            user=self.admin,
            role=ADMINISTRATOR
        )
        self.client.force_authenticate(user=self.admin)
        denied = self.client.delete(self.detail_url())
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(user=self.owner)
        deleted = self.client.delete(self.detail_url())
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Space.objects.filter(pk=self.space.pk).exists())

    def test_membership_and_join_request_have_database_uniqueness(self):
        SpaceMembership.objects.create(
            space=self.space,
            user=self.member,
            role=MEMBER
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SpaceMembership.objects.create(
                    space=self.space,
                    user=self.member,
                    role=MEMBER
                )

        SpaceJoinRequest.objects.create(
            space=self.space,
            user=self.member
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SpaceJoinRequest.objects.create(
                    space=self.space,
                    user=self.member
                )


def get_space_membership_role(space, user):
    if space.owner_id == user.id:
        return OWNER
    return space.memberships.get(user=user).role


def create_test_channel(space, created_by, name='general'):
    conversation = ChatSession.objects.create(owner=space.owner)
    return Channel.objects.create(
        space=space,
        conversation=conversation,
        name=name,
        created_by=created_by
    )


class ChannelAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='channel_owner',
            password='TestChannelOwner123!'
        )
        self.admin = User.objects.create_user(
            username='channel_admin',
            password='TestChannelAdmin123!'
        )
        self.moderator = User.objects.create_user(
            username='channel_moderator',
            password='TestChannelMod123!'
        )
        self.member = User.objects.create_user(
            username='channel_member',
            password='TestChannelMember123!'
        )
        self.outsider = User.objects.create_user(
            username='channel_outsider',
            password='TestChannelOutside123!'
        )
        self.space = Space.objects.create(
            owner=self.owner,
            name='Channel Testing',
            purpose='Test channel access.'
        )
        SpaceMembership.objects.create(
            space=self.space,
            user=self.admin,
            role=ADMINISTRATOR
        )
        SpaceMembership.objects.create(
            space=self.space,
            user=self.moderator,
            role=MODERATOR
        )
        SpaceMembership.objects.create(
            space=self.space,
            user=self.member,
            role=MEMBER
        )
        self.client = APIClient()
        self.channels_url = '/api/spaces/%s/channels/' % self.space.id
        self.channel = create_test_channel(self.space, self.owner)
        self.channel_url = self.channels_url + '%s/' % self.channel.id
        self.messages_url = self.channel_url + 'messages/'

    def test_new_space_creates_one_general_channel_without_a_chat_invite(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            '/api/spaces/',
            {'name': 'New Space', 'purpose': 'A new community.'},
            format='json'
        )

        self.assertEqual(response.status_code, 201)
        space = Space.objects.get(pk=response.data['id'])
        channel = space.channels.get()
        self.assertEqual(channel.name, 'general')
        self.assertEqual(channel.conversation.owner, self.owner)
        self.assertIsNone(channel.conversation.invite_token)
        self.assertEqual(space.channels.count(), 1)

    def test_members_can_list_and_read_channels_but_outsiders_cannot(self):
        for user in (self.owner, self.admin, self.moderator, self.member):
            self.client.force_authenticate(user=user)
            self.assertEqual(self.client.get(self.channels_url).status_code, 200)
            self.assertEqual(self.client.get(self.channel_url).status_code, 200)
            self.assertEqual(self.client.get(self.messages_url).status_code, 200)

        self.client.force_authenticate(user=self.outsider)
        self.assertEqual(self.client.get(self.channels_url).status_code, 404)
        self.assertEqual(self.client.get(self.channel_url).status_code, 404)
        self.assertEqual(self.client.get(self.messages_url).status_code, 404)

    def test_only_owner_and_admin_can_create_update_archive_or_delete_channels(self):
        self.client.force_authenticate(user=self.moderator)
        denied_create = self.client.post(
            self.channels_url,
            {'name': 'design'},
            format='json'
        )
        denied_update = self.client.patch(
            self.channel_url,
            {'name': 'lounge'},
            format='json'
        )
        self.assertEqual(denied_create.status_code, 403)
        self.assertEqual(denied_update.status_code, 403)

        self.client.force_authenticate(user=self.admin)
        created = self.client.post(
            self.channels_url,
            {'name': 'Design', 'description': 'Design discussion.'},
            format='json'
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['name'], 'design')
        renamed = self.client.patch(
            self.channels_url + '%s/' % created.data['id'],
            {'name': 'creative-work'},
            format='json'
        )
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.data['name'], 'creative-work')

        archived = self.client.patch(
            self.channel_url,
            {'archived': True},
            format='json'
        )
        self.assertEqual(archived.status_code, 200)
        self.assertTrue(archived.data['archived'])
        read_only = self.client.post(
            self.messages_url,
            {'message': 'This should not be sent.'},
            format='json'
        )
        self.assertEqual(read_only.status_code, 409)

        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.delete(self.channel_url).status_code, 204)

    def test_channel_names_are_unique_within_a_space(self):
        self.client.force_authenticate(user=self.admin)

        duplicate = self.client.post(
            self.channels_url,
            {'name': 'GENERAL'},
            format='json'
        )

        self.assertEqual(duplicate.status_code, 400)
        self.assertIn('name', duplicate.data)

    @patch('chat.services.notify')
    def test_message_author_is_taken_from_authentication_not_request_data(self, notify):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            self.messages_url,
            {
                'message': 'A channel message.',
                'user': {'username': self.owner.username}
            },
            format='json'
        )

        self.assertEqual(response.status_code, 201)
        saved = ChatSessionMessage.objects.get(pk=response.data['id'])
        self.assertEqual(saved.user, self.member)
        self.assertEqual(saved.message, 'A channel message.')
        self.assertEqual(response.data['user'], {'username': self.member.username})
        self.assertNotIn(
            self.channel.conversation.uri,
            response.data.values()
        )
        notify.assert_called_once()

    def test_channel_conversation_cannot_be_accessed_through_direct_chat_apis(self):
        self.client.force_authenticate(user=self.owner)

        history = self.client.get(
            '/api/chats/%s/messages/' % self.channel.conversation.uri
        )
        invite = self.client.get(
            '/api/chats/%s/invite/' % self.channel.conversation.uri
        )
        add_member = self.client.patch(
            '/api/chats/%s/' % self.channel.conversation.uri,
            {'username': self.outsider.username},
            format='json'
        )

        self.assertEqual(history.status_code, 404)
        self.assertEqual(invite.status_code, 404)
        self.assertEqual(add_member.status_code, 404)
        self.assertFalse(
            self.channel.conversation.members.filter(user=self.outsider).exists()
        )

    def test_optional_chat_bridge_does_not_authorize_channel_sessions(self):
        token = Token.objects.create(user=self.owner)

        self.assertFalse(
            _is_chat_member(self.channel.conversation.uri, token.key)
        )

    def test_channel_history_blocks_channel_and_space_deletion(self):
        self.client.force_authenticate(user=self.owner)
        self.client.post(
            self.messages_url,
            {'message': 'Keep this history.'},
            format='json'
        )

        delete_channel = self.client.delete(self.channel_url)
        delete_space = self.client.delete(
            '/api/spaces/%s/' % self.space.id
        )

        self.assertEqual(delete_channel.status_code, 409)
        self.assertEqual(delete_space.status_code, 409)
        self.assertTrue(Channel.objects.filter(pk=self.channel.pk).exists())
        self.assertTrue(
            ChatSessionMessage.objects.filter(
                chat_session=self.channel.conversation
            ).exists()
        )

    def test_empty_channel_can_be_deleted_without_leaving_a_conversation(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(self.channel_url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ChatSession.objects.filter(
            pk=self.channel.conversation_id
        ).exists())
        self.assertFalse(Channel.objects.filter(pk=self.channel.pk).exists())


class ChannelWebSocketTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='socket_channel_owner',
            password='TestSocketChannelOwner123!'
        )
        self.member = User.objects.create_user(
            username='socket_channel_member',
            password='TestSocketChannelMember123!'
        )
        self.outsider = User.objects.create_user(
            username='socket_channel_outsider',
            password='TestSocketChannelOutside123!'
        )
        self.space = Space.objects.create(
            owner=self.owner,
            name='Socket Space',
            purpose='Test channel sockets.'
        )
        SpaceMembership.objects.create(
            space=self.space,
            user=self.member,
            role=MEMBER
        )
        self.channel = create_test_channel(self.space, self.owner)
        self.member_token = Token.objects.create(user=self.member)
        self.outsider_token = Token.objects.create(user=self.outsider)

    def channel_path(self, space_id=None):
        return (
            '/ws/spaces/%s/channels/%s/'
            % (space_id or self.space.id, self.channel.id)
        )

    def test_space_member_connects_and_revoked_member_is_closed_before_delivery(self):
        async def exercise():
            communicator = WebsocketCommunicator(
                application,
                self.channel_path()
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to({
                'type': 'authenticate',
                'token': self.member_token.key
            })
            self.assertEqual(
                await communicator.receive_json_from(),
                {'type': 'authenticated'}
            )

            await sync_to_async(
                lambda: SpaceMembership.objects.filter(
                    space=self.space,
                    user=self.member
                ).delete(),
                thread_sensitive=True
            )()
            await get_channel_layer().group_send(
                'chat_%s' % self.channel.conversation.uri,
                {
                    'type': 'notifs.websocket_message',
                    'message': '{"id":1,"message":"must not be delivered"}'
                }
            )
            closed = await communicator.receive_output(timeout=1)
            self.assertEqual(closed['type'], 'websocket.close')
            self.assertEqual(closed['code'], 4403)
            await communicator.wait()

        async_to_sync(exercise)()

    def test_nonmember_and_wrong_space_route_cannot_subscribe(self):
        async def exercise():
            denied = WebsocketCommunicator(
                application,
                self.channel_path()
            )
            connected, _ = await denied.connect()
            self.assertTrue(connected)
            await denied.send_json_to({
                'type': 'authenticate',
                'token': self.outsider_token.key
            })
            closed = await denied.receive_output(timeout=1)
            self.assertEqual(closed['type'], 'websocket.close')
            self.assertEqual(closed['code'], 4403)

            wrong_space = WebsocketCommunicator(
                application,
                self.channel_path(space_id='00000000-0000-0000-0000-000000000001')
            )
            connected_wrong_space, close_code = await wrong_space.connect()
            self.assertFalse(connected_wrong_space)
            self.assertEqual(close_code, 4404)

        async_to_sync(exercise)()

    def test_channel_conversation_is_not_authorized_by_direct_chat_websocket(self):
        async def exercise():
            communicator = WebsocketCommunicator(
                application,
                '/ws/chats/%s/' % self.channel.conversation.uri
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to({
                'type': 'authenticate',
                'token': self.member_token.key
            })
            closed = await communicator.receive_output(timeout=1)
            self.assertEqual(closed['type'], 'websocket.close')
            self.assertEqual(closed['code'], 4403)
            await communicator.wait()

        async_to_sync(exercise)()
