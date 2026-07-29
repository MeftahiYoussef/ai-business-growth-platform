from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services import generate_competitor_posts
from apps.competitor_posts.models import CompetitorPost
from apps.competitor_posts.serializers import CompetitorPostSerializer
from common.utilities.access import get_owned_business, get_owned_competitor
from common.utilities.query import apply_search_sort

from .models import Competitor
from .serializers import CompetitorSerializer

SORT_MAP = {
    "name": "name",
    "platform": "platform",
    "followers": "followers",
    "engagementRate": "engagement_rate",
    "postingFrequency": "posting_frequency",
    "status": "status",
    "createdAt": "created_at",
    "updatedAt": "updated_at",
}


class CompetitorListCreateView(APIView):
    def get(self, request):
        business = get_owned_business(request.user)
        qs = apply_search_sort(
            Competitor.objects.filter(business=business),
            request,
            ["name", "platform", "posting_frequency", "status"],
            SORT_MAP,
        )
        paginator = self.paginator
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(CompetitorSerializer(page, many=True).data)

    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        serializer = CompetitorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        competitor = serializer.save(business=business)
        return Response({"success": True, "data": CompetitorSerializer(competitor).data}, status=status.HTTP_201_CREATED)

    @property
    def paginator(self):
        from common.pagination.compat import PageNumberLimitPagination

        return PageNumberLimitPagination()


class CompetitorDetailView(APIView):
    def get(self, request, competitor_id):
        _, competitor = get_owned_competitor(request.user, competitor_id)
        return Response({"success": True, "data": CompetitorSerializer(competitor).data})

    def put(self, request, competitor_id):
        _, competitor = get_owned_competitor(request.user, competitor_id)
        serializer = CompetitorSerializer(competitor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": CompetitorSerializer(competitor).data})

    def delete(self, request, competitor_id):
        _, competitor = get_owned_competitor(request.user, competitor_id)
        response_id = competitor_id
        competitor.delete()
        return Response({"success": True, "data": {"id": response_id}})


class CompetitorPostsView(APIView):
    def get(self, request, competitor_id):
        business, competitor = get_owned_competitor(request.user, competitor_id)
        qs = apply_search_sort(
            CompetitorPost.objects.filter(business=business, competitor=competitor),
            request,
            ["caption", "hook", "format", "platform"],
            {"createdAt": "created_at", "publishedAt": "published_at", "engagementScore": "engagement_score", "format": "format", "platform": "platform"},
        )
        paginator = self.paginator
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(CompetitorPostSerializer(page, many=True).data)

    @property
    def paginator(self):
        from common.pagination.compat import PageNumberLimitPagination

        return PageNumberLimitPagination()


class CompetitorPostsGenerateView(APIView):
    def post(self, request, competitor_id):
        _, competitor = get_owned_competitor(request.user, competitor_id)
        count = int(request.data.get("count") or 6)
        count = max(1, min(count, 25))
        posts = [CompetitorPost.objects.create(**item) for item in generate_competitor_posts(competitor, count)]
        return Response({"success": True, "data": CompetitorPostSerializer(posts, many=True).data}, status=status.HTTP_201_CREATED)


class CompetitorComparisonView(APIView):
    def get(self, request):
        business = get_owned_business(request.user)
        competitors = Competitor.objects.filter(business=business).order_by("-engagement_rate")[:10]
        data = [
            {
                "_id": str(item.id),
                "name": item.name,
                "platform": item.platform,
                "followers": item.followers,
                "engagementRate": item.engagement_rate,
                "postingFrequency": item.posting_frequency,
                "strengths": ["Consistent cadence", "Clear hooks"],
                "weaknesses": ["Limited proof assets"] if item.engagement_rate < 3 else ["Repetitive formats"],
                "opportunities": ["Create sharper comparison content", "Answer audience objections"],
                "risks": ["Fast trend decay"],
            }
            for item in competitors
        ]
        return Response({"success": True, "data": data})
