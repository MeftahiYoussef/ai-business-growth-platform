from django.urls import path

from .views import AnalyticsSummaryView, GoalView

urlpatterns = [
    path("summary", AnalyticsSummaryView.as_view()),
    path("goals", GoalView.as_view()),
]
