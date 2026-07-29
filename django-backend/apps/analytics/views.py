from django.db.models import Sum
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.competitors.models import Competitor
from apps.content_planner.models import ContentDraft
from apps.integrations.models import SocialAccount, SocialAccountMetricSnapshot, SocialPost, SocialPostMetricSnapshot
from common.utilities.access import get_owned_business

from .models import Goal
from .serializers import GoalSerializer


class AnalyticsSummaryView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        account_metrics = SocialAccountMetricSnapshot.objects.filter(business=business)
        post_metrics = SocialPostMetricSnapshot.objects.filter(business=business)
        totals = post_metrics.aggregate(
            reach=Sum("reach"), impressions=Sum("impressions"), likes=Sum("likes"),
            comments=Sum("comments"), shares=Sum("shares"), saves=Sum("saves"),
            clicks=Sum("clicks"), videoViews=Sum("video_views"),
        )
        followers = account_metrics.order_by("-snapshot_date").aggregate(total=Sum("followers"))["total"] or 0
        engagement = sum(totals.get(key) or 0 for key in ["likes", "comments", "shares", "saves"])
        impressions = totals.get("impressions") or 0
        payload = {
            "totalFollowers": followers,
            "reach": totals.get("reach") or 0,
            "impressions": impressions,
            "engagement": engagement,
            "engagementRate": round((engagement / impressions) * 100, 2) if impressions else 0,
            "likes": totals.get("likes") or 0,
            "comments": totals.get("comments") or 0,
            "shares": totals.get("shares") or 0,
            "saves": totals.get("saves") or 0,
            "clicks": totals.get("clicks") or 0,
            "videoViews": totals.get("videoViews") or 0,
            "publishedPosts": SocialPost.objects.filter(business=business).count(),
            "scheduledPosts": ContentDraft.objects.filter(business=business, status=ContentDraft.Status.SCHEDULED).count(),
            "competitorsTracked": Competitor.objects.filter(business=business).count(),
            "byPlatform": list(SocialAccount.objects.filter(business=business).values("platform", "followers")),
        }
        return Response({"success": True, "data": payload})


class GoalView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        return Response({"success": True, "data": GoalSerializer(Goal.objects.filter(business=business), many=True).data})

    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        serializer = GoalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        goal = serializer.save(business=business)
        return Response({"success": True, "data": GoalSerializer(goal).data}, status=status.HTTP_201_CREATED)
