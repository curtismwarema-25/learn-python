from django.urls import path

from . import views


app_name = 'learning'

urlpatterns = [
    path('pathways/', views.PathwayListView.as_view(), name='pathway-list'),
    path('pathways/<slug:slug>/', views.PathwayDetailView.as_view(), name='pathway-detail'),
    path('pathways/<slug:slug>/enroll/', views.PathwayEnrollmentView.as_view(), name='pathway-enroll'),
    path('lessons/<int:lesson_id>/complete/', views.LessonCompletionView.as_view(), name='lesson-complete'),
    path('me/progress/', views.MyLearningProgressView.as_view(), name='my-progress'),
    path('manage/pathways/', views.AuthorPathwayListView.as_view(), name='author-pathways'),
    path('manage/pathways/<slug:slug>/', views.AuthorPathwayDetailView.as_view(), name='author-pathway'),
    path('manage/pathways/<slug:slug>/units/', views.AuthorUnitListView.as_view(), name='author-units'),
    path('manage/pathways/<slug:slug>/<str:action>/', views.AuthorPathwayPublicationView.as_view(), name='author-publication'),
    path('manage/units/<int:unit_id>/', views.AuthorUnitDetailView.as_view(), name='author-unit'),
    path('manage/units/<int:unit_id>/lessons/', views.AuthorLessonListView.as_view(), name='author-lessons'),
    path('manage/lessons/<int:lesson_id>/', views.AuthorLessonDetailView.as_view(), name='author-lesson'),
    path('lessons/<int:lesson_id>/discussions/', views.LessonDiscussionLinkView.as_view(), name='lesson-discussions'),
    path('lessons/<int:lesson_id>/questions/', views.LessonQuestionView.as_view(), name='lesson-questions'),
]
