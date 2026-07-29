import json
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.analyses.models import BusinessAnalysis
from apps.businesses.models import Business
from apps.competitor_posts.models import CompetitorPost
from apps.competitors.models import Competitor
from apps.content_ideas.models import ContentIdea
from apps.feedback.models import Feedback
from apps.strategies.models import Strategy
from apps.trends.models import Trend


def oid(value):
    return str(value) if value else None


def as_dt(value):
    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value)
    return timezone.now()


class Command(BaseCommand):
    help = "Migrate MongoDB collections into PostgreSQL with legacy_mongo_id references."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--database-name", default=None)

    def handle(self, *args, **options):
        try:
            from pymongo import MongoClient
        except ImportError as exc:
            raise SystemExit("pymongo is required for MongoDB migration") from exc

        dry_run = options["dry_run"]
        client = MongoClient(settings.MONGODB_URI)
        db = client[options["database_name"]] if options["database_name"] else client.get_default_database()
        report = {"created": {}, "skipped": {}, "failed": []}

        with transaction.atomic():
            self._users(db, report)
            self._businesses(db, report)
            self._competitors(db, report)
            self._posts(db, report)
            self._trends(db, report)
            self._ideas(db, report)
            self._strategies(db, report)
            self._analyses(db, report)
            self._feedback(db, report)
            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(json.dumps({"dryRun": dry_run, **report}, indent=2, default=str))

    def _mark(self, report, key, created):
        bucket = "created" if created else "skipped"
        report[bucket][key] = report[bucket].get(key, 0) + 1

    def _users(self, db, report):
        for doc in db.users.find({}):
            user, created = User.objects.get_or_create(
                legacy_mongo_id=oid(doc["_id"]),
                defaults={
                    "email": doc["email"],
                    "full_name": doc.get("fullName", ""),
                    "role": doc.get("role", "owner"),
                    "password": f"bcrypt${doc.get('passwordHash', '')}",
                    "created_at": as_dt(doc.get("createdAt")),
                    "updated_at": as_dt(doc.get("updatedAt")),
                },
            )
            self._mark(report, "users", created)

    def _businesses(self, db, report):
        for doc in db.businesses.find({}):
            owner = User.objects.filter(legacy_mongo_id=oid(doc.get("ownerId"))).first()
            if not owner:
                report["failed"].append({"collection": "businesses", "id": oid(doc["_id"]), "reason": "owner missing"})
                continue
            _, created = Business.objects.get_or_create(
                legacy_mongo_id=oid(doc["_id"]),
                defaults={
                    "owner": owner,
                    "name": doc.get("name", ""),
                    "industry": doc.get("industry", ""),
                    "country": doc.get("country", ""),
                    "product_or_service": doc.get("productOrService", ""),
                    "target_audience": doc.get("targetAudience", ""),
                    "goals": doc.get("goals", []),
                    "known_competitors": doc.get("knownCompetitors", []),
                    "brand_voice": doc.get("brandVoice", ""),
                    "created_at": as_dt(doc.get("createdAt")),
                    "updated_at": as_dt(doc.get("updatedAt")),
                },
            )
            self._mark(report, "businesses", created)

    def _competitors(self, db, report):
        for doc in db.competitors.find({}):
            business = Business.objects.filter(legacy_mongo_id=oid(doc.get("businessId"))).first()
            if not business:
                report["failed"].append({"collection": "competitors", "id": oid(doc["_id"]), "reason": "business missing"})
                continue
            _, created = Competitor.objects.get_or_create(
                legacy_mongo_id=oid(doc["_id"]),
                defaults={
                    "business": business, "name": doc.get("name", ""), "platform": doc.get("platform", ""),
                    "profile_url": doc.get("profileUrl", ""), "followers": doc.get("followers", 0),
                    "engagement_rate": doc.get("engagementRate", 0), "posting_frequency": doc.get("postingFrequency", "Unknown"),
                    "status": doc.get("status", "active"), "created_at": as_dt(doc.get("createdAt")),
                    "updated_at": as_dt(doc.get("updatedAt")),
                },
            )
            self._mark(report, "competitors", created)

    def _posts(self, db, report):
        for doc in db.competitor_posts.find({}):
            business = Business.objects.filter(legacy_mongo_id=oid(doc.get("businessId"))).first()
            competitor = Competitor.objects.filter(legacy_mongo_id=oid(doc.get("competitorId"))).first()
            if not business or not competitor:
                report["failed"].append({"collection": "competitor_posts", "id": oid(doc["_id"]), "reason": "relationship missing"})
                continue
            _, created = CompetitorPost.objects.get_or_create(legacy_mongo_id=oid(doc["_id"]), defaults={
                "business": business, "competitor": competitor, "platform": doc.get("platform", ""),
                "post_url": doc.get("postUrl", ""), "caption": doc.get("caption", ""), "hashtags": doc.get("hashtags", []),
                "hook": doc.get("hook", ""), "format": doc.get("format", ""), "likes": doc.get("likes", 0),
                "comments": doc.get("comments", 0), "shares": doc.get("shares", 0), "views": doc.get("views", 0),
                "engagement_score": doc.get("engagementScore", 0), "published_at": as_dt(doc.get("publishedAt")),
                "created_at": as_dt(doc.get("createdAt")),
            })
            self._mark(report, "competitor_posts", created)

    def _trends(self, db, report):
        for doc in db.trends.find({}):
            business = Business.objects.filter(legacy_mongo_id=oid(doc.get("businessId"))).first()
            if not business:
                report["failed"].append({"collection": "trends", "id": oid(doc["_id"]), "reason": "business missing"})
                continue
            trend, created = Trend.objects.get_or_create(legacy_mongo_id=oid(doc["_id"]), defaults={
                "business": business, "topic": doc.get("topic", ""), "hashtags": doc.get("hashtags", []),
                "hooks": doc.get("hooks", []), "format": doc.get("format", ""), "momentum_label": doc.get("momentumLabel", "Emerging"),
                "trend_score": doc.get("trendScore", 0), "growth_rate": doc.get("growthRate", 0),
                "confidence": doc.get("confidence", 0.75), "explanation": doc.get("explanation", ""),
                "created_at": as_dt(doc.get("createdAt")),
            })
            posts = CompetitorPost.objects.filter(legacy_mongo_id__in=[oid(item) for item in doc.get("sourcePosts", [])])
            trend.source_posts.set(posts)
            self._mark(report, "trends", created)

    def _ideas(self, db, report):
        for doc in db.content_ideas.find({}):
            business = Business.objects.filter(legacy_mongo_id=oid(doc.get("businessId"))).first()
            if not business:
                report["failed"].append({"collection": "content_ideas", "id": oid(doc["_id"]), "reason": "business missing"})
                continue
            _, created = ContentIdea.objects.get_or_create(legacy_mongo_id=oid(doc["_id"]), defaults={
                "business": business, "title": doc.get("title", ""), "hook": doc.get("hook", ""),
                "caption": doc.get("caption", ""), "cta": doc.get("cta", ""), "hashtags": doc.get("hashtags", []),
                "format": doc.get("format", ""), "engagement_potential_score": doc.get("engagementPotentialScore", 0),
                "trend_match_score": doc.get("trendMatchScore", 0), "reason": doc.get("reason", ""),
                "status": doc.get("status", "draft"), "created_at": as_dt(doc.get("createdAt")),
            })
            self._mark(report, "content_ideas", created)

    def _strategies(self, db, report):
        for doc in db.strategies.find({}):
            business = Business.objects.filter(legacy_mongo_id=oid(doc.get("businessId"))).first()
            if not business:
                continue
            _, created = Strategy.objects.get_or_create(legacy_mongo_id=oid(doc["_id"]), defaults={
                "business": business, "weekly_calendar": doc.get("weeklyCalendar", []),
                "best_posting_times": doc.get("bestPostingTimes", []), "recommended_hashtags": doc.get("recommendedHashtags", []),
                "target_audience_recommendation": doc.get("targetAudienceRecommendation", ""),
                "next_best_actions": doc.get("nextBestActions", []), "created_at": as_dt(doc.get("createdAt")),
            })
            self._mark(report, "strategies", created)

    def _analyses(self, db, report):
        for doc in db.business_analyses.find({}):
            business = Business.objects.filter(legacy_mongo_id=oid(doc.get("businessId"))).first()
            if not business:
                continue
            _, created = BusinessAnalysis.objects.get_or_create(legacy_mongo_id=oid(doc["_id"]), defaults={
                "business": business, "strengths": doc.get("strengths", []), "weaknesses": doc.get("weaknesses", []),
                "opportunities": doc.get("opportunities", []), "threats": doc.get("threats", []),
                "growth_recommendations": doc.get("growthRecommendations", []), "created_at": as_dt(doc.get("createdAt")),
            })
            self._mark(report, "business_analyses", created)

    def _feedback(self, db, report):
        for doc in db.feedback.find({}):
            business = Business.objects.filter(legacy_mongo_id=oid(doc.get("businessId"))).first()
            idea = ContentIdea.objects.filter(legacy_mongo_id=oid(doc.get("contentIdeaId"))).first()
            if not business or not idea:
                continue
            _, created = Feedback.objects.get_or_create(legacy_mongo_id=oid(doc["_id"]), defaults={
                "business": business, "content_idea": idea, "liked": bool(doc.get("liked")),
                "comment": doc.get("comment", ""), "created_at": as_dt(doc.get("createdAt")),
            })
            self._mark(report, "feedback", created)
