import re
import string
from datetime import timedelta

from django.utils import timezone

FORMATS = ["Carousel", "Short video", "LinkedIn post", "Thread", "Case study"]
MOMENTUM_LABELS = ["Emerging", "Peaking", "Fading"]
STOPWORDS = {
    "a",
    "and",
    "are",
    "as",
    "for",
    "from",
    "how",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
    "your",
}


class ContentIdeaValidationError(ValueError):
    pass


def calculate_engagement_score(likes=0, comments=0, shares=0, views=0):
    if not views:
        return min(100, likes * 0.2 + comments * 1.5 + shares * 2)
    weighted = likes + comments * 4 + shares * 6
    return min(100, round((weighted / views) * 1000))


def calculate_trend_score(growth_rate=0, confidence=0.75, source_count=1):
    return min(100, round(growth_rate * 0.45 + confidence * 35 + source_count * 8))


def normalize_idea_text(value):
    collapsed = re.sub(r"\s+", " ", value or "").strip().lower()
    return collapsed.translate(str.maketrans("", "", string.punctuation))


def _meaningful_tokens(value):
    return {token for token in normalize_idea_text(value).split() if len(token) > 2 and token not in STOPWORDS}


def _similarity(left, right):
    left_tokens = _meaningful_tokens(left)
    right_tokens = _meaningful_tokens(right)
    if not left_tokens or not right_tokens:
        return 0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def validate_content_idea_batch(ideas, expected_count=None):
    if expected_count is not None and len(ideas) != expected_count:
        raise ContentIdeaValidationError("Content idea batch size does not match requested count")

    seen_titles = set()
    combined_texts = []
    for idea in ideas:
        title = idea.get("title", "")
        normalized_title = normalize_idea_text(title)
        if not normalized_title:
            raise ContentIdeaValidationError("Content idea title is required")
        if normalized_title in seen_titles:
            raise ContentIdeaValidationError("Duplicate content idea title detected")
        seen_titles.add(normalized_title)

        combined = " ".join([idea.get("title", ""), idea.get("hook", ""), idea.get("caption", "")])
        for previous in combined_texts:
            if _similarity(combined, previous) >= 0.78:
                raise ContentIdeaValidationError("Near-duplicate content idea detected")
        combined_texts.append(combined)

        if not idea.get("caption") or not idea.get("cta"):
            raise ContentIdeaValidationError("Content idea caption and CTA are required")
        if "competitors are testing" in normalize_idea_text(idea.get("hook", "")):
            raise ContentIdeaValidationError("Placeholder competitor hook detected")

    return ideas


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


def _clean_list(value):
    return [str(item).strip() for item in (value or []) if str(item).strip()]


def _context_value(value, fallback):
    return str(value or "").strip() or fallback


def _slug_hashtag(value):
    compact = re.sub(r"[^A-Za-z0-9]+", "", str(value).title())
    return f"#{compact[:28]}" if compact else "#BusinessGrowth"


def _profile_richness(business):
    fields = [
        business.industry,
        business.product_or_service,
        business.target_audience,
        business.brand_voice,
        business.posting_frequency,
        ", ".join(_clean_list(business.goals)),
        ", ".join(_clean_list(business.preferred_platforms)),
    ]
    return sum(1 for field in fields if str(field or "").strip())


def _topic_pool(business, trends):
    topics = [trend.topic for trend in trends if getattr(trend, "topic", "")]
    topics.extend([
        f"{business.industry} buying trigger",
        f"{business.product_or_service} proof point",
        f"{business.target_audience} objection",
        f"{business.posting_frequency or 'weekly'} planning rhythm",
        f"{business.brand_voice or 'clear'} brand voice",
    ])
    unique = []
    seen = set()
    for topic in topics:
        normalized = normalize_idea_text(topic)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(topic)
    return unique


