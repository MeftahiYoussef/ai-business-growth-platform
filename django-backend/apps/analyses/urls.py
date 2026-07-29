from django.urls import path

from .views import AnalysisView, GenerateAnalysisView

urlpatterns = [
    path("", AnalysisView.as_view()),
    path("generate", GenerateAnalysisView.as_view()),
]
