from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import (
    LearningActivity,
    LearningEnrollment,
    LearningLesson,
    LearningActivity,
    LearningPathway,
    LearningProgress,
    LearningUnit,
    LearningDiscussionLink
)
from .serializers import (
    LearningCompletionSerializer,
    LearningEnrollmentSerializer,
    LearningPathwaySerializer,
    LearningLessonWriteSerializer,
    LearningPathwayWriteSerializer,
    LearningUnitWriteSerializer
)
from community.models import Channel, Space
from community.permissions import get_space_role, MANAGER_ROLES
from community.services import channel_message_to_json, create_channel_message
from chat.models import ChatSessionMessage


def _pathway_queryset():
    return LearningPathway.objects.filter(
        published=True,
        status=LearningPathway.Status.PUBLISHED
    ).prefetch_related(
        'units__lessons__activity'
    )


def _pathway_context(pathway, user):
    enrollment = LearningEnrollment.objects.filter(
        pathway=pathway,
        user=user
    ).first()
    lesson_ids = LearningLesson.objects.filter(
        unit__pathway=pathway
    ).values_list('id', flat=True)
    progress = {
        item.lesson_id: item
        for item in LearningProgress.objects.filter(
            user=user,
            lesson_id__in=lesson_ids
        )
    }
    return {'enrollment': enrollment, 'progress': progress}


def _can_manage_pathway(pathway, user):
    return user.is_staff or pathway.created_by_id == user.pk


def _author_pathway_or_404(request, slug):
    pathway = get_object_or_404(
        LearningPathway.objects.prefetch_related('units__lessons__activity'),
        slug=slug
    )
    if not _can_manage_pathway(pathway, request.user):
        raise PermissionDenied('You cannot manage this pathway.')
    return pathway


def _lesson_or_404(request, lesson_id):
    lesson = get_object_or_404(
        LearningLesson.objects.select_related('unit__pathway'),
        pk=lesson_id
    )
    if not _can_manage_pathway(lesson.unit.pathway, request.user):
        raise PermissionDenied('You cannot manage this lesson.')
    if lesson.unit.pathway.status == LearningPathway.Status.ARCHIVED:
        raise ValidationError('Archived pathways cannot be edited.')
    return lesson


class PathwayListView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        pathways = _pathway_queryset()
        return Response([
            LearningPathwaySerializer(
                pathway,
                context={**_pathway_context(pathway, request.user), 'request': request}
            ).data
            for pathway in pathways
        ])


class PathwayDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, slug):
        pathway = get_object_or_404(_pathway_queryset(), slug=slug)
        return Response(
            LearningPathwaySerializer(
                pathway,
                context={**_pathway_context(pathway, request.user), 'request': request}
            ).data
        )


class PathwayEnrollmentView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, slug):
        pathway = get_object_or_404(LearningPathway, slug=slug, published=True)
        enrollment, created = LearningEnrollment.objects.get_or_create(
            pathway=pathway,
            user=request.user
        )
        return Response(
            LearningEnrollmentSerializer(enrollment).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class LessonCompletionView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, lesson_id):
        serializer = LearningCompletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson = get_object_or_404(
            LearningLesson.objects.select_related('unit__pathway'),
            pk=lesson_id,
            unit__pathway__published=True
        )
        pathway = lesson.unit.pathway
        enrollment = get_object_or_404(
            LearningEnrollment,
            pathway=pathway,
            user=request.user
        )
        with transaction.atomic():
            progress, created = LearningProgress.objects.update_or_create(
                user=request.user,
                lesson=lesson,
                defaults={'response': serializer.validated_data['response']}
            )
            enrollment.last_active_at = timezone.now()
            enrollment.save(update_fields=('last_active_at',))
        completed = LearningProgress.objects.filter(
            user=request.user,
            lesson__unit__pathway=pathway
        ).count()
        total = LearningLesson.objects.filter(unit__pathway=pathway).count()
        return Response({
            'lesson_id': lesson.pk,
            'completed': True,
            'created': created,
            'response': progress.response,
            'completed_lessons': completed,
            'total_lessons': total
        })


