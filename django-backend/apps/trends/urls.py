from django.urls import path

from .views import AnalyzeTrendsView, TrendsView

urlpatterns = [
    path("", TrendsView.as_view()),
    path("analyze", AnalyzeTrendsView.as_view()),
]