IDEA_PATTERNS = [
    {
        "format": "Carousel",
        "title": "{product} proof checklist for {audience}",
        "hook": "A practical checklist that helps {audience} judge whether {product} is worth their time.",
        "caption": "Break down the top decision criteria, connect each point to {industry}, and end with one concrete next step.",
        "cta": "Save this checklist before your next planning session.",
    },
    {
        "format": "LinkedIn post",
        "title": "What {audience} should ask before choosing {product}",
        "hook": "Turn common buyer uncertainty into a clear set of questions for {audience}.",
        "caption": "Open with the risk of vague requirements, then show how {product} helps clarify the buying decision.",
        "cta": "Comment with the question your team is debating.",
    },
    {
        "format": "Short video",
        "title": "One {industry} mistake that weakens {product} adoption",
        "hook": "Show the mistake, the consequence, and the better behavior in under 45 seconds.",
        "caption": "Use a before-and-after structure tailored to {audience}, with a simple visual example.",
        "cta": "Share this with the person planning next week.",
    },
    {
        "format": "Thread",
        "title": "A five-step way for {audience} to evaluate {topic}",
        "hook": "Make {topic} concrete with a sequence your audience can apply immediately.",
        "caption": "Each step should explain what to check, why it matters, and how it relates to {product}.",
        "cta": "Bookmark this thread for your next review.",
    },
    {
        "format": "Case study",
        "title": "How {product} supports a {industry} planning decision",
        "hook": "Frame a realistic scenario, then show the decision path without inventing performance metrics.",
        "caption": "Use the business context, the audience pain, and a recommendation that stays evidence-based.",
        "cta": "Ask for the template if you want the planning version.",
    },
    {
        "format": "Carousel",
        "title": "{brand_voice} positioning angles for {audience}",
        "hook": "Translate the brand voice into specific content angles instead of generic slogans.",
        "caption": "Show three angles, when each fits, and how each supports {product} without exaggerating claims.",
        "cta": "Pick one angle to test this week.",
    },
    {
        "format": "LinkedIn post",
        "title": "The weekly content rhythm for {posting_frequency}",
        "hook": "Make the posting cadence useful by tying each post type to a clear purpose.",
        "caption": "Map the cadence to education, proof, objection handling, and conversion support for {audience}.",
        "cta": "Save this rhythm and adapt it to your calendar.",
    },
    {
        "format": "Short video",
        "title": "Explain {product} to {audience} in one example",
        "hook": "Use one specific example to make the offer easier to understand.",
        "caption": "Start with the audience pain, show the useful example, and close with a non-hype recommendation.",
        "cta": "Send this to someone refining the message.",
    },
    {
        "format": "Thread",
        "title": "{industry} content prompts based on {topic}",
        "hook": "Use the topic as a prompt source, not as an unsupported market claim.",
        "caption": "List prompts that help {audience} explain problems, tradeoffs, and buying criteria.",
        "cta": "Reply with the prompt you would use first.",
    },
    {
        "format": "Case study",
        "title": "A realistic objection {audience} has about {product}",
        "hook": "Address the objection directly and keep the recommendation practical.",
        "caption": "Describe the objection, what evidence would help, and which next step is reasonable for {industry}.",
        "cta": "Save this for your next sales enablement draft.",
    },
]


def generate_content_ideas(business, trends, count=10, offset=0):
    ideas = []
    topics = _topic_pool(business, trends)
    goals = _clean_list(business.goals)
    platforms = _clean_list(business.preferred_platforms)
    industry = _context_value(business.industry, "your market")
    product = _context_value(business.product_or_service, "your offer")
    audience = _context_value(business.target_audience, "your audience")
    brand_voice = _context_value(business.brand_voice, "clear").split(",")[0].strip()
    posting_frequency = _context_value(business.posting_frequency, "weekly publishing")
    richness = _profile_richness(business)

    for index in range(count):
        position = index + offset
        trend = trends[position % len(trends)] if trends else None
        topic = topics[(position + position // len(IDEA_PATTERNS)) % len(topics)]
        pattern = IDEA_PATTERNS[position % len(IDEA_PATTERNS)]
        context = {
            "industry": industry,
            "product": product,
            "audience": audience,
            "brand_voice": brand_voice,
            "posting_frequency": posting_frequency,
            "topic": topic,
        }
        goal_bonus = 4 if goals else 0
        platform_bonus = 3 if platforms else 0
        trend_bonus = 8 if trend else 0
        format_bonus = (index % len(FORMATS)) * 2
        engagement_score = min(95, 58 + richness * 3 + goal_bonus + platform_bonus + trend_bonus + format_bonus)
        trend_match_score = min(95, round(trend.trend_score if trend else 52 + richness * 4 + (index % 4) * 3))
        hashtags = [
            _slug_hashtag(industry),
            _slug_hashtag(product),
            _slug_hashtag(goals[index % len(goals)] if goals else topic),
        ]
        title = pattern["title"].format(**context)
        if normalize_idea_text(topic) not in normalize_idea_text(title):
            title = f"{title}: {topic}"
        ideas.append({
            "business": business,
            "title": title,
            "hook": pattern["hook"].format(**context),
            "caption": pattern["caption"].format(**context),
            "cta": pattern["cta"].format(**context),
            "hashtags": list(dict.fromkeys(hashtags)),
            "format": pattern["format"],
            "engagement_potential_score": engagement_score,
            "trend_match_score": trend_match_score,
            "reason": (
                f"Rule-based estimate from business profile, goal context, and "
                f"{'stored trend: ' + trend.topic if trend else 'profile topic: ' + topic}."
            ),
            "status": "draft",
        })
    validate_content_idea_batch(ideas, expected_count=count)
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
