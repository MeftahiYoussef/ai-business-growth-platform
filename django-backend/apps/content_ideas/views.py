from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, Throttled
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
    AIValidationError,
)
from apps.ai.services import ContentIdeaValidationError, generate_content_ideas, generate_content_ideas_with_provider
from apps.trends.models import Trend
from common.utilities.access import get_owned_business
from common.utilities.ids import id_filter
from common.utilities.query import apply_search_sort

from .models import ContentIdea
from .serializers import ContentIdeaSerializer


class ContentIdeaGenerationError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Could not generate a diverse content idea batch. Please try again."
    default_code = "content_idea_generation_failed"


def _content_idea_ai_error_response(exc):
    if isinstance(exc, AIRateLimitError):
        return Response({"success": False, "message": str(exc)}, status=429)
    if isinstance(exc, AITimeoutError):
        return Response({"success": False, "message": str(exc)}, status=504)
    if isinstance(exc, AIConfigurationError):
        return Response({"success": False, "message": "AI provider is not configured"}, status=500)
    if isinstance(exc, AIValidationError):
        return Response({"success": False, "message": "AI provider returned invalid content"}, status=502)
    if isinstance(exc, AIProviderError):
        return Response({"success": False, "message": "AI provider request failed"}, status=502)
    raise exc


class ContentIdeasView(APIView):
    @property
    def paginator(self):
        from common.pagination.compat import PageNumberLimitPagination

        return PageNumberLimitPagination()

    def get(self, request):
        business = get_owned_business(request.user)
        qs = apply_search_sort(
            ContentIdea.objects.filter(business=business),
            request,
            ["title", "hook", "caption", "format", "status", "reason"],
            {"title": "title", "format": "format", "status": "status", "engagementPotentialScore": "engagement_potential_score", "trendMatchScore": "trend_match_score", "createdAt": "created_at"},
        )
        paginator = self.paginator
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ContentIdeaSerializer(page, many=True).data)


def _check_content_idea_limits(*, business, requested_count):
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = ContentIdea.objects.filter(business=business, created_at__gte=today_start).count()
    if today_count + requested_count > settings.CONTENT_IDEAS_MAX_BUSINESS_DAILY_ITEMS:
        raise Throttled(detail="Daily content idea generation quota exceeded")


class GenerateContentIdeasView(APIView):
    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        count = int(request.data.get("count") or 10)
        count = max(1, min(count, 25))
        _check_content_idea_limits(business=business, requested_count=count)
        trends = list(Trend.objects.filter(business=business).order_by("-created_at")[:5])
        existing_count = ContentIdea.objects.filter(business=business).count()
        try:
            generated = generate_content_ideas_with_provider(business, trends, count, offset=existing_count)
        except ContentIdeaValidationError:
            if not settings.CONTENT_IDEAS_DETERMINISTIC_FALLBACK_ENABLED:
                raise ContentIdeaGenerationError()
            generated = generate_content_ideas(business, trends, count, offset=existing_count)
        except (AIConfigurationError, AIProviderError, AIRateLimitError, AITimeoutError, AIValidationError) as exc:
            if not settings.CONTENT_IDEAS_DETERMINISTIC_FALLBACK_ENABLED:
                return _content_idea_ai_error_response(exc)
            generated = generate_content_ideas(business, trends, count, offset=existing_count)
        ideas = [ContentIdea.objects.create(**item) for item in generated]
        return Response({"success": True, "data": ContentIdeaSerializer(ideas, many=True).data}, status=status.HTTP_201_CREATED)


class SaveContentIdeaView(APIView):
    def put(self, request, idea_id):
        business = get_owned_business(request.user)
        idea = ContentIdea.objects.filter(id_filter(idea_id), business=business).first()
        if not idea:
            raise NotFound("Content idea not found")
        idea.status = ContentIdea.Status.SAVED
        idea.save(update_fields=["status"])
        return Response({"success": True, "data": ContentIdeaSerializer(idea).data})


class DeleteContentIdeaView(APIView):
    def delete(self, request, idea_id):
        business = get_owned_business(request.user)
        idea = ContentIdea.objects.filter(id_filter(idea_id), business=business).first()
        if not idea:
            raise NotFound("Content idea not found")
        idea.delete()
        return Response({"success": True, "data": {"id": idea_id}})
