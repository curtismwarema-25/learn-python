import json
from datetime import timedelta
from unittest.mock import patch

from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from fuego.asgi import application
from . import websocket as websocket_bridge
from .models import ChatSession, ChatSessionMessage


User = get_user_model()


class ChatAccessControlTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='chat_owner',
            email='owner@example.com',
            password='TestOwnerPassword123!'
        )

        self.other_user = User.objects.create_user(
            username='chat_other',
            email='other@example.com',
            password='TestOtherPassword123!'
        )

        self.chat = ChatSession.objects.create(owner=self.owner)
        self.chat.rotate_invite()

        self.message = ChatSessionMessage.objects.create(
            user=self.owner,
            chat_session=self.chat,
            message='Private test message'
        )

        self.client = APIClient()
        self.messages_url = (
            f'/api/chats/{self.chat.uri}/messages/'
        )
        self.chat_url = f'/api/chats/{self.chat.uri}/'

    def test_chat_invite_uri_is_unique_in_the_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ChatSession.objects.create(
                    owner=self.owner,
                    uri=self.chat.uri
                )

    def test_chat_membership_is_unique_in_the_database(self):
        self.chat.members.create(user=self.other_user)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.chat.members.create(user=self.other_user)

    def test_chat_creation_provisions_a_seven_day_invite(self):
        self.client.force_authenticate(user=self.owner)
        before_creation = timezone.now()

        response = self.client.post('/api/chats/')

        self.assertEqual(response.status_code, 201)
        chat_session = ChatSession.objects.get(uri=response.data['uri'])
        self.assertIsNotNone(chat_session.invite_token)
        self.assertAlmostEqual(
            (chat_session.invite_expires_at - before_creation).total_seconds(),
            timedelta(days=7).total_seconds(),
            delta=2
        )

    def test_owner_can_read_messages(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.messages_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['messages']), 1)
        self.assertEqual(
            response.data['messages'][0]['user'],
            {'username': self.owner.username}
        )

    def test_non_member_cannot_read_messages(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.messages_url)

        self.assertEqual(response.status_code, 404)

    def test_non_member_cannot_send_messages(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            self.messages_url,
            {'message': 'Unauthorized message'},
            format='json'
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            ChatSessionMessage.objects.filter(
                chat_session=self.chat
            ).count(),
            1
        )

    def test_non_owner_cannot_add_members(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.patch(
            self.chat_url,
            {'username': 'chat_other'},
            format='json'
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            self.chat.members.filter(user=self.other_user).exists()
        )

    def test_owner_can_add_member(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            self.chat_url,
            {'username': 'chat_other'},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            self.chat.members.filter(user=self.other_user).exists()
        )
        self.assertEqual(
            response.data['user'],
            {'username': self.other_user.username}
        )
        self.assertEqual(
            response.data['members'],
            [{'username': self.owner.username},
             {'username': self.other_user.username}]
        )

    def test_member_can_read_messages(self):
        self.chat.members.create(user=self.other_user)

        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.messages_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['messages']), 1)

    def test_member_can_send_messages(self):
        self.chat.members.create(user=self.other_user)

        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            self.messages_url,
            {'message': 'Hello from a member'},
            format='json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data['user'],
            {'username': self.other_user.username}
        )
        self.assertEqual(
            ChatSessionMessage.objects.filter(
                chat_session=self.chat
            ).count(),
            2
        )

    def test_message_is_published_to_rabbitmq_when_enabled(self):
        self.client.force_authenticate(user=self.owner)

        with override_settings(
            CHAT_RABBITMQ_ENABLED=True,
            CHAT_RABBITMQ_HOST='rabbit-test'
        ):
            with patch('chat.channels.pika.BlockingConnection') as connect:
                response = self.client.post(
                    self.messages_url,
                    {'message': 'RabbitMQ delivery'},
                    format='json'
                )

        self.assertEqual(response.status_code, 201)
        connect.assert_called_once()
        connection_parameters = connect.call_args.args[0]
        self.assertEqual(connection_parameters.host, 'rabbit-test')

        channel = connect.return_value.channel.return_value
        channel.exchange_declare.assert_called_once_with(
            exchange=self.chat.uri,
            exchange_type='fanout'
        )
        self.assertEqual(
            channel.basic_publish.call_args.kwargs['exchange'],
            self.chat.uri
        )

    def test_authenticated_user_can_join_from_invite_url(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            '/api/chats/invites/join/',
            {'token': self.chat.invite_token},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            self.chat.members.filter(user=self.other_user).exists()
        )

        response = self.client.get(self.messages_url)
        self.assertEqual(response.status_code, 200)

    def test_joining_chat_twice_does_not_duplicate_membership(self):
        self.client.force_authenticate(user=self.other_user)
        join_url = '/api/chats/invites/join/'
        self.client.post(
            join_url,
            {'token': self.chat.invite_token},
            format='json'
        )
        response = self.client.post(
            join_url,
            {'token': self.chat.invite_token},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.chat.members.filter(user=self.other_user).count(),
            1
        )

    def test_chat_uri_is_not_an_invite_token(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            '/api/chats/invites/join/',
            {'token': self.chat.uri},
            format='json'
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            self.chat.members.filter(user=self.other_user).exists()
        )

    def test_expired_invite_cannot_be_used(self):
        self.chat.invite_expires_at = timezone.now() - timedelta(seconds=1)
        self.chat.save(update_fields=('invite_expires_at',))

        self.client.force_authenticate(user=self.owner)
        invite_status = self.client.get(
            '/api/chats/%s/invite/' % self.chat.uri
        )
        self.assertIsNone(invite_status.data['token'])
        self.assertIsNotNone(invite_status.data['expires_at'])

        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            '/api/chats/invites/join/',
            {'token': self.chat.invite_token},
            format='json'
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            self.chat.members.filter(user=self.other_user).exists()
        )

    def test_invite_join_requires_a_token_in_the_request_body(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            '/api/chats/invites/join/',
            {},
            format='json'
        )

        self.assertEqual(response.status_code, 400)

    def test_owner_can_rotate_and_revoke_invite(self):
        self.client.force_authenticate(user=self.owner)
        old_token = self.chat.invite_token
        invite_url = '/api/chats/%s/invite/' % self.chat.uri

        current = self.client.get(invite_url)
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.data['token'], old_token)

        rotated = self.client.post(invite_url)

        self.assertEqual(rotated.status_code, 200)
        self.assertNotEqual(rotated.data['token'], old_token)
        self.assertEqual(rotated.data['can_manage'], True)
        self.assertAlmostEqual(
            (rotated.data['expires_at'] - timezone.now()).total_seconds(),
            timedelta(days=7).total_seconds(),
            delta=2
        )

        self.client.force_authenticate(user=self.other_user)
        old_link = self.client.post(
            '/api/chats/invites/join/',
            {'token': old_token},
            format='json'
        )
        self.assertEqual(old_link.status_code, 404)

        self.client.force_authenticate(user=self.owner)
        revoked = self.client.delete(invite_url)

        self.assertEqual(revoked.status_code, 200)
        self.chat.refresh_from_db()
        self.assertIsNone(self.chat.invite_token)
        self.assertIsNone(self.chat.invite_expires_at)

    def test_only_chat_owner_can_manage_invites(self):
        self.chat.members.create(user=self.other_user)
        self.client.force_authenticate(user=self.other_user)
        invite_url = '/api/chats/%s/invite/' % self.chat.uri

        response = self.client.post(invite_url)
        revoke_response = self.client.delete(invite_url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(revoke_response.status_code, 403)

    def test_members_cannot_retrieve_invite_token(self):
        self.chat.members.create(user=self.other_user)
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(
            '/api/chats/%s/invite/' % self.chat.uri
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['can_manage'], False)
        self.assertIsNone(response.data['token'])


class AuthenticationFlowTests(TestCase):
    def test_registered_user_can_log_in_and_receive_a_token(self):
        registration = self.client.post(
            '/auth/users/',
            {
                'email': 'new-user@example.com',
                'username': 'new_chat_user',
                'password': 'StrongTestPassword123!'
            },
            format='json'
        )

        self.assertEqual(registration.status_code, 201)

        login = self.client.post(
            '/auth/token/login/',
            {
                'username': 'new_chat_user',
                'password': 'StrongTestPassword123!'
            },
            format='json'
        )

        self.assertEqual(login.status_code, 200)
        self.assertIn('auth_token', login.data)


class ChatWebSocketTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='socket_owner',
            email='socket-owner@example.com',
            password='TestOwnerPassword123!'
        )
        self.other_user = User.objects.create_user(
            username='socket_other',
            email='socket-other@example.com',
            password='TestOtherPassword123!'
        )
        self.chat = ChatSession.objects.create(owner=self.owner)
        self.owner_token = Token.objects.create(user=self.owner)
        self.other_token = Token.objects.create(user=self.other_user)
        self.chat.rotate_invite()

    def test_owner_can_receive_messages_over_websocket(self):
        async def post_message_and_receive():
            communicator = WebsocketCommunicator(
                application,
                '/ws/chats/%s/' % self.chat.uri
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to({
                'type': 'authenticate',
                'token': self.owner_token.key
            })
            self.assertEqual(
                await communicator.receive_json_from(),
                {'type': 'authenticated'}
            )

            client = APIClient()
            client.credentials(
                HTTP_AUTHORIZATION='Token %s' % self.owner_token.key
            )
            response = await sync_to_async(
                client.post,
                thread_sensitive=True
            )(
                '/api/chats/%s/messages/' % self.chat.uri,
                {'message': 'Hello over WebSocket'},
                format='json'
            )
            received_message = await communicator.receive_json_from()
            await communicator.disconnect()
            return response.status_code, response.data, received_message

        response_status, response_data, received_message = async_to_sync(
            post_message_and_receive
        )()

        self.assertEqual(response_status, 201)
        self.assertEqual(
            received_message,
            {
                'id': response_data['id'],
                'user': response_data['user'],
                'message': response_data['message']
            }
        )

    def test_non_member_cannot_connect_to_chat_websocket(self):
        async def connect_as_non_member():
            communicator = WebsocketCommunicator(
                application,
                '/ws/chats/%s/' % self.chat.uri
            )
            connected, _ = await communicator.connect()
            await communicator.send_json_to({
                'type': 'authenticate',
                'token': self.other_token.key
            })
            output = await communicator.receive_output()
            await communicator.wait()
            return connected, output

        connected, close_output = async_to_sync(connect_as_non_member)()

        self.assertTrue(connected)
        self.assertEqual(close_output['type'], 'websocket.close')
        self.assertEqual(close_output['code'], 4403)

    def test_query_string_token_alone_does_not_authenticate_websocket(self):
        async def connect_with_query_token():
            communicator = WebsocketCommunicator(
                application,
                '/ws/chats/%s/?token=%s' % (
                    self.chat.uri,
                    self.owner_token.key
                )
            )
            connected, _ = await communicator.connect()
            await communicator.send_json_to({'type': 'ping'})
            output = await communicator.receive_output()
            await communicator.wait()
            return connected, output

        connected, close_output = async_to_sync(
            connect_with_query_token
        )()

        self.assertTrue(connected)
        self.assertEqual(close_output['type'], 'websocket.close')
        self.assertEqual(close_output['code'], 4401)

    def test_invited_member_can_join_and_receive_websocket_messages(self):
        async def join_and_receive():
            member_client = APIClient()
            member_client.credentials(
                HTTP_AUTHORIZATION='Token %s' % self.other_token.key
            )
            join_response = await sync_to_async(
                member_client.post,
                thread_sensitive=True
            )(
                '/api/chats/invites/join/',
                {'token': self.chat.invite_token},
                format='json'
            )

            communicator = WebsocketCommunicator(
                application,
                '/ws/chats/%s/' % self.chat.uri
            )
            connected, _ = await communicator.connect()
            await communicator.send_json_to({
                'type': 'authenticate',
                'token': self.other_token.key
            })
            auth_response = await communicator.receive_json_from()

            owner_client = APIClient()
            owner_client.credentials(
                HTTP_AUTHORIZATION='Token %s' % self.owner_token.key
            )
            message_response = await sync_to_async(
                owner_client.post,
                thread_sensitive=True
            )(
                '/api/chats/%s/messages/' % self.chat.uri,
                {'message': 'Invitee can receive this'},
                format='json'
            )
            received_message = await communicator.receive_json_from()
            await communicator.disconnect()
            return (
                join_response.status_code,
                connected,
                auth_response,
                message_response.status_code,
                received_message
            )

        join_status, connected, auth_response, message_status, received_message = async_to_sync(
            join_and_receive
        )()

        self.assertEqual(join_status, 200)
        self.assertTrue(connected)
        self.assertEqual(auth_response, {'type': 'authenticated'})
        self.assertEqual(message_status, 201)
        self.assertEqual(received_message['message'], 'Invitee can receive this')

    def test_revoked_token_closes_an_existing_socket_before_delivery(self):
        async def revoke_and_send():
            await sync_to_async(
                self.chat.members.create,
                thread_sensitive=True
            )(user=self.other_user)
            communicator = WebsocketCommunicator(
                application,
                '/ws/chats/%s/' % self.chat.uri
            )
            connected, _ = await communicator.connect()
            await communicator.send_json_to({
                'type': 'authenticate',
                'token': self.other_token.key
            })
            await communicator.receive_json_from()
            await sync_to_async(
                Token.objects.filter(key=self.other_token.key).delete,
                thread_sensitive=True
            )()

            client = APIClient()
            client.credentials(
                HTTP_AUTHORIZATION='Token %s' % self.owner_token.key
            )
            await sync_to_async(
                client.post,
                thread_sensitive=True
            )(
                '/api/chats/%s/messages/' % self.chat.uri,
                {'message': 'This should not reach the revoked socket'},
                format='json'
            )
            close_output = await communicator.receive_output()
            await communicator.wait()
            return connected, close_output

        connected, close_output = async_to_sync(revoke_and_send)()

        self.assertTrue(connected)
        self.assertEqual(close_output['type'], 'websocket.close')
        self.assertEqual(close_output['code'], 4403)

    def test_removed_membership_closes_an_existing_socket_before_delivery(self):
        async def remove_member_and_send():
            await sync_to_async(
                self.chat.members.create,
                thread_sensitive=True
            )(user=self.other_user)
            communicator = WebsocketCommunicator(
                application,
                '/ws/chats/%s/' % self.chat.uri
            )
            connected, _ = await communicator.connect()
            await communicator.send_json_to({
                'type': 'authenticate',
                'token': self.other_token.key
            })
            await communicator.receive_json_from()
            await sync_to_async(
                self.chat.members.filter(user=self.other_user).delete,
                thread_sensitive=True
            )()

            owner_client = APIClient()
            owner_client.credentials(
                HTTP_AUTHORIZATION='Token %s' % self.owner_token.key
            )
            await sync_to_async(
                owner_client.post,
                thread_sensitive=True
            )(
                '/api/chats/%s/messages/' % self.chat.uri,
                {'message': 'The removed member must not receive this'},
                format='json'
            )
            close_output = await communicator.receive_output()
            await communicator.wait()
            return connected, close_output

        connected, close_output = async_to_sync(
            remove_member_and_send
        )()

        self.assertTrue(connected)
        self.assertEqual(close_output['type'], 'websocket.close')
        self.assertEqual(close_output['code'], 4403)

    def test_uwsgi_bridge_authenticates_from_first_frame_not_query(self):
        class UWSGIStub:
            def __init__(self):
                self.frames = [json.dumps({
                    'type': 'authenticate',
                    'token': self_token
                })]
                self.sent = []

            def websocket_handshake(self, key, origin):
                self.handshake = (key, origin)

            def websocket_recv_nb(self):
                return self.frames.pop(0) if self.frames else None

            def websocket_send(self, payload):
                self.sent.append(payload)

        self_token = self.owner_token.key
        uwsgi_stub = UWSGIStub()
        env = {
            'PATH_INFO': '/ws/chats/%s/' % self.chat.uri,
            'QUERY_STRING': 'token=%s' % self.other_token.key,
            'HTTP_SEC_WEBSOCKET_KEY': 'socket-key',
            'HTTP_ORIGIN': 'http://localhost'
        }
        def start_response(status, headers):
            return None

        with patch.dict('sys.modules', {'uwsgi': uwsgi_stub}):
            with patch('chat.websocket.pika.BlockingConnection') as connect:
                channel = connect.return_value.channel.return_value
                channel.queue_declare.return_value.method.queue = 'queue'
                channel.consume.return_value = []

                result = websocket_bridge.application(env, start_response)

        self.assertEqual(result, [])
        self.assertEqual(
            uwsgi_stub.sent,
            [json.dumps({'type': 'authenticated'})]
        )
        self.assertEqual(uwsgi_stub.handshake, ('socket-key', 'http://localhost'))
        connect.assert_called_once()

    def test_uwsgi_bridge_does_not_authenticate_from_query_alone(self):
        class UWSGIStub:
            def __init__(self):
                self.handshakes = 0

            def websocket_handshake(self, key, origin):
                self.handshakes += 1

            def websocket_recv_nb(self):
                return None

        uwsgi_stub = UWSGIStub()
        env = {
            'PATH_INFO': '/ws/chats/%s/' % self.chat.uri,
            'QUERY_STRING': 'token=%s' % self.owner_token.key,
            'HTTP_SEC_WEBSOCKET_KEY': 'socket-key',
            'HTTP_ORIGIN': 'http://localhost'
        }
        def start_response(status, headers):
            return None

        with patch.dict('sys.modules', {'uwsgi': uwsgi_stub}):
            with patch(
                'chat.websocket.WEBSOCKET_AUTH_TIMEOUT_SECONDS',
                0
            ):
                with patch('chat.websocket.pika.BlockingConnection') as connect:
                    result = websocket_bridge.application(env, start_response)

        self.assertEqual(result, [])
        self.assertEqual(uwsgi_stub.handshakes, 1)
        connect.assert_not_called()