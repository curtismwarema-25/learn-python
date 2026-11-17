"""URLs for the Community API."""

from django.urls import path

from . import views


app_name = 'community'

urlpatterns = [
    path('spaces/', views.SpaceDirectoryView.as_view(), name='directory'),
    path('spaces/mine/', views.MySpacesView.as_view(), name='mine'),
    path(
        'spaces/<uuid:space_id>/resources/',
        views.SpaceResourcesView.as_view(),
        name='resources'
    ),
    path(
        'spaces/<uuid:space_id>/resources/<uuid:resource_id>/',
        views.SpaceResourceDetailView.as_view(),
        name='resource-detail'
    ),
    path(
        'spaces/<uuid:space_id>/search/',
        views.SpaceSearchView.as_view(),
        name='search'
    ),
    path(
        'spaces/invites/join/',
        views.SpaceInviteJoinView.as_view(),
        name='invite-join'
    ),
    path(
        'spaces/<uuid:space_id>/channels/',
        views.SpaceChannelsView.as_view(),
        name='channels'
    ),
    path(
        'spaces/<uuid:space_id>/channels/<uuid:channel_id>/messages/',
        views.SpaceChannelMessagesView.as_view(),
        name='channel-messages'
    ),
    path(
        'spaces/<uuid:space_id>/channels/<uuid:channel_id>/',
        views.SpaceChannelDetailView.as_view(),
        name='channel-detail'
    ),
    path(
        'spaces/<uuid:space_id>/',
        views.SpaceDetailView.as_view(),
        name='detail'
    ),
    path(
        'spaces/<uuid:space_id>/members/',
        views.SpaceMembersView.as_view(),
        name='members'
    ),
    path(
        'spaces/<uuid:space_id>/members/<int:user_id>/',
        views.SpaceMemberDetailView.as_view(),
        name='member-detail'
    ),
    path(
        'spaces/<uuid:space_id>/leave/',
        views.LeaveSpaceView.as_view(),
        name='leave'
    ),
    path(
        'spaces/<uuid:space_id>/requests/',
        views.SpaceJoinRequestsView.as_view(),
        name='requests'
    ),
    path(
        'spaces/<uuid:space_id>/requests/<int:request_id>/approve/',
        views.SpaceJoinDecisionView.as_view(decision='approve'),
        name='request-approve'
    ),
    path(
        'spaces/<uuid:space_id>/requests/<int:request_id>/deny/',
        views.SpaceJoinDecisionView.as_view(decision='deny'),
        name='request-deny'
    ),
    path(
        'spaces/<uuid:space_id>/invite/',
        views.SpaceInviteView.as_view(),
        name='invite'
    ),
    path(
        'spaces/<uuid:space_id>/transfer/',
        views.TransferSpaceOwnershipView.as_view(),
        name='transfer'
    ),
]
