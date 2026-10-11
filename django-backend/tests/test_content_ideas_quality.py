from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.ai.services import (
    ContentIdeaValidationError,
    generate_content_ideas,
    normalize_idea_text,
    validate_content_idea_batch,
)
from apps.businesses.models import Business


def business(**overrides):
    values = {
        "industry": "B2B AI software",
        "product_or_service": "AI launch planning software",
        "target_audience": "SaaS founders",
        "brand_voice": "Clear, technical, pragmatic",
        "posting_frequency": "4 posts per week",
        "goals": ["lead generation", "education"],
        "preferred_platforms": ["LinkedIn", "YouTube"],
        "known_competitors": ["LaunchKit"],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def idea(**overrides):
    values = {
        "title": "Unique title",
        "hook": "A useful hook for a real audience.",
        "caption": "A meaningful caption that is not copied from another card.",
        "cta": "Save this.",
        "hashtags": ["#Growth"],
    }
    values.update(overrides)
    return values


class ContentIdeaQualityTests(TestCase):
    def test_duplicate_exact_titles_are_rejected(self):
        with self.assertRaises(ContentIdeaValidationError):
            validate_content_idea_batch([
                idea(title="Same title"),
                idea(title="Same title", cta="Different CTA"),
            ])

    def test_duplicate_titles_ignore_case_whitespace_and_punctuation(self):
        with self.assertRaises(ContentIdeaValidationError):
            validate_content_idea_batch([
                idea(title="The Founders trend your competitors are testing now"),
                idea(title="  the founders trend: your competitors are testing now!  "),
            ])

    def test_different_cta_only_does_not_make_duplicate_valid(self):
        with self.assertRaises(ContentIdeaValidationError):
            validate_content_idea_batch([
                idea(title="Buyer checklist", caption="Use the same buyer checklist."),
                idea(title="Buyer checklist", caption="Use the same buyer checklist.", cta="Comment for the template."),
            ])

    def test_unique_batch_is_accepted(self):
        batch = [
            idea(title="AI launch checklist", caption="Explain the launch planning decision."),
            idea(title="Founder proof post", caption="Show one proof point without inventing metrics."),
        ]
        self.assertEqual(validate_content_idea_batch(batch), batch)

    def test_generator_returns_unique_business_specific_titles(self):
        generated = generate_content_ideas(business(), [], count=10)
        titles = [item["title"] for item in generated]
        self.assertEqual(len({normalize_idea_text(title) for title in titles}), 10)
        self.assertTrue(any("AI launch planning software" in title for title in titles))
        self.assertFalse(any("competitors are testing now" in item["hook"] for item in generated))
        self.assertFalse(any("#contentops" in item["hashtags"] for item in generated))

    def test_generator_personalizes_different_businesses(self):
        software = generate_content_ideas(business(), [], count=5)
        bakery = generate_content_ideas(
            business(
                industry="Local bakery",
                product_or_service="sourdough bread and custom cakes",
                target_audience="neighborhood families",
                brand_voice="Warm, local, friendly",
                goals=["store visits"],
                preferred_platforms=["Instagram"],
            ),
            [],
            count=5,
        )

        software_text = " ".join(item["title"] + " " + item["caption"] for item in software)
        bakery_text = " ".join(item["title"] + " " + item["caption"] for item in bakery)
        self.assertIn("AI launch planning software", software_text)
        self.assertIn("sourdough bread and custom cakes", bakery_text)
        self.assertNotIn("sourdough bread", software_text)
        self.assertNotIn("AI launch planning software", bakery_text)

    def test_scores_are_deterministic_profile_estimates(self):
        first = generate_content_ideas(business(), [], count=3)
        second = generate_content_ideas(business(), [], count=3)
        self.assertEqual(
            [(item["engagement_potential_score"], item["trend_match_score"], item["reason"]) for item in first],
            [(item["engagement_potential_score"], item["trend_match_score"], item["reason"]) for item in second],
        )
        self.assertTrue(all("Rule-based estimate" in item["reason"] for item in first))

    def test_endpoint_retries_once_then_fails_safely_for_invalid_batches(self):
        user = get_user_model().objects.create_user("owner@example.com", "Password123!", full_name="Owner")
        owned_business = Business.objects.create(
            owner=user,
            name="Signal Co",
            industry="B2B AI software",
            country="United States",
            product_or_service="AI launch planning software",
            target_audience="SaaS founders",
        )
        client = APIClient()
        client.force_authenticate(user)

        with patch("apps.content_ideas.views.generate_content_ideas", side_effect=ContentIdeaValidationError("duplicate")) as generator:
            response = client.post("/api/content-ideas/generate", {"businessId": str(owned_business.id), "count": 3}, format="json")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(generator.call_count, 2)

    def test_endpoint_returns_unique_batch(self):
        user = get_user_model().objects.create_user("owner2@example.com", "Password123!", full_name="Owner")
        owned_business = Business.objects.create(
            owner=user,
            name="Signal Co",
            industry="B2B AI software",
            country="United States",
            product_or_service="AI launch planning software",
            target_audience="SaaS founders",
            goals=["lead generation"],
            preferred_platforms=["LinkedIn"],
        )
        client = APIClient()
        client.force_authenticate(user)

        response = client.post("/api/content-ideas/generate", {"businessId": str(owned_business.id), "count": 10}, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        titles = [item["title"] for item in response.data["data"]]
        self.assertEqual(len({normalize_idea_text(title) for title in titles}), 10)

    def test_endpoint_advances_diversity_across_multiple_runs(self):
        user = get_user_model().objects.create_user("owner3@example.com", "Password123!", full_name="Owner")
        owned_business = Business.objects.create(
            owner=user,
            name="Signal Co",
            industry="B2B AI software",
            country="United States",
            product_or_service="AI launch planning software",
            target_audience="SaaS founders",
            goals=["lead generation", "education"],
            preferred_platforms=["LinkedIn"],
        )
        client = APIClient()
        client.force_authenticate(user)

        batches = []
        all_titles = []
        for _ in range(5):
            response = client.post("/api/content-ideas/generate", {"businessId": str(owned_business.id), "count": 10}, format="json")
            self.assertEqual(response.status_code, 201, response.content)
            titles = [normalize_idea_text(item["title"]) for item in response.data["data"]]
            self.assertEqual(len(set(titles)), 10)
            batches.append(titles)
            all_titles.extend(titles)

        self.assertEqual(len({tuple(batch) for batch in batches}), 5)
        self.assertEqual(len(set(all_titles)), 50)
