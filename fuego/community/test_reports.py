from django.test import TestCase
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from .models import MessageReport, Space, SpaceMembership
from .permissions import MEMBER
from .services import ensure_default_channel


User = get_user_model()


class MessageReportAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='report_owner', password='ReportOwner123!')
        self.member = User.objects.create_user(username='report_member', password='ReportMember123!')
        self.other = User.objects.create_user(username='report_other', password='ReportOther123!')
        self.space = Space.objects.create(owner=self.owner, name='Report Space', purpose='Review community safety.')
        self.channel = ensure_default_channel(self.space)
        SpaceMembership.objects.create(space=self.space, user=self.member, role=MEMBER)
        SpaceMembership.objects.create(space=self.space, user=self.other, role=MEMBER)
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)
        created = self.client.post(
            '/api/spaces/%s/channels/%s/messages/' % (self.space.id, self.channel.id),
            {'message': 'Please review this message.'}
        )
        self.assertEqual(created.status_code, 201)
        self.message_id = created.data['id']

    def report_url(self):
        return '/api/spaces/%s/channels/%s/messages/%s/reports/' % (
            self.space.id, self.channel.id, self.message_id
        )

    def test_member_can_report_once_and_manager_can_review(self):
        self.client.force_authenticate(user=self.member)
        created = self.client.post(self.report_url(), {'reason': 'This needs moderation.'})
        self.assertEqual(created.status_code, 201)
        duplicate = self.client.post(self.report_url(), {'reason': 'Duplicate report.'})
        self.assertEqual(duplicate.status_code, 400)

        self.client.force_authenticate(user=self.other)
        self.assertEqual(self.client.get(self.report_url()).status_code, 403)

        self.client.force_authenticate(user=self.owner)
        reports = self.client.get(self.report_url())
        self.assertEqual(reports.status_code, 200)
        self.assertEqual(len(reports.data), 1)
        report_id = reports.data[0]['id']
        reviewed = self.client.patch(
            self.report_url() + '%s/' % report_id,
            {'status': MessageReport.Status.ACTIONED, 'moderator_notes': 'Handled.'},
            format='json'
        )
        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(reviewed.data['status'], MessageReport.Status.ACTIONED)
