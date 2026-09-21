from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view

from .views import AnalyzeTrendsView, TrendsView


@extend_schema_view(post=extend_schema(exclude=True))
class AnalyzeTrendsAliasView(AnalyzeTrendsView):
    pass


urlpatterns = [
    path("", TrendsView.as_view()),
    path("analyze", AnalyzeTrendsView.as_view()),
    path("analyze/", AnalyzeTrendsAliasView.as_view()),
]
