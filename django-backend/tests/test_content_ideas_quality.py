from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.ai.providers.base import AIProviderResult
from apps.ai.services import (
    ContentIdeaValidationError,
    generate_content_ideas,
    generate_content_ideas_with_provider,
    normalize_idea_text,
    validate_content_idea_batch,
)
from apps.businesses.models import Business
from apps.content_ideas.models import ContentIdea


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


def provider_payload(count=3, prefix="Provider"):
    topics = [
        "launch readiness checklist",
        "buyer objection teardown",
        "product proof story",
        "audience education sequence",
        "platform comparison angle",
    ]
    return {
        "ideas": [
            {
                "title": f"{prefix} {topics[index % len(topics)]}",
                "hook": f"Show how {topics[index % len(topics)]} helps the audience make a decision.",
                "caption": f"Build a practical post around {topics[index % len(topics)]} with distinct examples and next steps.",
                "cta": f"Save the {topics[index % len(topics)]} idea.",
                "hashtags": ["#Growth", f"#Idea{index}"],
                "format": "LinkedIn post",
            }
            for index in range(count)
        ]
    }


def fake_provider(parsed_data):
    provider = Mock()
    provider.name = "groq"
    provider.model = "openai/gpt-oss-20b"
    provider.generate_structured_json.return_value = AIProviderResult(
        content="{}",
        parsed_data=parsed_data,
        provider="groq",
        model="openai/gpt-oss-20b",
        input_tokens=10,
        output_tokens=20,
        request_id="content-ideas-request",
        finish_reason="stop",
    )
    return provider


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

    def test_provider_generator_uses_groq_structured_path_and_deterministic_scores(self):
        provider = fake_provider(provider_payload(count=3))
        with patch("apps.ai.services.get_ai_provider", return_value=provider):
            generated = generate_content_ideas_with_provider(business(), [], count=3)

        provider.generate_structured_json.assert_called_once()
        self.assertEqual(
            [item["title"] for item in generated],
            ["Provider launch readiness checklist", "Provider buyer objection teardown", "Provider product proof story"],
        )
        self.assertTrue(all(item["reason"].startswith("Generated by Groq; scores are deterministic estimates") for item in generated))
        self.assertTrue(all("business" in item for item in generated))

    def test_provider_generator_retries_once_for_duplicate_provider_batch(self):
        provider = fake_provider(provider_payload(count=2, prefix="Recovered"))
        provider.generate_structured_json.side_effect = [
            AIProviderResult(
                content="{}",
                parsed_data={"ideas": [
                    {
                        "title": "Duplicate",
                        "hook": "Same hook.",
                        "caption": "Same caption.",
                        "cta": "Save.",
                        "hashtags": ["#Growth"],
                        "format": "Carousel",
                    },
                    {
                        "title": "Duplicate",
                        "hook": "Same hook.",
                        "caption": "Same caption.",
                        "cta": "Comment.",
                        "hashtags": ["#Growth"],
                        "format": "Carousel",
                    },
                ]},
                provider="groq",
                model="openai/gpt-oss-20b",
            ),
            provider.generate_structured_json.return_value,
        ]

        with patch("apps.ai.services.get_ai_provider", return_value=provider):
            generated = generate_content_ideas_with_provider(business(), [], count=2)

        self.assertEqual(provider.generate_structured_json.call_count, 2)
        self.assertEqual(
            [item["title"] for item in generated],
            ["Recovered launch readiness checklist", "Recovered buyer objection teardown"],
        )

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

        with patch("apps.content_ideas.views.generate_content_ideas_with_provider", side_effect=ContentIdeaValidationError("duplicate")) as generator:
            response = client.post("/api/content-ideas/generate", {"businessId": str(owned_business.id), "count": 3}, format="json")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(generator.call_count, 1)

    @override_settings(CONTENT_IDEAS_DETERMINISTIC_FALLBACK_ENABLED=True)
    def test_endpoint_fallback_requires_explicit_setting(self):
        user = get_user_model().objects.create_user("owner-fallback@example.com", "Password123!", full_name="Owner")
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

        with patch("apps.content_ideas.views.generate_content_ideas_with_provider", side_effect=ContentIdeaValidationError("duplicate")):
            response = client.post("/api/content-ideas/generate", {"businessId": str(owned_business.id), "count": 3}, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(len(response.data["data"]), 3)

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

        generated = generate_content_ideas(owned_business, [], count=10)
        with patch("apps.content_ideas.views.generate_content_ideas_with_provider", return_value=generated) as provider_generator:
            response = client.post("/api/content-ideas/generate", {"businessId": str(owned_business.id), "count": 10}, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        provider_generator.assert_called_once()
        titles = [item["title"] for item in response.data["data"]]
        self.assertEqual(len({normalize_idea_text(title) for title in titles}), 10)

    @override_settings(CONTENT_IDEAS_MAX_BUSINESS_DAILY_ITEMS=3)
    def test_endpoint_enforces_business_daily_content_idea_quota_before_provider_call(self):
        user = get_user_model().objects.create_user("owner-quota@example.com", "Password123!", full_name="Owner")
        owned_business = Business.objects.create(
            owner=user,
            name="Signal Co",
            industry="B2B AI software",
            country="United States",
            product_or_service="AI launch planning software",
            target_audience="SaaS founders",
        )
        for index in range(3):
            ContentIdea.objects.create(
                business=owned_business,
                title=f"Existing idea {index}",
                hook=f"Existing hook {index}",
                caption="Existing caption",
                cta="Save this",
                hashtags=["#Growth"],
                format="LinkedIn post",
                engagement_potential_score=80,
                trend_match_score=75,
            )
        client = APIClient()
        client.force_authenticate(user)

        with patch("apps.content_ideas.views.generate_content_ideas_with_provider") as provider_generator:
            response = client.post("/api/content-ideas/generate", {"businessId": str(owned_business.id), "count": 1}, format="json")

        self.assertEqual(response.status_code, 429)
        self.assertIn("Daily content idea generation quota exceeded", str(response.data))
        provider_generator.assert_not_called()

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
            existing_count = len(all_titles)
            generated = generate_content_ideas(owned_business, [], count=10, offset=existing_count)
            with patch("apps.content_ideas.views.generate_content_ideas_with_provider", return_value=generated):
                response = client.post("/api/content-ideas/generate", {"businessId": str(owned_business.id), "count": 10}, format="json")
            self.assertEqual(response.status_code, 201, response.content)
            titles = [normalize_idea_text(item["title"]) for item in response.data["data"]]
            self.assertEqual(len(set(titles)), 10)
            batches.append(titles)
            all_titles.extend(titles)

        self.assertEqual(len({tuple(batch) for batch in batches}), 5)
        self.assertEqual(len(set(all_titles)), 50)
