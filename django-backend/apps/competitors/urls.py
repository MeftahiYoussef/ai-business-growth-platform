from django.urls import path

from .views import (
    CompetitorComparisonView,
    CompetitorDetailView,
    CompetitorListCreateView,
    CompetitorPostsGenerateView,
    CompetitorPostsView,
)

urlpatterns = [
    path("", CompetitorListCreateView.as_view()),
    path("compare", CompetitorComparisonView.as_view()),
    path("<str:competitor_id>", CompetitorDetailView.as_view()),
    path("<str:competitor_id>/posts", CompetitorPostsView.as_view()),
    path("<str:competitor_id>/posts/mock-generate", CompetitorPostsGenerateView.as_view()),
]