class MyLearningProgressView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        enrollments = LearningEnrollment.objects.filter(
            user=request.user
        ).select_related('pathway')
        return Response([
            {
                'pathway': enrollment.pathway.slug,
                'title': enrollment.pathway.title,
                'completed_lessons': LearningProgress.objects.filter(
                    user=request.user,
                    lesson__unit__pathway=enrollment.pathway
                ).count(),
                'total_lessons': LearningLesson.objects.filter(
                    unit__pathway=enrollment.pathway
                ).count(),
                'started_at': enrollment.started_at,
                'last_active_at': enrollment.last_active_at
            }
            for enrollment in enrollments
        ])


class AuthorPathwayListView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        pathways = (LearningPathway.objects.all() if request.user.is_staff else
                    LearningPathway.objects.filter(created_by=request.user)).prefetch_related(
                        'units__lessons__activity'
                    )
        return Response([
            LearningPathwaySerializer(
                pathway,
                context={**_pathway_context(pathway, request.user), 'request': request}
            ).data
            for pathway in pathways
        ])

    def post(self, request):
        serializer = LearningPathwayWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pathway = serializer.save(created_by=request.user, status=LearningPathway.Status.DRAFT, published=False)
        return Response(
            LearningPathwaySerializer(
                pathway,
                context={'request': request, 'progress': {}, 'enrollment': None}
            ).data,
            status=status.HTTP_201_CREATED
        )


class AuthorPathwayDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, slug):
        pathway = _author_pathway_or_404(request, slug)
        return Response(LearningPathwaySerializer(
            pathway,
            context={**_pathway_context(pathway, request.user), 'request': request}
        ).data)

    def patch(self, request, slug):
        pathway = _author_pathway_or_404(request, slug)
        if pathway.status == LearningPathway.Status.ARCHIVED:
            raise ValidationError('Archived pathways cannot be edited.')
        serializer = LearningPathwayWriteSerializer(
            pathway,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.get(request, slug)


class AuthorPathwayPublicationView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, slug, action):
        pathway = _author_pathway_or_404(request, slug)
        if action == 'archive':
            pathway.status = LearningPathway.Status.ARCHIVED
            pathway.published = False
            pathway.save(update_fields=('status', 'published', 'update_date'))
            return Response({'status': pathway.status})
        if action != 'publish':
            raise ValidationError('Unknown publication action.')
        lessons = LearningLesson.objects.filter(unit__pathway=pathway).prefetch_related('activity')
        if not pathway.title.strip() or not pathway.description.strip() or not pathway.outcome.strip():
            raise ValidationError('Pathway title, description, and outcome are required.')
        if not pathway.units.exists() or not lessons.exists():
            raise ValidationError('A pathway needs at least one unit and lesson before publishing.')
        if lessons.filter(activity__isnull=True).exists():
            raise ValidationError('Every lesson needs a practical activity.')
        if any(not lesson.activity.prompt.strip() for lesson in lessons):
            raise ValidationError('Every activity needs a prompt.')
        pathway.status = LearningPathway.Status.PUBLISHED
        pathway.published = True
        pathway.save(update_fields=('status', 'published', 'update_date'))
        return Response({'status': pathway.status})


class AuthorUnitListView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, slug):
        pathway = _author_pathway_or_404(request, slug)
        if pathway.status == LearningPathway.Status.ARCHIVED:
            raise ValidationError('Archived pathways cannot be edited.')
        serializer = LearningUnitWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        unit = serializer.save(pathway=pathway)
        return Response(LearningUnitWriteSerializer(unit).data, status=status.HTTP_201_CREATED)


class AuthorUnitDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request, unit_id):
        unit = get_object_or_404(LearningUnit.objects.select_related('pathway'), pk=unit_id)
        if not _can_manage_pathway(unit.pathway, request.user):
            raise PermissionDenied('You cannot manage this unit.')
        if unit.pathway.status == LearningPathway.Status.ARCHIVED:
            raise ValidationError('Archived pathways cannot be edited.')
        serializer = LearningUnitWriteSerializer(unit, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(LearningUnitWriteSerializer(serializer.save()).data)


class AuthorLessonListView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, unit_id):
        unit = get_object_or_404(LearningUnit.objects.select_related('pathway'), pk=unit_id)
        if not _can_manage_pathway(unit.pathway, request.user):
            raise PermissionDenied('You cannot manage this lesson.')
        if unit.pathway.status == LearningPathway.Status.ARCHIVED:
            raise ValidationError('Archived pathways cannot be edited.')
        serializer = LearningLessonWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        activity = data.pop('activity')
        with transaction.atomic():
            lesson = LearningLesson.objects.create(unit=unit, **data)
            LearningActivity.objects.create(lesson=lesson, prompt=activity['prompt'])
        return Response(LearningLessonWriteSerializer(lesson).data, status=status.HTTP_201_CREATED)


class AuthorLessonDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request, lesson_id):
        lesson = _lesson_or_404(request, lesson_id)
        serializer = LearningLessonWriteSerializer(lesson, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        activity = data.pop('activity', None)
        with transaction.atomic():
            lesson = serializer.update(lesson, data)
            if activity is not None:
                LearningActivity.objects.update_or_create(
                    lesson=lesson,
                    defaults={'prompt': activity['prompt']}
                )
        return Response(LearningLessonWriteSerializer(lesson).data)


def _link_payload(link):
    return {
        'id': link.pk,
        'space_id': str(link.space_id),
        'space_name': link.space.name,
        'channel_id': str(link.channel_id),
        'channel_name': link.channel.name,
        'source_message_id': link.source_message_id
    }


class LessonDiscussionLinkView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, lesson_id):
        lesson = get_object_or_404(
            LearningLesson.objects.select_related('unit__pathway'),
            pk=lesson_id,
            unit__pathway__published=True,
            unit__pathway__status=LearningPathway.Status.PUBLISHED
        )
        links = lesson.discussion_links.select_related('space', 'channel')
        return Response([
            _link_payload(link)
            for link in links
            if get_space_role(link.space, request.user) is not None
        ])

    def post(self, request, lesson_id):
        lesson = get_object_or_404(
            LearningLesson.objects.select_related('unit__pathway'),
            pk=lesson_id,
            unit__pathway__status=LearningPathway.Status.PUBLISHED
        )
        space = get_object_or_404(Space, pk=request.data.get('space_id'))
        channel = get_object_or_404(Channel, pk=request.data.get('channel_id'), space=space)
        if (
            get_space_role(space, request.user) not in MANAGER_ROLES
            and not _can_manage_pathway(lesson.unit.pathway, request.user)
        ):
            raise PermissionDenied('Only pathway authors or Space managers can link discussions.')
        source_message = None
        if request.data.get('source_message_id') is not None:
            source_message = get_object_or_404(
                ChatSessionMessage,
                pk=request.data['source_message_id'],
                chat_session=channel.conversation,
                deleted_at__isnull=True
            )
        link, _created = LearningDiscussionLink.objects.get_or_create(
            lesson=lesson,
            channel=channel,
            source_message=source_message,
            defaults={'space': space, 'created_by': request.user}
        )
        return Response(_link_payload(link), status=status.HTTP_201_CREATED if _created else status.HTTP_200_OK)


class LessonQuestionView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, lesson_id):
        lesson = get_object_or_404(
            LearningLesson.objects.select_related('unit__pathway'),
            pk=lesson_id,
            unit__pathway__published=True,
            unit__pathway__status=LearningPathway.Status.PUBLISHED
        )
        message = request.data.get('message', '').strip()
        if not message or len(message) > 2000:
            raise ValidationError('A question between 1 and 2,000 characters is required.')
        link = get_object_or_404(
            LearningDiscussionLink.objects.select_related('space', 'channel'),
            lesson=lesson,
            space_id=request.data.get('space_id'),
            channel_id=request.data.get('channel_id'),
            source_message__isnull=True
        )
        if get_space_role(link.space, request.user) is None:
            raise PermissionDenied('Join the Space before asking a question there.')
        if not LearningEnrollment.objects.filter(pathway=lesson.unit.pathway, user=request.user).exists():
            raise PermissionDenied('Enroll in the pathway before asking a lesson question.')
        with transaction.atomic():
            created = create_channel_message(link.channel, request.user, message, resources=[])
            discussion = LearningDiscussionLink.objects.create(
                lesson=lesson,
                space=link.space,
                channel=link.channel,
                source_message=created,
                created_by=request.user
            )
        return Response({
            'message': channel_message_to_json(created),
            'discussion': _link_payload(discussion)
        }, status=status.HTTP_201_CREATED)
