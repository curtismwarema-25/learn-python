from django.db.models import Q
from rest_framework import serializers

from .models import (
    LearningActivity,
    LearningEnrollment,
    LearningLesson,
    LearningPathway,
    LearningProgress,
    LearningUnit
)
from community.permissions import get_space_role


class LearningActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningActivity
        fields = ('id', 'kind', 'prompt')


class LearningLessonSerializer(serializers.ModelSerializer):
    activity = LearningActivitySerializer(read_only=True)
    completed = serializers.SerializerMethodField()
    response = serializers.SerializerMethodField()
    discussions = serializers.SerializerMethodField()

    class Meta:
        model = LearningLesson
        fields = (
            'id', 'title', 'objective', 'body', 'estimated_minutes',
            'position', 'activity', 'completed', 'response'
            , 'discussions'
        )

    def get_completed(self, obj):
        progress = self.context.get('progress', {}).get(obj.pk)
        return progress is not None

    def get_response(self, obj):
        progress = self.context.get('progress', {}).get(obj.pk)
        return progress.response if progress else None

    def get_discussions(self, obj):
        request = self.context.get('request')
        if request is None:
            return []
        links = obj.discussion_links.select_related('space', 'channel', 'source_message').filter(
            Q(source_message__isnull=True) | Q(source_message__deleted_at__isnull=True)
        )
        visible = []
        for link in links:
            if get_space_role(link.space, request.user) is None:
                continue
            visible.append({
                'space_id': str(link.space_id),
                'space_name': link.space.name,
                'channel_id': str(link.channel_id),
                'channel_name': link.channel.name,
                'source_message_id': link.source_message_id
            })
        return visible


class LearningUnitSerializer(serializers.ModelSerializer):
    lessons = serializers.SerializerMethodField()

    class Meta:
        model = LearningUnit
        fields = ('id', 'title', 'description', 'position', 'lessons')

    def get_lessons(self, obj):
        return LearningLessonSerializer(
            obj.lessons.all(),
            many=True,
            context=self.context
        ).data


class LearningPathwaySerializer(serializers.ModelSerializer):
    units = LearningUnitSerializer(many=True, read_only=True)
    enrolled = serializers.SerializerMethodField()
    completed_lessons = serializers.SerializerMethodField()
    total_lessons = serializers.SerializerMethodField()

    class Meta:
        model = LearningPathway
        fields = (
            'slug', 'title', 'description', 'outcome', 'units',
            'enrolled', 'completed_lessons', 'total_lessons', 'status'
        )

    def get_enrolled(self, obj):
        return self.context.get('enrollment') is not None

    def get_total_lessons(self, obj):
        return sum(len(unit.lessons.all()) for unit in obj.units.all())

    def get_completed_lessons(self, obj):
        return len(self.context.get('progress', {}))


class LearningEnrollmentSerializer(serializers.ModelSerializer):
    pathway = serializers.SlugRelatedField(read_only=True, slug_field='slug')

    class Meta:
        model = LearningEnrollment
        fields = ('pathway', 'started_at', 'last_active_at')


class LearningCompletionSerializer(serializers.Serializer):
    response = serializers.CharField(max_length=2000, allow_blank=False)

    def validate_response(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('A response is required.')
        return value


class LearningPathwayWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPathway
        fields = ('slug', 'title', 'description', 'outcome')


class LearningUnitWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningUnit
        fields = ('id', 'title', 'description', 'position')
        read_only_fields = ('id',)


class LearningLessonWriteSerializer(serializers.ModelSerializer):
    activity_prompt = serializers.CharField(
        source='activity.prompt',
        max_length=1000,
        required=False,
        allow_blank=True
    )

    class Meta:
        model = LearningLesson
        fields = (
            'id', 'title', 'objective', 'body', 'estimated_minutes', 'position',
            'activity_prompt'
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        if self.instance is None and not attrs.get('activity', {}).get('prompt', '').strip():
            raise serializers.ValidationError({'activity_prompt': 'An activity prompt is required.'})
        if 'activity' in attrs:
            attrs['activity']['prompt'] = attrs['activity']['prompt'].strip()
        return attrs
