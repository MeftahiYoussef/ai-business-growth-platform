from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.ai.services import (
    generate_business_analysis,
    generate_competitor_posts,
    generate_content_ideas,
    generate_strategy,
    generate_trends,
)
from apps.analyses.models import BusinessAnalysis
from apps.businesses.models import Business
from apps.competitor_posts.models import CompetitorPost
from apps.competitors.models import Competitor
from apps.content_ideas.models import ContentIdea
from apps.strategies.models import Strategy
from apps.trends.models import Trend


class Command(BaseCommand):
    help = "Create idempotent development seed data. Never run automatically in production."

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            email="demo@example.com",
            defaults={"full_name": "Demo Owner", "role": User.Role.OWNER},
        )
        if not user.has_usable_password():
            user.set_password("Password123!")
            user.save()

        business, _ = Business.objects.get_or_create(
            owner=user,
            name="Nova Studio",
            defaults={
                "industry": "Digital products",
                "country": "US",
                "product_or_service": "AI launch kits",
                "target_audience": "Founders",
                "goals": ["leads", "content velocity"],
                "known_competitors": ["GrowthPilot"],
                "brand_voice": "Sharp, useful, and premium",
            },
        )
        competitor, _ = Competitor.objects.get_or_create(
            business=business,
            name="GrowthPilot",
            platform="LinkedIn",
            defaults={"followers": 120000, "engagement_rate": 4.8, "posting_frequency": "9 posts/week"},
        )
        if not competitor.posts.exists():
            for payload in generate_competitor_posts(competitor, 4):
                CompetitorPost.objects.create(**payload)
        if not business.trends.exists():
            posts = list(business.competitor_posts.all()[:5])
            for payload in generate_trends(business, posts):
                source_posts = payload.pop("source_posts")
                trend = Trend.objects.create(**payload)
                trend.source_posts.set(source_posts)
        if not business.content_ideas.exists():
            for payload in generate_content_ideas(business, list(business.trends.all()[:3]), 5):
                ContentIdea.objects.create(**payload)
        if not business.strategies.exists():
            Strategy.objects.create(**generate_strategy(business, list(business.trends.all()[:3])))
        if not business.analyses.exists():
            BusinessAnalysis.objects.create(**generate_business_analysis(business, list(business.trends.all()[:3])))

        self.stdout.write(self.style.SUCCESS("Seed data ready: demo@example.com / Password123!"))
