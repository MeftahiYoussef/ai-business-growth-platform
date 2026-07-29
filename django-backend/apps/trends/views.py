from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services import generate_trends
from apps.competitor_posts.models import CompetitorPost
from common.utilities.access import get_owned_business
from common.utilities.query import apply_search_sort

from .models import Trend
from .serializers import TrendSerializer


class TrendsView(APIView):
    @property
    def paginator(self):
        from common.pagination.compat import PageNumberLimitPagination

        return PageNumberLimitPagination()

    def get(self, request):
        business = get_owned_business(request.user)
        qs = apply_search_sort(
            Trend.objects.filter(business=business).prefetch_related("source_posts"),
            request,
            ["topic", "format", "momentum_label", "explanation"],
            {"topic": "topic", "format": "format", "momentumLabel": "momentum_label", "trendScore": "trend_score", "growthRate": "growth_rate", "createdAt": "created_at"},
        )
        paginator = self.paginator
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(TrendSerializer(page, many=True).data)


class AnalyzeTrendsView(APIView):
    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        source_posts = list(CompetitorPost.objects.filter(business=business).order_by("-created_at")[:10])
        created = []
        for payload in generate_trends(business, source_posts):
            posts = payload.pop("source_posts")
            trend = Trend.objects.create(**payload)
            trend.source_posts.set(posts)
            created.append(trend)
        return Response({"success": True, "data": TrendSerializer(created, many=True).data}, status=status.HTTP_201_CREATED)
