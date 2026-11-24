from datetime import datetime, timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import APIClient

from chat.models import ChatSession, ChatSessionMessage

from .models import (
    Channel,
    KnowledgeVersion,
    PreservedKnowledge,
    Resource,
    Space,
    SpaceMembership
)
from .permissions import MEMBER


User = get_user_model()


class SpaceSearchAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='search_owner',
            email='search-owner@example.com',
            password='SearchOwner123!'
        )
        self.member = User.objects.create_user(
            username='search_member',
            email='search-member@example.com',
            password='SearchMember123!'
        )
        self.outsider = User.objects.create_user(
            username='search_outsider',
            password='SearchOutside123!'
        )
        self.space = Space.objects.create(
            owner=self.owner,
            name='Python Learners',
            purpose='Share practical Python learning.'
        )
        SpaceMembership.objects.create(
            space=self.space,
            user=self.member,
            role=MEMBER
        )
        self.channel = self.create_channel(self.space, self.owner, 'general')
        self.client = APIClient()
        self.client.force_authenticate(user=self.member)
        self.search_url = f'/api/spaces/{self.space.pk}/search/'

    def create_channel(self, space, owner, name):
        conversation = ChatSession.objects.create(owner=owner)
        return Channel.objects.create(
            space=space,
            conversation=conversation,
            name=name,
            created_by=owner
        )

    def create_message(self, channel, user, content, created_at=None):
        message = ChatSessionMessage.objects.create(
            chat_session=channel.conversation,
            user=user,
            message=content
        )
        if created_at is not None:
            ChatSessionMessage.objects.filter(pk=message.pk).update(
                create_date=created_at
            )
            message.refresh_from_db()
        return message

    def create_resource(self, space=None, **values):
        return Resource.objects.create(
            space=space or self.space,
            created_by=values.pop('created_by', self.owner),
            title=values.pop('title', 'Python reference'),
            description=values.pop('description', 'A practical guide.'),
            external_url=values.pop(
                'external_url',
                'https://docs.example.test/python'
            ),
            **values
        )

    def test_search_is_space_scoped_and_excludes_direct_archived_and_deleted_resources(self):
        self.channel.archived_at = datetime.now(datetime_timezone.utc)
        self.channel.save(update_fields=('archived_at',))
        message = self.create_message(
            self.channel,
            self.member,
            'Use a Python virtual environment (venv).'
        )
        resource = self.create_resource(
            title='Python venv setup',
            description='Create one environment per project.'
        )
        self.create_resource(
            title='Archived Python reference',
            status=Resource.Status.ARCHIVED
        )
        self.create_resource(
            title='',
            description='',
            external_url='',
            status=Resource.Status.DELETED
        )

        direct_chat = ChatSession.objects.create(owner=self.member)
        ChatSessionMessage.objects.create(
            chat_session=direct_chat,
            user=self.member,
            message='Private Python venv discussion.'
        )
        other_space = Space.objects.create(
            owner=self.outsider,
            name='Other Space',
            purpose='Private knowledge.'
        )
        other_channel = self.create_channel(
            other_space,
            self.outsider,
            'python-help'
        )
        self.create_message(
            other_channel,
            self.outsider,
            'Python venv discussion in another Space.'
        )
        self.create_resource(
            space=other_space,
            title='Other Space Python venv guide'
        )

        response = self.client.get(self.search_url, {
            'q': '  PYTHON,   venv  '
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        results = response.data['results']
        self.assertEqual(
            {result['type'] for result in results},
            {'discussion', 'resource'}
        )
        discussion = next(result for result in results if result['type'] == 'discussion')
        resource_result = next(result for result in results if result['type'] == 'resource')
        self.assertEqual(discussion['id'], str(message.pk))
        self.assertEqual(discussion['channel']['id'], str(self.channel.pk))
        self.assertEqual(discussion['author'], self.member.username)
        self.assertNotIn('email', discussion)
        self.assertEqual(resource_result['id'], str(resource.pk))
        self.assertEqual(resource_result['source_domain'], 'docs.example.test')
        self.assertNotIn('Private Python', str(results))
        self.assertNotIn('Other Space', str(results))

    def test_content_type_channel_and_space_filters_compose(self):
        other_channel = self.create_channel(self.space, self.owner, 'packaging')
        general_message = self.create_message(
            self.channel,
            self.member,
            'Python packaging basics.'
        )
        self.create_message(
            other_channel,
            self.owner,
            'Python packaging workflow.'
        )
        resource = self.create_resource(title='Python packaging reference')

        discussions = self.client.get(self.search_url, {
            'q': 'python packaging',
            'content_type': 'discussions',
            'channel_id': str(self.channel.pk)
        })
        resources = self.client.get(self.search_url, {
            'q': 'python packaging',
            'content_type': 'resources'
        })
        combined = self.client.get(self.search_url, {
            'q': 'python packaging',
            'channel_id': str(self.channel.pk)
        })

        self.assertEqual(discussions.status_code, 200)
        self.assertEqual(discussions.data['count'], 1)
        self.assertEqual(discussions.data['results'][0]['id'], str(general_message.pk))
        self.assertEqual(resources.status_code, 200)
        self.assertEqual(resources.data['count'], 1)
        self.assertEqual(resources.data['results'][0]['id'], str(resource.pk))
        self.assertEqual(combined.status_code, 200)
        self.assertEqual(
            {result['type'] for result in combined.data['results']},
            {'discussion', 'resource'}
        )

        other_space = Space.objects.create(
            owner=self.outsider,
            name='Separate Space',
            purpose='Separate content.'
        )
        foreign_channel = self.create_channel(
            other_space,
            self.outsider,
            'private'
        )
        foreign_filter = self.client.get(self.search_url, {
            'q': 'python',
            'channel_id': str(foreign_channel.pk)
        })
        incompatible_filter = self.client.get(self.search_url, {
            'q': 'python',
            'content_type': 'resources',
            'channel_id': str(self.channel.pk)
        })
        self.assertEqual(foreign_filter.status_code, 404)
        self.assertEqual(incompatible_filter.status_code, 400)

    def test_active_preserved_knowledge_is_searchable_without_duplicate_source(self):
        message = self.create_message(
            self.channel,
            self.member,
            'A preserved Python answer.'
        )
        knowledge = PreservedKnowledge.objects.create(
            space=self.space,
            source_message=message,
            preserved_by=self.member
        )
        version = KnowledgeVersion.objects.create(
            knowledge=knowledge,
            source_message=message,
            version_number=1,
            content=message.message,
            created_by=self.member
        )
        knowledge.current_version = version
        knowledge.save(update_fields=('current_version',))
        ordinary = self.create_message(
            self.channel,
            self.member,
            'Another ordinary Python discussion.'
        )

        response = self.client.get(self.search_url, {'q': 'Python'})
        knowledge_only = self.client.get(
            self.search_url,
            {'q': 'Python', 'content_type': 'knowledge'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {result['type'] for result in response.data['results']},
            {'knowledge', 'discussion'}
        )
        self.assertEqual(
            len([result for result in response.data['results'] if result['id'] == str(message.pk)]),
            1
        )
        result = next(result for result in response.data['results'] if result['type'] == 'knowledge')
        self.assertEqual(result['id'], str(message.pk))
        self.assertEqual(result['source_message_id'], str(message.pk))
        self.assertEqual(result['knowledge_id'], knowledge.pk)
        self.assertEqual(result['channel']['id'], str(self.channel.pk))
        self.assertEqual(result['author'], self.member.username)
        self.assertEqual(
            next(result for result in response.data['results'] if result['id'] == str(ordinary.pk))['type'],
            'discussion'
        )
        self.assertEqual(knowledge_only.data['count'], 1)
        self.assertEqual(knowledge_only.data['results'][0]['type'], 'knowledge')

    def test_withdrawn_knowledge_is_excluded_from_knowledge_search(self):
        message = self.create_message(
            self.channel,
            self.member,
            'Withdrawn Python answer.'
        )
        PreservedKnowledge.objects.create(
            space=self.space,
            source_message=message,
            preserved_by=self.member,
            status=PreservedKnowledge.Status.WITHDRAWN,
            withdrawn_at=datetime(2026, 11, 23, tzinfo=datetime_timezone.utc),
            withdrawn_by=self.member
        )

        response = self.client.get(
            self.search_url,
            {'q': 'Withdrawn Python', 'content_type': 'knowledge'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['results'], [])

    def test_knowledge_search_uses_only_the_current_version_snapshot(self):
        message = self.create_message(
            self.channel,
            self.member,
            'Original answer wording.'
        )
        knowledge = PreservedKnowledge.objects.create(
            space=self.space,
            source_message=message,
            preserved_by=self.member
        )
        original = KnowledgeVersion.objects.create(
            knowledge=knowledge,
            source_message=message,
            version_number=1,
            content='Original answer wording.',
            created_by=self.member
        )
        current = KnowledgeVersion.objects.create(
            knowledge=knowledge,
            source_message=message,
            version_number=2,
            content='Corrected answer wording.',
            explanation='Clarified the wording.',
            created_by=self.member
        )
        knowledge.current_version = current
        knowledge.save(update_fields=('current_version',))

        old_search = self.client.get(self.search_url, {
            'q': 'Original answer',
            'content_type': 'knowledge'
        })
        current_search = self.client.get(self.search_url, {
            'q': 'Corrected answer',
            'content_type': 'knowledge'
        })

        self.assertEqual(old_search.data['count'], 0)
        self.assertEqual(current_search.data['count'], 1)
        result = current_search.data['results'][0]
        self.assertEqual(result['knowledge_id'], knowledge.pk)
        self.assertEqual(result['knowledge_version'], current.version_number)
        self.assertTrue(result['knowledge_corrected'])
        self.assertNotEqual(result['knowledge_version'], original.version_number)

    def test_ranking_is_relevance_first_then_recency_and_paginates(self):
        old = datetime(2020, 1, 1, tzinfo=datetime_timezone.utc)
        newer = datetime(2025, 1, 1, tzinfo=datetime_timezone.utc)
        newest = datetime(2026, 1, 1, tzinfo=datetime_timezone.utc)
        resource = self.create_resource(title='Python', description='A reference.')
        Resource.objects.filter(pk=resource.pk).update(create_date=old)
        exact_message = self.create_message(
            self.channel,
            self.member,
            'Python',
            created_at=old
        )
        older_phrase = self.create_message(
            self.channel,
            self.member,
            'Python helps build useful tools.',
            created_at=newer
        )
        newer_phrase = self.create_message(
            self.channel,
            self.member,
            'Python makes practical automation possible.',
            created_at=newest
        )

        first_page = self.client.get(self.search_url, {
            'q': 'Python',
            'page': 1,
            'page_size': 2
        })
        second_page = self.client.get(self.search_url, {
            'q': 'Python',
            'page': 2,
            'page_size': 2
        })

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.data['count'], 4)
        self.assertEqual(first_page.data['total_pages'], 2)
        self.assertEqual(
            [(hit['type'], hit['id']) for hit in first_page.data['results']],
            [('resource', str(resource.pk)), ('discussion', str(exact_message.pk))]
        )
        self.assertEqual(
            [hit['id'] for hit in second_page.data['results']],
            [str(newer_phrase.pk), str(older_phrase.pk)]
        )
        self.assertEqual(second_page.data['page'], 2)
        self.assertEqual(second_page.data['page_size'], 2)

    def test_date_range_filters_both_sources_and_rejects_invalid_ranges(self):
        target_date = datetime(2024, 3, 10, 12, tzinfo=datetime_timezone.utc)
        message = self.create_message(
            self.channel,
            self.member,
            'Python timezone search',
            created_at=target_date
        )
        resource = self.create_resource(title='Python timezone guide')
        Resource.objects.filter(pk=resource.pk).update(create_date=target_date)
        outside = self.create_message(
            self.channel,
            self.member,
            'Python timezone outside the date range',
            created_at=datetime(2024, 3, 12, 12, tzinfo=datetime_timezone.utc)
        )

        response = self.client.get(self.search_url, {
            'q': 'python timezone',
            'start_date': '2024-03-10',
            'end_date': '2024-03-10'
        })
        invalid_range = self.client.get(self.search_url, {
            'q': 'python',
            'start_date': '2024-03-11',
            'end_date': '2024-03-10'
        })
        invalid_date = self.client.get(self.search_url, {
            'q': 'python',
            'start_date': 'not-a-date'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {hit['id'] for hit in response.data['results']},
            {str(message.pk), str(resource.pk)}
        )
        self.assertNotIn(str(outside.pk), {
            hit['id'] for hit in response.data['results']
        })
        self.assertEqual(invalid_range.status_code, 400)
        self.assertEqual(invalid_date.status_code, 400)

    def test_empty_punctuation_only_and_oversized_queries_are_rejected(self):
        for params in (
            {'q': ''},
            {'q': '... !!!'},
            {'q': 'x' * 201},
            {'q': 'python', 'page_size': 51}
        ):
            with self.subTest(params=params):
                response = self.client.get(self.search_url, params)
                self.assertEqual(response.status_code, 400)

    def test_membership_revocation_blocks_search_and_source_navigation(self):
        message = self.create_message(
            self.channel,
            self.member,
            'Permission boundary search phrase.'
        )
        resource = self.create_resource(
            title='Permission boundary reference'
        )
        self.space.memberships.filter(user=self.member).delete()

        response = self.client.get(self.search_url, {'q': 'permission boundary'})
        message_response = self.client.get(
            f'/api/spaces/{self.space.pk}/channels/{self.channel.pk}/messages/'
        )
        resource_response = self.client.get(
            f'/api/spaces/{self.space.pk}/resources/{resource.pk}/'
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(message_response.status_code, 404)
        self.assertEqual(resource_response.status_code, 404)
        self.assertTrue(ChatSessionMessage.objects.filter(pk=message.pk).exists())

    def test_search_page_avoids_per_result_database_queries(self):
        self.create_message(
            self.channel,
            self.member,
            'Bounded query inspection search.'
        )
        self.create_resource(title='Bounded query inspection guide')

        with self.assertNumQueries(8):
            response = self.client.get(
                self.search_url,
                {'q': 'bounded query inspection'}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
