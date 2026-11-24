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

from .models import (
    Channel,
    KnowledgeIndexChunk,
    KnowledgeChunkEmbedding,
    KnowledgeIndexingJob,
    KnowledgeVersion,
    MessageReport,
    PreservedKnowledge,
    Resource,
    ResourceReference,
    Space,
    SpaceJoinRequest,
    SpaceMembership
)
from .permissions import ADMINISTRATOR, MEMBER, MODERATOR, OWNER
from .indexing import chunk_content, index_knowledge
from .embedding_pipeline import embed_indexing_job
from .embeddings import EmbeddingProviderError, FakeEmbeddingProvider
from .vector_store import get_vector_store
from .tasks import embed_indexing_job_task
from .services import ensure_default_channel


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


class ResourceAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='resource_owner',
            password='TestResourceOwner123!'
        )
        self.admin = User.objects.create_user(
            username='resource_admin',
            password='TestResourceAdmin123!'
        )
        self.moderator = User.objects.create_user(
            username='resource_moderator',
            password='TestResourceModerator123!'
        )
        self.member = User.objects.create_user(
            username='resource_member',
            password='TestResourceMember123!'
        )
        self.other_member = User.objects.create_user(
            username='resource_other',
            password='TestResourceOther123!'
        )
        self.outsider = User.objects.create_user(
            username='resource_outsider',
            password='TestResourceOutside123!'
        )
        self.space = Space.objects.create(
            owner=self.owner,
            name='Resource Testing',
            purpose='Test shared Space resources.'
        )
        for user, role in (
            (self.admin, ADMINISTRATOR),
            (self.moderator, MODERATOR),
            (self.member, MEMBER),
            (self.other_member, MEMBER)
        ):
            SpaceMembership.objects.create(
                space=self.space,
                user=user,
                role=role
            )
        self.client = APIClient()
        self.resources_url = '/api/spaces/%s/resources/' % self.space.id
        self.channel = create_test_channel(self.space, self.owner)
        self.messages_url = (
            '/api/spaces/%s/channels/%s/messages/'
            % (self.space.id, self.channel.id)
        )

    def create_resource(self, created_by=None, **values):
        return Resource.objects.create(
            space=self.space,
            created_by=created_by or self.owner,
            title=values.get('title', 'Django documentation'),
            description=values.get('description', 'A useful reference.'),
            external_url=values.get(
                'external_url',
                'https://docs.djangoproject.com/'
            )
        )

    def test_member_can_add_search_and_read_links_but_other_spaces_are_hidden(self):
        self.client.force_authenticate(user=self.member)
        created = self.client.post(
            self.resources_url,
            {
                'title': 'Django docs',
                'description': 'Official framework reference.',
                'url': 'https://docs.djangoproject.com/en/6.1/'
            },
            format='json'
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['source_domain'], 'docs.djangoproject.com')
        self.assertEqual(created.data['creator_username'], self.member.username)
        self.assertEqual(
            self.client.get(self.resources_url + '?q=framework').data[0]['id'],
            created.data['id']
        )
        self.assertEqual(
            self.client.get(
                self.resources_url + '?q=not-found'
            ).data,
            []
        )

        other_space = Space.objects.create(
            owner=self.outsider,
            name='Other Space',
            purpose='A separate community.'
        )
        other_resource = Resource.objects.create(
            space=other_space,
            created_by=self.outsider,
            title='Private link',
            external_url='https://example.com/'
        )
        self.client.force_authenticate(user=self.outsider)
        self.assertEqual(
            self.client.get(self.resources_url).status_code,
            404
        )
        self.assertEqual(
            self.client.get(
                self.resources_url + '%s/' % other_resource.id
            ).status_code,
            404
        )

    def test_links_reject_unsafe_schemes_and_embedded_credentials(self):
        self.client.force_authenticate(user=self.member)
        for url in (
            'javascript:alert(1)',
            'https://user:password@example.com/private'
        ):
            with self.subTest(url=url):
                response = self.client.post(
                    self.resources_url,
                    {'title': 'Unsafe link', 'url': url},
                    format='json'
                )
                self.assertEqual(response.status_code, 400)
        self.assertEqual(Resource.objects.count(), 0)

    def test_creator_and_moderator_archive_but_only_managers_delete(self):
        resource = self.create_resource(created_by=self.member)
        detail_url = self.resources_url + '%s/' % resource.id

        self.client.force_authenticate(user=self.member)
        edited = self.client.patch(
            detail_url,
            {'title': 'Updated by creator'},
            format='json'
        )
        self.assertEqual(edited.status_code, 200)

        self.client.force_authenticate(user=self.moderator)
        archived = self.client.patch(
            detail_url,
            {'status': Resource.Status.ARCHIVED},
            format='json'
        )
        self.assertEqual(archived.status_code, 200)
        denied_edit = self.client.patch(
            detail_url,
            {'title': 'Moderator cannot edit'},
            format='json'
        )
        denied_delete = self.client.delete(detail_url)
        self.assertEqual(denied_edit.status_code, 403)
        self.assertEqual(denied_delete.status_code, 403)

        self.client.force_authenticate(user=self.other_member)
        self.assertEqual(
            self.client.get(self.resources_url + '?status=archived').data,
            []
        )

        self.client.force_authenticate(user=self.admin)
        restored = self.client.patch(
            detail_url,
            {'status': Resource.Status.ACTIVE},
            format='json'
        )
        self.assertEqual(restored.status_code, 200)
        removed = self.client.delete(detail_url)
        self.assertEqual(removed.status_code, 204)
        resource.refresh_from_db()
        self.assertEqual(resource.status, Resource.Status.DELETED)
        self.assertEqual(resource.external_url, '')
        self.assertEqual(resource.title, '')

    def test_removed_member_loses_resource_access(self):
        resource = self.create_resource(created_by=self.member)
        self.space.memberships.filter(user=self.member).delete()
        self.client.force_authenticate(user=self.member)

        self.assertEqual(self.client.get(self.resources_url).status_code, 404)
        self.assertEqual(
            self.client.get(
                self.resources_url + '%s/' % resource.id
            ).status_code,
            404
        )

    def test_channel_reference_is_space_scoped_and_survives_resource_deletion(self):
        resource = self.create_resource()
        self.client.force_authenticate(user=self.member)

        with patch('chat.services.notify') as notify:
            with self.captureOnCommitCallbacks(execute=True):
                posted = self.client.post(
                    self.messages_url,
                    {
                        'message': 'Keep this reference.',
                        'resource_ids': [str(resource.id)]
                    },
                    format='json'
                )

        self.assertEqual(posted.status_code, 201)
        self.assertEqual(
            posted.data['resources'],
            [{
                'id': str(resource.id),
                'title': resource.title,
                'status': Resource.Status.ACTIVE
            }]
        )
        event_message = (
            notify.call_args.kwargs['extra_data']['context']['message']
        )
        self.assertEqual(event_message['resources'], posted.data['resources'])
        self.assertTrue(
            ResourceReference.objects.filter(
                message_id=posted.data['id'],
                resource=resource
            ).exists()
        )

        other_space = Space.objects.create(
            owner=self.outsider,
            name='Elsewhere',
            purpose='Not this Space.'
        )
        other_resource = Resource.objects.create(
            space=other_space,
            created_by=self.outsider,
            title='Other Space resource',
            external_url='https://example.org/'
        )
        wrong_space_reference = self.client.post(
            self.messages_url,
            {
                'message': 'This must not be accepted.',
                'resource_ids': [str(other_resource.id)]
            },
            format='json'
        )
        self.assertEqual(wrong_space_reference.status_code, 400)

        self.client.force_authenticate(user=self.owner)
        self.assertEqual(
            self.client.delete(self.resources_url + '%s/' % resource.id).status_code,
            204
        )
        self.client.force_authenticate(user=self.member)
        history = self.client.get(self.messages_url)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(
            history.data['messages'][0]['resources'],
            [{
                'id': str(resource.id),
                'title': 'Resource removed',
                'status': Resource.Status.DELETED
            }]
        )

    def test_space_deletion_requires_resources_to_be_removed_first(self):
        resource = self.create_resource()
        self.client.force_authenticate(user=self.owner)

        blocked = self.client.delete('/api/spaces/%s/' % self.space.id)
        self.assertEqual(blocked.status_code, 409)

        self.client.delete(self.resources_url + '%s/' % resource.id)
        deleted = self.client.delete('/api/spaces/%s/' % self.space.id)
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Space.objects.filter(pk=self.space.pk).exists())


class KnowledgePreservationAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='knowledge_owner',
            password='TestKnowledgeOwner123!'
        )
        self.member = User.objects.create_user(
            username='knowledge_member',
            password='TestKnowledgeMember123!'
        )
        self.other_member = User.objects.create_user(
            username='knowledge_other',
            password='TestKnowledgeOther123!'
        )
        self.outsider = User.objects.create_user(
            username='knowledge_outsider',
            password='TestKnowledgeOutside123!'
        )
        self.space = Space.objects.create(
            owner=self.owner,
            name='Knowledge Space',
            purpose='Preserve useful answers.'
        )
        for user in (self.member, self.other_member):
            SpaceMembership.objects.create(
                space=self.space,
                user=user,
                role=MEMBER
            )
        self.channel = create_test_channel(self.space, self.owner)
        self.message = ChatSessionMessage.objects.create(
            chat_session=self.channel.conversation,
            user=self.member,
            message='A reusable answer.'
        )
        self.knowledge_url = '/api/spaces/%s/knowledge/' % self.space.id
        self.client = APIClient()

    def test_member_can_preserve_and_retrieve_traceable_message(self):
        self.client.force_authenticate(user=self.member)

        preserved = self.client.post(
            self.knowledge_url,
            {'message_id': self.message.id},
            format='json'
        )

        self.assertEqual(preserved.status_code, 201)
        self.assertEqual(preserved.data['source_message_id'], self.message.id)
        self.assertEqual(preserved.data['source_message']['content'], 'A reusable answer.')
        self.assertEqual(preserved.data['source_message']['author'], self.member.username)
        self.assertEqual(preserved.data['source_message']['channel_id'], str(self.channel.id))
        self.assertTrue(preserved.data['can_withdraw'])
        self.assertEqual(preserved.data['current_version']['version_number'], 1)
        self.assertEqual(preserved.data['current_version']['content'], 'A reusable answer.')
        self.assertEqual(preserved.data['version_count'], 1)

        self.message.message = 'The corrected reusable answer.'
        self.message.save(update_fields=('message', 'update_date'))
        listed = self.client.get(self.knowledge_url)

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(
            listed.data[0]['source_message']['content'],
            'The corrected reusable answer.'
        )
        self.assertEqual(
            PreservedKnowledge.objects.get(source_message=self.message).status,
            PreservedKnowledge.Status.ACTIVE
        )

    def test_preservation_creates_idempotent_index_and_member_scoped_chunks(self):
        self.client.force_authenticate(user=self.member)
        preserved = self.client.post(
            self.knowledge_url,
            {'message_id': self.message.id},
            format='json'
        )
        knowledge_id = preserved.data['id']
        job = KnowledgeIndexingJob.objects.get(knowledge_id=knowledge_id)
        self.assertEqual(job.status, KnowledgeIndexingJob.Status.INDEXED)
        self.assertEqual(job.attempt_count, 1)
        self.assertEqual(job.chunks.count(), 1)
        chunk = job.chunks.get()
        self.assertEqual(chunk.version_id, preserved.data['current_version']['id'])
        self.assertEqual(chunk.source_message_id, self.message.id)
        self.assertEqual(chunk.source_author, self.member.username)
        self.assertEqual(chunk.source_channel_id, self.channel.id)

        index_knowledge(knowledge_id)
        job.refresh_from_db()
        self.assertEqual(job.attempt_count, 1)
        self.assertEqual(job.chunks.count(), 1)

        chunks = self.client.get(
            self.knowledge_url + '%s/chunks/' % knowledge_id
        )
        self.assertEqual(chunks.status_code, 200)
        self.assertEqual(len(chunks.data['chunks']), 1)
        self.assertEqual(chunks.data['chunks'][0]['knowledge_id'], knowledge_id)

        self.space.memberships.filter(user=self.member).delete()
        self.assertEqual(
            self.client.get(self.knowledge_url + '%s/chunks/' % knowledge_id).status_code,
            404
        )

    def test_preservation_generates_deterministic_embedding_and_vector_candidates(self):
        self.client.force_authenticate(user=self.member)
        preserved = self.client.post(
            self.knowledge_url,
            {'message_id': self.message.id},
            format='json'
        )
        job = KnowledgeIndexingJob.objects.get(knowledge_id=preserved.data['id'])
        task_result = embed_indexing_job_task.delay(job.pk)
        self.assertEqual(task_result.get()['status'], KnowledgeIndexingJob.EmbeddingStatus.COMPLETE)
        job.refresh_from_db()
        self.assertEqual(
            job.embedding_status,
            KnowledgeIndexingJob.EmbeddingStatus.COMPLETE,
            job.embedding_error
        )
        embedding = KnowledgeChunkEmbedding.objects.get(chunk__job=job)
        self.assertEqual(embedding.status, KnowledgeChunkEmbedding.Status.READY)
        self.assertEqual(embedding.provider, 'fake')
        self.assertEqual(embedding.model, 'fuego-fake-v1')
        self.assertEqual(embedding.dimensions, 32)

        provider = FakeEmbeddingProvider()
        candidates = get_vector_store().search(
            self.space,
            provider.embed(self.message.message),
            provider,
            provider.model
        )
        self.assertEqual(candidates[0].chunk_id, embedding.chunk_id)
        self.assertAlmostEqual(candidates[0].similarity, 1.0)

    def test_provider_failure_is_recorded_and_recovery_is_idempotent(self):
        self.client.force_authenticate(user=self.member)
        preserved = self.client.post(
            self.knowledge_url,
            {'message_id': self.message.id},
            format='json'
        )
        job = KnowledgeIndexingJob.objects.get(knowledge_id=preserved.data['id'])
        embed_indexing_job(job.pk)
        job.refresh_from_db()
        job.embedding_status = KnowledgeIndexingJob.EmbeddingStatus.PENDING
        job.save(update_fields=('embedding_status', 'update_date'))
        provider = FakeEmbeddingProvider()
        with patch('community.embedding_pipeline.get_embedding_provider', return_value=provider):
            with patch.object(
                provider,
                'embed_batch',
                side_effect=EmbeddingProviderError('provider unavailable')
            ):
                with self.assertRaises(EmbeddingProviderError):
                    embed_indexing_job(job.pk)
        job.refresh_from_db()
        self.assertEqual(
            job.embedding_status,
            KnowledgeIndexingJob.EmbeddingStatus.FAILED
        )
        self.assertIn('provider unavailable', job.embedding_error)
        recovered = embed_indexing_job(job.pk)
        self.assertEqual(
            recovered.embedding_status,
            KnowledgeIndexingJob.EmbeddingStatus.COMPLETE
        )
        self.assertEqual(
            KnowledgeChunkEmbedding.objects.filter(chunk__job=job).count(),
            1
        )

    def test_model_change_obsoletes_old_embedding_without_changing_knowledge(self):
        self.client.force_authenticate(user=self.member)
        preserved = self.client.post(
            self.knowledge_url,
            {'message_id': self.message.id},
            format='json'
        )
        job = KnowledgeIndexingJob.objects.get(knowledge_id=preserved.data['id'])
        embed_indexing_job(job.pk)
        with patch('community.embedding_pipeline.get_embedding_provider') as get_provider:
            provider = FakeEmbeddingProvider(model='fuego-fake-v2')
            get_provider.return_value = provider
            embed_indexing_job(job.pk)
        self.assertEqual(
            KnowledgeChunkEmbedding.objects.filter(
                chunk__job=job,
                model='fuego-fake-v1',
                status=KnowledgeChunkEmbedding.Status.OBSOLETE
            ).count(),
            1
        )
        self.assertTrue(
            KnowledgeChunkEmbedding.objects.filter(
                chunk__job=job,
                model='fuego-fake-v2',
                status=KnowledgeChunkEmbedding.Status.READY
            ).exists()
        )
        self.assertEqual(
            KnowledgeVersion.objects.get(pk=preserved.data['current_version']['id']).content,
            self.message.message
        )

    def test_correction_obsoletes_old_index_and_indexes_only_current_version(self):
        self.client.force_authenticate(user=self.member)
        preserved = self.client.post(
            self.knowledge_url,
            {'message_id': self.message.id},
            format='json'
        )
        knowledge_id = preserved.data['id']
        correction = self.client.post(
            self.knowledge_url + '%s/corrections/' % knowledge_id,
            {'content': 'A newer indexed answer.'},
            format='json'
        )
        self.assertEqual(correction.status_code, 201)
        jobs = KnowledgeIndexingJob.objects.filter(knowledge_id=knowledge_id).order_by('version_id')
        self.assertEqual(jobs.count(), 2)
        self.assertEqual(jobs[0].status, KnowledgeIndexingJob.Status.OBSOLETE)
        self.assertEqual(jobs[1].status, KnowledgeIndexingJob.Status.INDEXED)
        chunks = self.client.get(self.knowledge_url + '%s/chunks/' % knowledge_id)
        self.assertEqual(chunks.data['chunks'][0]['version_id'], correction.data['current_version']['id'])

    def test_index_failure_is_recorded_and_retry_recovers(self):
        self.client.force_authenticate(user=self.member)
        preserved = self.client.post(
            self.knowledge_url,
            {'message_id': self.message.id},
            format='json'
        )
        knowledge_id = preserved.data['id']
        job = KnowledgeIndexingJob.objects.get(knowledge_id=knowledge_id)
        job.status = KnowledgeIndexingJob.Status.OBSOLETE
        job.save(update_fields=('status', 'update_date'))
        with patch(
            'community.indexing.chunk_content',
            side_effect=RuntimeError('simulated failure')
        ):
            failed = index_knowledge(knowledge_id)
        self.assertEqual(failed.status, KnowledgeIndexingJob.Status.FAILED)
        self.assertIn('simulated failure', failed.error_message)
        recovered = index_knowledge(knowledge_id)
        self.assertEqual(recovered.status, KnowledgeIndexingJob.Status.INDEXED)
        self.assertEqual(recovered.attempt_count, 3)

    def test_chunking_normalizes_text_and_uses_overlap(self):
        chunks = chunk_content('  One\n two   three.  ')
        self.assertEqual([chunk.content for chunk in chunks], ['One two three.'])
        long_text = ' '.join('word%03d' % index for index in range(250))
        chunks = chunk_content(long_text)
        self.assertGreater(len(chunks), 1)
        self.assertLessEqual(max(len(chunk.content) for chunk in chunks), 1000)
        self.assertTrue(set(chunks[0].content.split()) & set(chunks[1].content.split()))

    def test_corrections_are_authorized_transactional_and_immutable(self):
        self.client.force_authenticate(user=self.member)
        preserved = self.client.post(
            self.knowledge_url,
            {'message_id': self.message.id},
            format='json'
        )
        knowledge_id = preserved.data['id']
        detail_url = self.knowledge_url + '%s/' % knowledge_id
        correction_url = detail_url + 'corrections/'
        history_url = detail_url + 'history/'

        self.message.message = 'A source edit that is not a curated correction.'
        self.message.save(update_fields=('message', 'update_date'))
        detail = self.client.get(detail_url)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(
            detail.data['source_message']['content'],
            'A source edit that is not a curated correction.'
        )
        self.assertEqual(detail.data['current_version']['content'], 'A reusable answer.')

        correction = self.client.post(
            correction_url,
            {
                'content': 'The corrected reusable answer.',
                'explanation': 'Clarified the example.'
            },
            format='json'
        )
        self.assertEqual(correction.status_code, 201)
        self.assertEqual(correction.data['current_version']['version_number'], 2)
        self.assertEqual(correction.data['current_version']['created_by_username'], self.member.username)
        self.assertEqual(correction.data['version_count'], 2)

        history = self.client.get(history_url)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data['current_version'], correction.data['current_version']['id'])
        self.assertEqual(
            [version['content'] for version in history.data['versions']],
            ['The corrected reusable answer.', 'A reusable answer.']
        )
        self.assertEqual(history.data['versions'][0]['explanation'], 'Clarified the example.')
        self.assertTrue(history.data['versions'][0]['is_current'])
        self.assertFalse(history.data['versions'][1]['is_current'])

        self.client.force_authenticate(user=self.other_member)
        denied = self.client.post(
            correction_url,
            {'content': 'An unauthorized rewrite.'},
            format='json'
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(KnowledgeVersion.objects.filter(knowledge_id=knowledge_id).count(), 2)

        self.client.force_authenticate(user=self.member)
        self.assertEqual(self.client.post(detail_url + 'withdraw/').status_code, 204)
        withdrawn_correction = self.client.post(
            correction_url,
            {'content': 'This must not be accepted.'},
            format='json'
        )
        self.assertEqual(withdrawn_correction.status_code, 400)

    def test_preservation_rejects_direct_messages_and_other_spaces(self):
        self.client.force_authenticate(user=self.member)
        direct_chat = ChatSession.objects.create(owner=self.member)
        direct_message = ChatSessionMessage.objects.create(
            chat_session=direct_chat,
            user=self.member,
            message='Private message.'
        )
        self.assertEqual(
            self.client.post(
                self.knowledge_url,
                {'message_id': direct_message.id},
                format='json'
            ).status_code,
            404
        )

        other_space = Space.objects.create(
            owner=self.outsider,
            name='Other Knowledge Space',
            purpose='Separate content.'
        )
        other_channel = create_test_channel(other_space, self.outsider)
        other_message = ChatSessionMessage.objects.create(
            chat_session=other_channel.conversation,
            user=self.outsider,
            message='Other Space answer.'
        )
        self.assertEqual(
            self.client.post(
                self.knowledge_url,
                {'message_id': other_message.id},
                format='json'
            ).status_code,
            404
        )
        self.client.force_authenticate(user=self.outsider)
        self.assertEqual(self.client.get(self.knowledge_url).status_code, 404)

    def test_preserver_can_withdraw_and_members_cannot_read_after_membership_loss(self):
        self.client.force_authenticate(user=self.member)
        preserved = self.client.post(
            self.knowledge_url,
            {'message_id': self.message.id},
            format='json'
        )
        withdraw_url = self.knowledge_url + '%s/withdraw/' % preserved.data['id']

        withdrawn = self.client.post(withdraw_url)
        self.assertEqual(withdrawn.status_code, 204)
        self.assertEqual(self.client.get(self.knowledge_url).data, [])

        self.client.force_authenticate(user=self.other_member)
        self.assertEqual(self.client.get(self.knowledge_url).data, [])
        self.space.memberships.filter(user=self.other_member).delete()
        self.assertEqual(self.client.get(self.knowledge_url).status_code, 404)

    def test_space_deletion_is_blocked_until_preserved_knowledge_is_withdrawn(self):
        self.client.force_authenticate(user=self.member)
        self.client.post(
            self.knowledge_url,
            {'message_id': self.message.id},
            format='json'
        )
        self.client.force_authenticate(user=self.owner)
        blocked = self.client.delete('/api/spaces/%s/' % self.space.id)
        self.assertEqual(blocked.status_code, 409)


class SourceMessageLifecycleAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='lifecycle_owner', password='LifecycleOwner123!')
        self.member = User.objects.create_user(username='lifecycle_member', password='LifecycleMember123!')
        self.other = User.objects.create_user(username='lifecycle_other', password='LifecycleOther123!')
        self.space = Space.objects.create(
            owner=self.owner,
            name='Lifecycle Space',
            purpose='Test source lifecycle.'
        )
        SpaceMembership.objects.create(space=self.space, user=self.member, role=MEMBER)
        SpaceMembership.objects.create(space=self.space, user=self.other, role=MEMBER)
        self.channel = create_test_channel(self.space, self.owner)
        self.message = ChatSessionMessage.objects.create(
            chat_session=self.channel.conversation,
            user=self.member,
            message='Original source content.'
        )
        self.client = APIClient()
        self.message_url = (
            '/api/spaces/%s/channels/%s/messages/%s/'
            % (self.space.id, self.channel.id, self.message.id)
        )
        self.messages_url = (
            '/api/spaces/%s/channels/%s/messages/'
            % (self.space.id, self.channel.id)
        )

    def test_author_edit_creates_source_revision_and_marks_knowledge_for_review(self):
        self.client.force_authenticate(user=self.member)
        preserved = self.client.post(
            '/api/spaces/%s/knowledge/' % self.space.id,
            {'message_id': self.message.id},
            format='json'
        )
        self.assertEqual(preserved.status_code, 201)

        edited = self.client.patch(
            self.message_url,
            {'message': 'Edited source content.'},
            format='json'
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.data['message'], 'Edited source content.')
        revision = self.message.revisions.get()
        self.assertEqual(revision.revision_number, 1)
        self.assertEqual(revision.content, 'Original source content.')
        self.assertEqual(revision.changed_by, self.member)
        self.assertEqual(
            PreservedKnowledge.objects.get(pk=preserved.data['id']).status,
            PreservedKnowledge.Status.NEEDS_REVIEW
        )
        job = KnowledgeIndexingJob.objects.get(knowledge_id=preserved.data['id'])
        self.assertEqual(job.status, KnowledgeIndexingJob.Status.OBSOLETE)
        self.assertIsNotNone(job.chunks.get().invalidated_at)
        self.assertEqual(
            job.embedding_status,
            KnowledgeIndexingJob.EmbeddingStatus.OBSOLETE
        )

        history = self.client.get(self.message_url + 'revisions/')
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data['current']['content'], 'Edited source content.')
        self.assertEqual(history.data['revisions'][0]['content'], 'Original source content.')

    def test_only_author_or_manager_can_change_and_delete_source(self):
        self.client.force_authenticate(user=self.other)
        self.assertEqual(self.client.patch(self.message_url, {'message': 'Nope'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(self.message_url).status_code, 403)

        self.client.force_authenticate(user=self.owner)
        deleted = self.client.delete(self.message_url)
        self.assertEqual(deleted.status_code, 204)
        self.assertIsNotNone(ChatSessionMessage.objects.get(pk=self.message.id).deleted_at)
        self.assertEqual(self.client.get(self.messages_url).data['messages'], [])

    def test_source_deletion_marks_active_knowledge_source_deleted_but_preserves_withdrawn(self):
        self.client.force_authenticate(user=self.member)
        preserved = self.client.post(
            '/api/spaces/%s/knowledge/' % self.space.id,
            {'message_id': self.message.id},
            format='json'
        )
        self.assertEqual(preserved.status_code, 201)
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.delete(self.message_url).status_code, 204)
        self.assertEqual(
            PreservedKnowledge.objects.get(pk=preserved.data['id']).status,
            PreservedKnowledge.Status.SOURCE_DELETED
        )
        self.assertEqual(
            KnowledgeIndexingJob.objects.get(knowledge_id=preserved.data['id']).status,
            KnowledgeIndexingJob.Status.OBSOLETE
        )
        self.assertEqual(
            KnowledgeIndexingJob.objects.get(knowledge_id=preserved.data['id']).embedding_status,
            KnowledgeIndexingJob.EmbeddingStatus.OBSOLETE
        )


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
