from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import APIClient

from chat.models import ChatSession
from community.models import Channel, Space, SpaceMembership
from community.permissions import MEMBER

from .models import (
    LearningEnrollment,
    LearningProgress,
    LearningLesson,
    LearningPathway
)


User = get_user_model()


class LearningPathwayAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='learner',
            password='TestLearner123!'
        )
        self.other = User.objects.create_user(
            username='other_learner',
            password='TestOtherLearner123!'
        )
        self.client = APIClient()

    def test_authenticated_learner_can_discover_seeded_pathway(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/learning/pathways/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['slug'], 'ai-awareness')
        self.assertEqual(response.data[0]['total_lessons'], 6)
        self.assertFalse(response.data[0]['enrolled'])

    def test_learner_can_enroll_complete_activity_and_read_progress(self):
        self.client.force_authenticate(user=self.user)
        enrolled = self.client.post('/api/learning/pathways/ai-awareness/enroll/')
        self.assertEqual(enrolled.status_code, 201)
        self.assertTrue(
            LearningEnrollment.objects.filter(
                user=self.user,
                pathway__slug='ai-awareness'
            ).exists()
        )
        lesson = LearningLesson.objects.filter(
            unit__pathway__slug='ai-awareness'
        ).first()
        completed = self.client.post(
            '/api/learning/lessons/%s/complete/' % lesson.id,
            {'response': 'I would define the task before choosing a tool.'},
            format='json'
        )
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.data['completed_lessons'], 1)
        self.assertEqual(completed.data['total_lessons'], 6)
        progress = self.client.get('/api/learning/me/progress/')
        self.assertEqual(progress.status_code, 200)
        self.assertEqual(progress.data[0]['completed_lessons'], 1)

    def test_completion_requires_enrollment_and_response(self):
        self.client.force_authenticate(user=self.user)
        lesson = LearningLesson.objects.filter(
            unit__pathway__slug='ai-awareness'
        ).first()
        not_enrolled = self.client.post(
            '/api/learning/lessons/%s/complete/' % lesson.id,
            {'response': 'Attempt'},
            format='json'
        )
        self.assertEqual(not_enrolled.status_code, 404)
        self.client.post('/api/learning/pathways/ai-awareness/enroll/')
        blank = self.client.post(
            '/api/learning/lessons/%s/complete/' % lesson.id,
            {'response': '  '},
            format='json'
        )
        self.assertEqual(blank.status_code, 400)

    def test_progress_is_private_to_the_authenticated_learner(self):
        self.client.force_authenticate(user=self.user)
        self.client.post('/api/learning/pathways/ai-awareness/enroll/')
        lesson = LearningLesson.objects.filter(
            unit__pathway__slug='ai-awareness'
        ).first()
        self.client.post(
            '/api/learning/lessons/%s/complete/' % lesson.id,
            {'response': 'My private reflection.'},
            format='json'
        )
        self.client.force_authenticate(user=self.other)
        detail = self.client.get('/api/learning/pathways/ai-awareness/')
        self.assertEqual(detail.status_code, 200)
        self.assertFalse(detail.data['enrolled'])
        self.assertIsNone(detail.data['units'][0]['lessons'][0]['response'])
        self.assertFalse(
            LearningProgress.objects.filter(user=self.other).exists()
        )


