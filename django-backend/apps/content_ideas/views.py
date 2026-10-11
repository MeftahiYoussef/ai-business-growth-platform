from rest_framework import status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services import ContentIdeaValidationError, generate_content_ideas
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


class GenerateContentIdeasView(APIView):
    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        count = int(request.data.get("count") or 10)
        count = max(1, min(count, 25))
        trends = list(Trend.objects.filter(business=business).order_by("-created_at")[:5])
        existing_count = ContentIdea.objects.filter(business=business).count()
        generated = None
        for offset in (existing_count, existing_count + 1):
            try:
                generated = generate_content_ideas(business, trends, count, offset=offset)
                break
            except ContentIdeaValidationError:
                generated = None
        if generated is None:
            raise ContentIdeaGenerationError()
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
