from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services import generate_content_ideas
from apps.trends.models import Trend
from common.utilities.access import get_owned_business
from common.utilities.ids import id_filter
from common.utilities.query import apply_search_sort

from .models import ContentIdea
from .serializers import ContentIdeaSerializer


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
        ideas = [ContentIdea.objects.create(**item) for item in generate_content_ideas(business, trends, count)]
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
