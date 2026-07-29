from datetime import timedelta

from django.utils import timezone

FORMATS = ["Carousel", "Short video", "LinkedIn post", "Thread", "Case study"]
MOMENTUM_LABELS = ["Emerging", "Peaking", "Fading"]


def calculate_engagement_score(likes=0, comments=0, shares=0, views=0):
    if not views:
        return min(100, likes * 0.2 + comments * 1.5 + shares * 2)
    weighted = likes + comments * 4 + shares * 6
    return min(100, round((weighted / views) * 1000))


def calculate_trend_score(growth_rate=0, confidence=0.75, source_count=1):
    return min(100, round(growth_rate * 0.45 + confidence * 35 + source_count * 8))


def generate_competitor_posts(competitor, count=6):
    # TODO: Replace with social media data provider APIs for live competitor post ingestion.
    posts = []
    for index in range(count):
        likes = 120 + index * 47
        comments = 18 + index * 6
        shares = 12 + index * 5
        views = 2400 + index * 800
        posts.append({
            "competitor": competitor,
            "business": competitor.business,
            "platform": competitor.platform,
            "post_url": f"{competitor.profile_url}/mock-post-{index + 1}" if competitor.profile_url else "",
            "caption": f"A practical breakdown of how {competitor.name} turns market signals into buyer-ready content.",
            "hashtags": ["#aigrowth", "#trendintelligence", "#contentstrategy"],
            "hook": "Most brands miss this signal before it peaks." if index % 2 == 0 else "Here is the content pattern competitors repeat every week.",
            "format": FORMATS[index % len(FORMATS)],
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "views": views,
            "engagement_score": calculate_engagement_score(likes, comments, shares, views),
            "published_at": timezone.now() - timedelta(days=index),
        })
    return posts


def generate_trends(business, source_posts):
    # TODO: Connect this to a real AI trend analysis API and social listening data.
    topics = [
        f"AI workflows for {business.industry}",
        f"{business.target_audience} pain-point teardowns",
        f"Founder-led proof for {business.product_or_service}",
    ]
    trends = []
    for index, topic in enumerate(topics):
        growth_rate = 38 + index * 14
        confidence = 0.72 + index * 0.06
        trends.append({
            "business": business,
            "topic": topic,
            "hashtags": ["#aitools", "#growthstrategy", "#markettrends"],
            "hooks": ["This trend is still early enough to own.", "Your competitors are already testing this angle."],
            "format": FORMATS[index % len(FORMATS)],
            "momentum_label": MOMENTUM_LABELS[index % len(MOMENTUM_LABELS)],
            "trend_score": calculate_trend_score(growth_rate, confidence, len(source_posts) or 1),
            "growth_rate": growth_rate,
            "confidence": confidence,
            "explanation": f"Mock analysis found repeated demand signals for {topic}.",
            "source_posts": source_posts[:5],
        })
    return trends


def generate_content_ideas(business, trends, count=10):
    # TODO: Replace with real LLM-powered content ideation.
    ideas = []
    for index in range(count):
        trend = trends[index % max(len(trends), 1)] if trends else None
        topic = trend.topic if trend else f"growth signal for {business.industry}"
        ideas.append({
            "business": business,
            "title": f"Post idea {index + 1}: {topic}",
            "hook": f"The {business.target_audience} trend your competitors are testing now",
            "caption": f"Show the signal, explain why it matters, and connect it to {business.product_or_service} with one practical example.",
            "cta": "Save this before your next planning session." if index % 2 == 0 else 'Comment "growth" for the checklist.',
            "hashtags": ["#aibusiness", "#contentops", "#trendstrategy"],
            "format": FORMATS[index % len(FORMATS)],
            "engagement_potential_score": 78 + (index % 5) * 4,
            "trend_match_score": trend.trend_score if trend else 82,
            "reason": f"Generated from mock trend signal: {topic}.",
            "status": "draft",
        })
    return ideas


def generate_strategy(business, trends):
    # TODO: Connect strategy generation to a real AI planning API.
    return {
        "business": business,
        "weekly_calendar": [
            {"day": "Monday", "format": "LinkedIn post", "topic": "Market signal"},
            {"day": "Tuesday", "format": "Carousel", "topic": trends[0].topic if trends else "AI workflow teardown"},
            {"day": "Wednesday", "format": "Short video", "topic": "Competitor lesson"},
            {"day": "Thursday", "format": "Thread", "topic": "Objection handling"},
            {"day": "Friday", "format": "Case study", "topic": "Customer proof"},
        ],
        "best_posting_times": ["Tuesday 09:00", "Thursday 11:30", "Sunday 18:00"],
        "recommended_hashtags": ["#aigrowth", "#founderbrand", "#contentstrategy"],
        "target_audience_recommendation": f"Prioritize {business.target_audience} with practical, proof-driven content.",
        "next_best_actions": [
            {"title": "Publish one AI workflow teardown", "reason": "Mock trend data shows high save potential.", "impact": "High", "difficulty": "Medium"},
            {"title": "Create competitor comparison content", "reason": "Competitor posts leave positioning gaps.", "impact": "High", "difficulty": "Medium"},
            {"title": "Move two posts to peak time windows", "reason": "Mock audience timing suggests better reach.", "impact": "Medium", "difficulty": "Low"},
        ],
    }


def generate_business_analysis(business, trends):
    # TODO: Replace mock SWOT generation with a real AI analysis workflow.
    return {
        "business": business,
        "strengths": ["Focused positioning", "Clear target audience", "High-value product category"],
        "weaknesses": ["Limited proof assets", "Inconsistent posting cadence", "Manual competitor tracking"],
        "opportunities": [trends[0].topic if trends else "AI workflow content", "Founder-led trust building", "Comparison and teardown formats"],
        "threats": ["Crowded AI tooling market", "Fast trend decay", "Competitors with larger audiences"],
        "growth_recommendations": [
            {"title": "Build a weekly teardown series", "signal": "Trend and competitor content overlap", "impact": "High"},
            {"title": "Package a practical lead magnet", "signal": "Audience responds to templates and checklists", "impact": "Medium"},
        ],
    }
