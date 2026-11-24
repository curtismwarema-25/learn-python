from django.conf import settings
from django.db import models


class LearningPathway(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'

    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=160)
    description = models.TextField(max_length=2000)
    outcome = models.CharField(max_length=500)
    published = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='created_learning_pathways',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('title', 'id')


class LearningUnit(models.Model):
    pathway = models.ForeignKey(
        LearningPathway,
        related_name='units',
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=160)
    description = models.TextField(max_length=1000, blank=True)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ('position', 'id')
        constraints = [
            models.UniqueConstraint(
                fields=('pathway', 'position'),
                name='uniq_learning_unit_position'
            )
        ]


class LearningLesson(models.Model):
    unit = models.ForeignKey(
        LearningUnit,
        related_name='lessons',
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=160)
    objective = models.CharField(max_length=500)
    body = models.TextField(max_length=10000)
    estimated_minutes = models.PositiveIntegerField(default=10)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ('position', 'id')
        constraints = [
            models.UniqueConstraint(
                fields=('unit', 'position'),
                name='uniq_learning_lesson_position'
            )
        ]


class LearningActivity(models.Model):
    class Kind(models.TextChoices):
        SHORT_RESPONSE = 'short_response', 'Short response'

    lesson = models.OneToOneField(
        LearningLesson,
        related_name='activity',
        on_delete=models.CASCADE
    )
    prompt = models.TextField(max_length=1000)
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.SHORT_RESPONSE
    )


class LearningEnrollment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='learning_enrollments',
        on_delete=models.CASCADE
    )
    pathway = models.ForeignKey(
        LearningPathway,
        related_name='enrollments',
        on_delete=models.CASCADE
    )
    started_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'pathway'),
                name='uniq_learning_enrollment'
            )
        ]


class LearningProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='learning_progress',
        on_delete=models.CASCADE
    )
    lesson = models.ForeignKey(
        LearningLesson,
        related_name='progress_records',
        on_delete=models.CASCADE
    )
    response = models.TextField(max_length=2000)
    completed_at = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'lesson'),
                name='uniq_learning_progress_lesson'
            )
        ]


class LearningDiscussionLink(models.Model):
    """A permission-checked link from a lesson to Space discussion context."""

    lesson = models.ForeignKey(
        LearningLesson,
        related_name='discussion_links',
        on_delete=models.CASCADE
    )
    space = models.ForeignKey(
        'community.Space',
        related_name='learning_discussion_links',
        on_delete=models.PROTECT
    )
    channel = models.ForeignKey(
        'community.Channel',
        related_name='learning_discussion_links',
        on_delete=models.PROTECT
    )
    source_message = models.ForeignKey(
        'chat.ChatSessionMessage',
        related_name='learning_discussion_links',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='created_learning_discussion_links',
        on_delete=models.PROTECT
    )
    create_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('create_date', 'id')
        constraints = [
            models.UniqueConstraint(
                fields=('lesson', 'channel', 'source_message'),
                name='uniq_learning_discussion_link'
            )
        ]
