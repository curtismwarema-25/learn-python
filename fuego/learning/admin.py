from django.contrib import admin

from .models import (
    LearningActivity,
    LearningEnrollment,
    LearningLesson,
    LearningPathway,
    LearningProgress,
    LearningUnit
)


admin.site.register((
    LearningPathway,
    LearningUnit,
    LearningLesson,
    LearningActivity,
    LearningEnrollment,
    LearningProgress
))
