from django.urls import path

from .views import (
    AIStudioActionView,
    AIStudioGenerateView,
    AIStudioHistoryView,
    AIStudioVersionsView,
    ContentPlanCreateDraftsView,
    ContentPlanGenerateView,
    ContentPlanQueueView,
    ContentPlanStatusView,
)

urlpatterns = [
    path("studio/generate", AIStudioGenerateView.as_view()),
    path("studio/history", AIStudioHistoryView.as_view()),
    path("studio/<str:generation_id>/action", AIStudioActionView.as_view()),
    path("studio/<str:generation_id>/versions", AIStudioVersionsView.as_view()),
    path("content-plans/generate/", ContentPlanGenerateView.as_view()),
    path("content-plans/queue/", ContentPlanQueueView.as_view()),
    path("content-plans/<str:generation_id>/status/", ContentPlanStatusView.as_view()),
    path("content-plans/<str:generation_id>/create-drafts/", ContentPlanCreateDraftsView.as_view()),
]
