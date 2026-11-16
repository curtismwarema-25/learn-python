from unittest.mock import patch

from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings

from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from fuego.asgi import application
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

    def test_owner_can_read_messages(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.messages_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['messages']), 1)

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
            '/api/chats/%s/join/' % self.chat.uri
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            self.chat.members.filter(user=self.other_user).exists()
        )

        response = self.client.get(self.messages_url)
        self.assertEqual(response.status_code, 200)

    def test_joining_chat_twice_does_not_duplicate_membership(self):
        self.client.force_authenticate(user=self.other_user)
        join_url = '/api/chats/%s/join/' % self.chat.uri

        self.client.post(join_url)
        response = self.client.post(join_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.chat.members.filter(user=self.other_user).count(),
            1
        )


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

    def test_owner_can_receive_messages_over_websocket(self):
        async def post_message_and_receive():
            communicator = WebsocketCommunicator(
                application,
                '/ws/chats/%s/?token=%s' % (
                    self.chat.uri,
                    self.owner_token.key
                )
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

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
                '/ws/chats/%s/?token=%s' % (
                    self.chat.uri,
                    self.other_token.key
                )
            )
            return await communicator.connect()

        connected, close_code = async_to_sync(connect_as_non_member)()

        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)

    def test_invited_member_can_join_and_receive_websocket_messages(self):
        async def join_and_receive():
            member_client = APIClient()
            member_client.credentials(
                HTTP_AUTHORIZATION='Token %s' % self.other_token.key
            )
            join_response = await sync_to_async(
                member_client.post,
                thread_sensitive=True
            )('/api/chats/%s/join/' % self.chat.uri)

            communicator = WebsocketCommunicator(
                application,
                '/ws/chats/%s/?token=%s' % (
                    self.chat.uri,
                    self.other_token.key
                )
            )
            connected, _ = await communicator.connect()

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
                message_response.status_code,
                received_message
            )

        join_status, connected, message_status, received_message = async_to_sync(
            join_and_receive
        )()

        self.assertEqual(join_status, 200)
        self.assertTrue(connected)
        self.assertEqual(message_status, 201)
        self.assertEqual(received_message['message'], 'Invitee can receive this')