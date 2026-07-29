from django.urls import include, path
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.ai.views import ContentPlanCreateDraftsView, ContentPlanGenerateView
from apps.analyses.views import AnalysisView
from apps.businesses.views import BusinessCollectionView
from apps.competitors.views import CompetitorListCreateView
from apps.content_ideas.views import ContentIdeasView
from apps.feedback.views import FeedbackView
from apps.notifications.views import NotificationView
from apps.reports.views import ReportView
from apps.strategies.views import StrategyView
from apps.trends.views import TrendsView
from config import health


def schema_excluded(view_class):
    methods = {
        method: extend_schema(exclude=True)
        for method in getattr(view_class, "http_method_names", [])
        if hasattr(view_class, method)
    }
    return extend_schema_view(**methods)(view_class).as_view()


urlpatterns = [
    path("health", health.live),
    path("api/health/live/", health.live),
    path("api/health/ready/", health.ready),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/business", schema_excluded(BusinessCollectionView)),
    path("api/competitors", schema_excluded(CompetitorListCreateView)),
    path("api/trends", schema_excluded(TrendsView)),
    path("api/content-ideas", schema_excluded(ContentIdeasView)),
    path("api/strategy", schema_excluded(StrategyView)),
    path("api/analysis", schema_excluded(AnalysisView)),
    path("api/feedback", schema_excluded(FeedbackView)),
    path("api/reports", schema_excluded(ReportView)),
    path("api/notifications", schema_excluded(NotificationView)),
    path("api/ai/content-plans/generate", schema_excluded(ContentPlanGenerateView)),
    path("api/ai/content-plans/<str:generation_id>/create-drafts", schema_excluded(ContentPlanCreateDraftsView)),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/business/", include("apps.businesses.urls")),
    path("api/competitors/", include("apps.competitors.urls")),
    path("api/trends/", include("apps.trends.urls")),
    path("api/content-ideas/", include("apps.content_ideas.urls")),
    path("api/strategy/", include("apps.strategies.urls")),
    path("api/analysis/", include("apps.analyses.urls")),
    path("api/feedback/", include("apps.feedback.urls")),
    path("api/team/", include("apps.teams.urls")),
    path("api/integrations/", include("apps.integrations.urls")),
    path("api/planner/", include("apps.content_planner.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/ai/", include("apps.ai.urls")),
]
