from typing import Any

from django.db.models import Sum

from apps.competitor_posts.models import CompetitorPost
from apps.competitors.models import Competitor
from apps.content_planner.models import ContentDraft
from apps.integrations.models import SocialAccount, SocialAccountMetricSnapshot, SocialPostMetricSnapshot
from apps.trends.models import Trend


def _clip(value: str, limit: int = 500) -> str:
    value = value or ""
    return value[:limit]


def build_ai_context(*, business) -> dict[str, Any]:
    post_metrics = SocialPostMetricSnapshot.objects.filter(business=business)
    totals = post_metrics.aggregate(
        reach=Sum("reach"), impressions=Sum("impressions"), likes=Sum("likes"),
        comments=Sum("comments"), shares=Sum("shares"), saves=Sum("saves"), clicks=Sum("clicks"),
    )
    engagement = sum(totals.get(key) or 0 for key in ["likes", "comments", "shares", "saves"])
    impressions = totals.get("impressions") or 0
    analytics = {
        "source": "application_calculated_metrics",
        "reach": totals.get("reach") or 0,
        "impressions": impressions,
        "engagement": engagement,
        "engagement_rate": round((engagement / impressions) * 100, 2) if impressions else 0,
        "clicks": totals.get("clicks") or 0,
        "scheduled_posts": ContentDraft.objects.filter(business=business, status=ContentDraft.Status.SCHEDULED).count(),
    }
    followers = SocialAccountMetricSnapshot.objects.filter(business=business).order_by("-snapshot_date").aggregate(total=Sum("followers"))["total"] or 0
    analytics["followers"] = followers
    return {
        "business": {
            "name": business.name,
            "industry": business.industry,
            "country": business.country,
            "product_or_service": business.product_or_service,
            "target_audience": business.target_audience,
            "goals": business.goals[:8] if isinstance(business.goals, list) else [],
            "known_competitors": business.known_competitors[:8] if isinstance(business.known_competitors, list) else [],
            "brand_voice": business.brand_voice,
            "preferred_language": "English",
            "brand_restrictions": "Unavailable",
            "example_content": "Unavailable",
        },
        "preferred_platforms": list(SocialAccount.objects.filter(business=business).values_list("platform", flat=True).distinct()[:8]),
        "analytics": analytics,
        "trends": [
            {
                "topic": trend.topic,
                "hashtags": trend.hashtags[:8] if isinstance(trend.hashtags, list) else [],
                "hooks": trend.hooks[:4] if isinstance(trend.hooks, list) else [],
                "format": trend.format,
                "momentum_label": trend.momentum_label,
                "trend_score": trend.trend_score,
                "growth_rate": trend.growth_rate,
                "confidence": trend.confidence,
                "explanation": _clip(trend.explanation, 350),
            }
            for trend in Trend.objects.filter(business=business).order_by("-created_at")[:8]
        ],
        "competitors": [
            {
                "name": competitor.name,
                "platform": competitor.platform,
                "followers": competitor.followers,
                "engagement_rate": competitor.engagement_rate,
                "posting_frequency": competitor.posting_frequency,
            }
            for competitor in Competitor.objects.filter(business=business).order_by("-created_at")[:8]
        ],
        "competitor_posts": [
            {
                "competitor": post.competitor.name,
                "platform": post.platform,
                "hook": _clip(post.hook, 220),
                "caption": _clip(post.caption, 360),
                "hashtags": post.hashtags[:8] if isinstance(post.hashtags, list) else [],
                "format": post.format,
                "engagement_score": post.engagement_score,
            }
            for post in CompetitorPost.objects.filter(business=business).select_related("competitor").order_by("-published_at")[:12]
        ],
    }
