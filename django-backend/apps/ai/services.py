import json
import re
import string
from datetime import timedelta

from django.utils import timezone

from apps.ai.exceptions import AIValidationError
from apps.ai.providers.factory import get_ai_provider

FORMATS = ["Carousel", "Short video", "LinkedIn post", "Thread", "Case study"]
MOMENTUM_LABELS = ["Emerging", "Peaking", "Fading"]
CONTENT_IDEA_PROMPT_VERSION = "content_ideas_groq_v1"
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


def content_idea_schema(count):
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "ideas": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string", "minLength": 1, "maxLength": 180},
                        "hook": {"type": "string", "minLength": 1, "maxLength": 360},
                        "caption": {"type": "string", "minLength": 1, "maxLength": 1200},
                        "cta": {"type": "string", "minLength": 1, "maxLength": 220},
                        "hashtags": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 8,
                            "items": {"type": "string", "minLength": 1, "maxLength": 80},
                        },
                        "format": {"type": "string", "enum": FORMATS},
                    },
                    "required": ["title", "hook", "caption", "cta", "hashtags", "format"],
                },
            }
        },
        "required": ["ideas"],
    }


def _business_context(business):
    return {
        "name": _context_value(getattr(business, "name", ""), "the business"),
        "industry": _context_value(business.industry, "the market"),
        "product_or_service": _context_value(business.product_or_service, "the offer"),
        "target_audience": _context_value(business.target_audience, "the audience"),
        "brand_voice": _context_value(business.brand_voice, "clear and helpful"),
        "posting_frequency": _context_value(business.posting_frequency, "weekly"),
        "goals": _clean_list(business.goals),
        "preferred_platforms": _clean_list(business.preferred_platforms),
        "known_competitors": _clean_list(getattr(business, "known_competitors", [])),
    }


def _trend_context(trends):
    return [
        {
            "topic": trend.topic,
            "momentum_label": trend.momentum_label,
            "trend_score": trend.trend_score,
            "growth_rate": trend.growth_rate,
            "confidence": trend.confidence,
        }
        for trend in trends
        if getattr(trend, "topic", "")
    ]


def build_content_idea_prompt(business, trends, count, offset=0, retry_feedback=""):
    context = {
        "business": _business_context(business),
        "available_trends": _trend_context(trends),
        "requested_count": count,
        "generation_offset": offset,
        "retry_feedback": retry_feedback,
    }
    system = (
        "You generate content idea cards for a business marketing app. "
        "Return JSON only. Generate distinct, useful ideas grounded in the supplied business context. "
        "Do not output engagement scores, trend scores, analytics, provider metadata, or publication decisions. "
        "Do not invent competitor performance, market metrics, or trend facts. "
        "Only mention a trend when it appears in available_trends. "
        "Every title must be unique, and ideas must not be CTA-only variations of each other."
    )
    user = (
        "Create content ideas using this JSON context. "
        "Use the business context heavily. If retry_feedback is present, correct those exact defects. "
        f"{json.dumps(context, ensure_ascii=True, sort_keys=True)}"
    )
    return {"system": system, "user": user, "schema": content_idea_schema(count), "prompt_version": CONTENT_IDEA_PROMPT_VERSION}


def _coerce_provider_idea(raw):
    if not isinstance(raw, dict):
        raise AIValidationError("AI provider returned an invalid content idea")
    hashtags = raw.get("hashtags")
    if not isinstance(hashtags, list):
        hashtags = []
    return {
        "title": str(raw.get("title", "")).strip(),
        "hook": str(raw.get("hook", "")).strip(),
        "caption": str(raw.get("caption", "")).strip(),
        "cta": str(raw.get("cta", "")).strip(),
        "hashtags": [str(hashtag).strip() for hashtag in hashtags if str(hashtag).strip()],
        "format": str(raw.get("format", "")).strip(),
    }


def _estimate_content_idea_scores(business, trends, idea, index):
    richness = _profile_richness(business)
    searchable = normalize_idea_text(" ".join([
        idea.get("title", ""),
        idea.get("hook", ""),
        idea.get("caption", ""),
        idea.get("cta", ""),
        " ".join(idea.get("hashtags", [])),
    ]))
    context_terms = [
        business.industry,
        business.product_or_service,
        business.target_audience,
        business.brand_voice,
        *(_clean_list(business.goals)),
        *(_clean_list(business.preferred_platforms)),
    ]
    context_hits = sum(1 for term in context_terms if term and normalize_idea_text(str(term)) in searchable)
    trend_hits = sum(1 for trend in trends if normalize_idea_text(getattr(trend, "topic", "")) in searchable)
    hashtag_count = min(4, len(idea.get("hashtags", [])))
    format_bonus = min(6, index * 2)
    engagement_estimate = min(95, 50 + richness * 3 + context_hits * 2 + hashtag_count * 2 + format_bonus)
    if trend_hits and trends:
        trend_score = max(float(getattr(trend, "trend_score", 0) or 0) for trend in trends if normalize_idea_text(getattr(trend, "topic", "")) in searchable)
        profile_fit_estimate = min(95, round(trend_score))
    else:
        profile_fit_estimate = min(95, 48 + richness * 4 + context_hits * 3)
    return round(engagement_estimate), round(profile_fit_estimate)


def _hydrate_content_ideas(business, trends, provider_ideas):
    ideas = []
    for index, raw_idea in enumerate(provider_ideas):
        idea = _coerce_provider_idea(raw_idea)
        engagement_score, profile_fit_score = _estimate_content_idea_scores(business, trends, idea, index)
        trend_basis = "stored trend evidence" if any(
            normalize_idea_text(getattr(trend, "topic", "")) in normalize_idea_text(idea["title"] + " " + idea["caption"])
            for trend in trends
        ) else "business profile context"
        ideas.append({
            "business": business,
            **idea,
            "engagement_potential_score": engagement_score,
            "trend_match_score": profile_fit_score,
            "reason": (
                "Generated by Groq; scores are deterministic estimates from "
                f"profile richness, context matches, hashtags, format, and {trend_basis}."
            ),
            "status": "draft",
        })
    validate_content_idea_batch(ideas, expected_count=len(provider_ideas))
    return ideas


def generate_content_ideas_with_provider(business, trends, count=10, offset=0):
    provider = get_ai_provider()
    retry_feedback = ""
    last_error: Exception | None = None
    for _attempt in range(2):
        prompt = build_content_idea_prompt(business, trends, count, offset=offset, retry_feedback=retry_feedback)
        result = provider.generate_structured_json(
            system=prompt["system"],
            user=prompt["user"],
            schema=prompt["schema"],
            prompt_version=prompt["prompt_version"],
        )
        if not isinstance(result.parsed_data, dict):
            raise AIValidationError("AI provider did not return an object")
        raw_ideas = result.parsed_data.get("ideas")
        if not isinstance(raw_ideas, list):
            raise AIValidationError("AI provider did not return content ideas")
        try:
            ideas = _hydrate_content_ideas(business, trends, raw_ideas)
            validate_content_idea_batch(ideas, expected_count=count)
            return ideas
        except ContentIdeaValidationError as exc:
            last_error = exc
            retry_feedback = str(exc)
    raise ContentIdeaValidationError(str(last_error or "Content idea validation failed"))


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
