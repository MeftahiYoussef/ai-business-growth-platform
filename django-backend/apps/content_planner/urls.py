from django.urls import path

from .views import CampaignView, DraftActionView, DraftCommentsView, DraftDetailView, DraftVersionsView, DraftView

urlpatterns = [
    path("campaigns", CampaignView.as_view()),
    path("drafts", DraftView.as_view()),
    path("drafts/<str:draft_id>", DraftDetailView.as_view()),
    path("drafts/<str:draft_id>/<str:action>", DraftActionView.as_view()),
    path("drafts/<str:draft_id>/versions", DraftVersionsView.as_view()),
    path("drafts/<str:draft_id>/comments", DraftCommentsView.as_view()),
]