class LearningAuthoringAPITests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username='pathway_author',
            password='TestPathwayAuthor123!'
        )
        self.learner = User.objects.create_user(
            username='pathway_learner',
            password='TestPathwayLearner123!'
        )
        self.other = User.objects.create_user(
            username='pathway_other',
            password='TestPathwayOther123!'
        )
        self.client = APIClient()

    def create_draft(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.post(
            '/api/learning/manage/pathways/',
            {
                'slug': 'practical-pathway',
                'title': 'Practical Pathway',
                'description': 'A test pathway.',
                'outcome': 'Make a small, testable improvement.'
            },
            format='json'
        )
        self.assertEqual(response.status_code, 201)
        return LearningPathway.objects.get(slug='practical-pathway')

    def add_content(self, pathway):
        unit = self.client.post(
            '/api/learning/manage/pathways/%s/units/' % pathway.slug,
            {'title': 'First steps', 'description': 'Begin here.', 'position': 1},
            format='json'
        )
        self.assertEqual(unit.status_code, 201)
        lesson = self.client.post(
            '/api/learning/manage/units/%s/lessons/' % unit.data['id'],
            {
                'title': 'Try it',
                'objective': 'Make a useful observation.',
                'body': 'Read the prompt and try a small experiment.',
                'estimated_minutes': 5,
                'position': 1,
                'activity_prompt': 'What did you observe?'
            },
            format='json'
        )
        self.assertEqual(lesson.status_code, 201)
        return lesson.data['id']

    def test_author_can_create_edit_and_publish_but_other_learner_cannot_manage(self):
        pathway = self.create_draft()
        self.assertEqual(pathway.status, LearningPathway.Status.DRAFT)
        lesson_id = self.add_content(pathway)
        edited = self.client.patch(
            '/api/learning/manage/lessons/%s/' % lesson_id,
            {'activity_prompt': 'What changed after your experiment?'},
            format='json'
        )
        self.assertEqual(edited.status_code, 200)
        published = self.client.post(
            '/api/learning/manage/pathways/%s/publish/' % pathway.slug
        )
        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.data['status'], LearningPathway.Status.PUBLISHED)
        self.assertEqual(
            self.client.get('/api/learning/pathways/%s/' % pathway.slug).status_code,
            200
        )
        self.client.force_authenticate(user=self.other)
        denied = self.client.patch(
            '/api/learning/manage/pathways/%s/' % pathway.slug,
            {'title': 'Not yours'},
            format='json'
        )
        self.assertEqual(denied.status_code, 403)

    def test_publication_requires_complete_structure_and_archive_blocks_new_enrolment(self):
        pathway = self.create_draft()
        invalid = self.client.post(
            '/api/learning/manage/pathways/%s/publish/' % pathway.slug
        )
        self.assertEqual(invalid.status_code, 400)
        self.add_content(pathway)
        self.assertEqual(
            self.client.post('/api/learning/manage/pathways/%s/publish/' % pathway.slug).status_code,
            200
        )
        self.client.force_authenticate(user=self.learner)
        self.assertEqual(
            self.client.post('/api/learning/pathways/%s/enroll/' % pathway.slug).status_code,
            201
        )
        lesson = LearningLesson.objects.get(unit__pathway=pathway)
        self.client.post(
            '/api/learning/lessons/%s/complete/' % lesson.id,
            {'response': 'Completed before archive.'},
            format='json'
        )
        self.client.force_authenticate(user=self.author)
        archived = self.client.post(
            '/api/learning/manage/pathways/%s/archive/' % pathway.slug
        )
        self.assertEqual(archived.status_code, 200)
        self.client.force_authenticate(user=self.other)
        self.assertEqual(
            self.client.get('/api/learning/pathways/%s/' % pathway.slug).status_code,
            404
        )
        self.assertEqual(
            LearningProgress.objects.filter(user=self.learner, lesson=lesson).count(),
            1
        )

    def test_discussion_link_and_question_require_space_membership(self):
        pathway = self.create_draft()
        lesson_id = self.add_content(pathway)
        self.client.post('/api/learning/manage/pathways/%s/publish/' % pathway.slug)
        space = Space.objects.create(
            owner=self.author,
            name='Learning Questions',
            purpose='Discuss the pathway.'
        )
        SpaceMembership.objects.create(space=space, user=self.learner, role=MEMBER)
        conversation = ChatSession.objects.create(owner=self.author)
        channel = Channel.objects.create(
            space=space,
            conversation=conversation,
            name='questions',
            created_by=self.author
        )
        linked = self.client.post(
            '/api/learning/lessons/%s/discussions/' % lesson_id,
            {'space_id': space.id, 'channel_id': channel.id},
            format='json'
        )
        self.assertEqual(linked.status_code, 201)
        self.client.force_authenticate(user=self.learner)
        self.client.post('/api/learning/pathways/%s/enroll/' % pathway.slug)
        question = self.client.post(
            '/api/learning/lessons/%s/questions/' % lesson_id,
            {
                'space_id': space.id,
                'channel_id': channel.id,
                'message': 'Can someone discuss this activity?'
            },
            format='json'
        )
        self.assertEqual(question.status_code, 201)
        self.client.force_authenticate(user=self.other)
        denied = self.client.post(
            '/api/learning/lessons/%s/questions/' % lesson_id,
            {
                'space_id': space.id,
                'channel_id': channel.id,
                'message': 'I should not see this.'
            },
            format='json'
        )
        self.assertEqual(denied.status_code, 403)
