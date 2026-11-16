"""URLs for the chat app."""

from django.urls import path
from . import views

urlpatterns = [
    path('chats/', views.ChatSessionView.as_view()),
    path(
        'chats/<str:uri>/join/',
        views.ChatSessionJoinView.as_view()
    ),
    path('chats/<str:uri>/', views.ChatSessionView.as_view()),
    path(
        'chats/<str:uri>/messages/',
        views.ChatSessionMessageView.as_view()
    ),
]