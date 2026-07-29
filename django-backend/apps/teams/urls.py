from django.urls import path

from .views import ActivityView, TeamInvitationRespondView, TeamInviteView, TeamMemberDetailView, TeamView

urlpatterns = [
    path("", TeamView.as_view()),
    path("invite", TeamInviteView.as_view()),
    path("invitations/<uuid:token>/respond", TeamInvitationRespondView.as_view()),
    path("members/<str:member_id>", TeamMemberDetailView.as_view()),
    path("activity", ActivityView.as_view()),
]
