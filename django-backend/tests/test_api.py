import json
import threading
import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from django.contrib.auth import get_user_model
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from groq import APIError as GroqAPIError
from groq import APITimeoutError as GroqAPITimeoutError
from groq import BadRequestError as GroqBadRequestError
from groq import RateLimitError as GroqRateLimitError
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.ai.content_plan_service import (
    create_drafts_from_plan,
    run_queued_content_plan_generation,
    submit_weekly_content_plan_job,
)
from apps.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
    AIValidationError,
)
from apps.ai.models import AIContentGeneration
from apps.ai.providers.base import AIProviderResult
from apps.ai.providers.factory import get_ai_provider
from apps.ai.providers.groq_provider import GroqProvider
from apps.ai.services import generate_content_ideas
from apps.ai.tasks import generate_content_plan_task
from apps.ai.validators import validate_content_plan
from apps.businesses.models import Business
from apps.content_planner.models import ContentDraft, ContentVersion


def valid_content_plan():
    return {
        "summary": "A focused weekly plan.",
        "primary_goal": "engagement",
        "target_audience": "Founders",
        "items": [
            {
                "day_number": day,
                "title": f"Day {day} post",
                "platform": "linkedin",
                "content_type": "linkedin_post",
                "objective": "engagement",
                "topic": f"Topic {day}",
                "hook": f"Hook {day}",
                "caption": f"Caption {day}",
                "call_to_action": "Save this",
                "hashtags": ["#growth"],
                "visual_brief": "Simple visual",
                "recommended_time": "18:00",
                "source_context": ["test"],
                "risk_flags": [],
                "requires_human_review": True,
            }
            for day in range(1, 8)
        ],
    }


def groq_response(content, *, response_id="groq-request-1", model="openai/gpt-oss-20b", finish_reason="stop"):
    return SimpleNamespace(
        id=response_id,
        model=model,
        choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish_reason)],
        usage=SimpleNamespace(prompt_tokens=111, completion_tokens=222),
    )


def fake_groq_provider(result=None):
    provider = Mock(name="groq", model="openai/gpt-oss-20b")
    provider.name = "groq"
    provider.model = "openai/gpt-oss-20b"
    provider.generate_social_content.return_value = {
        "hook": "Founders are paying attention to this shift.",
        "caption": "Use one clear market signal and connect it to the offer.",
        "cta": "Save this.",
        "hashtags": ["#growth"],
        "alternatives": [],
        "imagePrompt": "Clean SaaS social graphic.",
    }
    provider.generate_structured_json.return_value = result or AIProviderResult(
        content="",
        parsed_data=valid_content_plan(),
        provider="groq",
        model="openai/gpt-oss-20b",
        input_tokens=111,
        output_tokens=222,
        request_id="groq-request-1",
        finish_reason="stop",
    )
    return provider


class ApiFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def register(self, email="owner@example.com"):
        response = self.client.post(
            "/api/auth/register",
            {"fullName": "Owner User", "email": email, "password": "Password123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        token = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return response.data

    def create_business(self):
        response = self.client.post(
            "/api/business/",
            {
                "name": "Nova Studio",
                "industry": "SaaS",
                "country": "US",
                "productOrService": "AI launch kits",
                "targetAudience": "Founders",
                "goals": ["leads"],
                "knownCompetitors": ["GrowthPilot"],
                "brandVoice": "Sharp",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.data["data"]

    def test_full_business_flow(self):
        auth = self.register()
        self.assertTrue(auth["success"])
        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)

        business = self.create_business()
        competitor = self.client.post(
            "/api/competitors/",
            {"businessId": business["_id"], "name": "GrowthPilot", "platform": "LinkedIn"},
            format="json",
        )
        self.assertEqual(competitor.status_code, 201, competitor.content)
        competitor_id = competitor.data["data"]["_id"]

        posts = self.client.post(f"/api/competitors/{competitor_id}/posts/mock-generate", {"count": 2}, format="json")
        self.assertEqual(posts.status_code, 201, posts.content)
        self.assertEqual(len(posts.data["data"]), 2)

        trends = self.client.post("/api/trends/analyze", {"businessId": business["_id"]}, format="json")
        self.assertEqual(trends.status_code, 201, trends.content)
        owned_business = Business.objects.get(id=business["_id"])
        with patch("apps.content_ideas.views.generate_content_ideas_with_provider", return_value=generate_content_ideas(owned_business, [], count=2)):
            ideas = self.client.post("/api/content-ideas/generate", {"businessId": business["_id"], "count": 2}, format="json")
        self.assertEqual(ideas.status_code, 201, ideas.content)
        strategy = self.client.post("/api/strategy/generate", {"businessId": business["_id"]}, format="json")
        self.assertEqual(strategy.status_code, 201, strategy.content)
        analysis = self.client.post("/api/analysis/generate", {"businessId": business["_id"]}, format="json")
        self.assertEqual(analysis.status_code, 201, analysis.content)
        feedback = self.client.post(
            "/api/feedback/",
            {"businessId": business["_id"], "contentIdeaId": ideas.data["data"][0]["_id"], "liked": True},
            format="json",
        )
        self.assertEqual(feedback.status_code, 201, feedback.content)

    def test_protected_endpoint_requires_auth(self):
        response = self.client.get("/api/business/me")
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])

    def test_health_endpoints_are_minimal_and_database_ready(self):
        live = self.client.get("/api/health/live/")
        self.assertEqual(live.status_code, 200)
        self.assertEqual(live.json(), {"status": "ok"})

        ready = self.client.get("/api/health/ready/")
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["status"], "ok")
        self.assertEqual(ready.json()["database"], "ok")

        with patch("config.health.connection.cursor", side_effect=RuntimeError("database unavailable")):
            unavailable = self.client.get("/api/health/ready/")
        self.assertEqual(unavailable.status_code, 503)
        self.assertEqual(unavailable.json(), {"status": "error", "database": "error"})

    @override_settings(AI_ASYNC_CONTENT_PLAN_ENABLED=True, CELERY_TASK_ALWAYS_EAGER=False)
    def test_readiness_checks_redis_when_async_generation_is_enabled(self):
        redis_client = Mock()
        redis_client.ping.return_value = True
        with patch("config.health.Redis.from_url", return_value=redis_client):
            response = self.client.get("/api/health/ready/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok", "redis": "ok"})

        with patch("config.health.Redis.from_url", side_effect=RuntimeError("redis unavailable")):
            unavailable = self.client.get("/api/health/ready/")
        self.assertEqual(unavailable.status_code, 503)
        self.assertEqual(unavailable.json(), {"status": "error", "database": "ok", "redis": "error"})

    def test_request_id_header_is_returned_without_auth_logging_surface(self):
        response = self.client.get("/api/health/live/", HTTP_X_REQUEST_ID="staging-smoke-request")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "staging-smoke-request")

    def test_cross_user_resource_access_is_denied(self):
        self.register("one@example.com")
        business = self.create_business()
        self.client.credentials()
        self.register("two@example.com")
        response = self.client.post(
            "/api/competitors/",
            {"businessId": business["_id"], "name": "Other", "platform": "LinkedIn"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_search_sort_and_pagination(self):
        self.register("page@example.com")
        business = self.create_business()
        for name in ["Zulu", "Alpha", "Beta"]:
            self.client.post(
                "/api/competitors/",
                {"businessId": business["_id"], "name": name, "platform": "LinkedIn"},
                format="json",
            )
        response = self.client.get("/api/competitors/?search=a&sortBy=name&sortOrder=asc&page=1&limit=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["pagination"]["limit"], 2)
        self.assertLessEqual(len(response.data["items"]), 2)

    def test_phase_one_social_ai_calendar_reports_flow(self):
        self.register("phase1@example.com")
        business = self.create_business()
        business_id = business["_id"]

        connection = self.client.post(
            "/api/integrations/connections",
            {"businessId": business_id, "provider": "sandbox"},
            format="json",
        )
        self.assertEqual(connection.status_code, 201, connection.content)
        connection_id = connection.data["data"]["_id"]
        sync = self.client.post(f"/api/integrations/connections/{connection_id}/sync", {}, format="json")
        self.assertEqual(sync.status_code, 200, sync.content)

        analytics = self.client.get("/api/analytics/summary")
        self.assertEqual(analytics.status_code, 200, analytics.content)
        self.assertGreaterEqual(analytics.data["data"]["totalFollowers"], 0)

        with patch("apps.ai.views.get_ai_provider", return_value=fake_groq_provider()):
            generated = self.client.post(
                "/api/ai/studio/generate",
                {"businessId": business_id, "objective": "Generate leads", "platform": "LinkedIn"},
                format="json",
            )
        self.assertEqual(generated.status_code, 201, generated.content)
        self.assertEqual(generated.data["data"]["provider"], "groq")

        draft = self.client.post(
            "/api/planner/drafts",
            {"businessId": business_id, "title": "Launch post", "caption": "Ready", "platform": "LinkedIn"},
            format="json",
        )
        self.assertEqual(draft.status_code, 201, draft.content)
        draft_id = draft.data["data"]["_id"]
        self.assertEqual(self.client.post(f"/api/planner/drafts/{draft_id}/request-review", {}, format="json").status_code, 200)
        self.assertEqual(self.client.post(f"/api/planner/drafts/{draft_id}/approve", {}, format="json").status_code, 200)
        scheduled = self.client.post(
            f"/api/planner/drafts/{draft_id}/schedule",
            {"scheduledAt": "2026-07-20T09:00:00Z"},
            format="json",
        )
        self.assertEqual(scheduled.status_code, 200, scheduled.content)

        report = self.client.post("/api/reports/", {"businessId": business_id}, format="json")
        self.assertEqual(report.status_code, 201, report.content)
        notifications = self.client.get("/api/notifications/")
        self.assertEqual(notifications.status_code, 200)
        self.assertGreaterEqual(len(notifications.data["data"]), 1)
        notification_id = notifications.data["data"][0]["_id"]
        slashless_read = self.client.post(f"/api/notifications/{notification_id}/read", {}, format="json")
        self.assertEqual(slashless_read.status_code, 200, slashless_read.content)
        slash_read = self.client.post(f"/api/notifications/{notification_id}/read/", {}, format="json")
        self.assertEqual(slash_read.status_code, 200, slash_read.content)
        self.assertIsNotNone(slash_read.data["data"]["readAt"])

    def test_viewer_cannot_approve_content(self):
        self.register("owner2@example.com")
        business = self.create_business()
        invite = self.client.post(
            "/api/team/invite",
            {"businessId": business["_id"], "email": "viewer@example.com", "role": "viewer"},
            format="json",
        )
        self.assertEqual(invite.status_code, 201, invite.content)
        token = invite.data["data"]["token"]
        self.client.credentials()
        self.register("viewer@example.com")
        self.assertEqual(self.client.post(f"/api/team/invitations/{token}/respond", {"accept": True}, format="json").status_code, 200)
        draft = self.client.post(
            "/api/planner/drafts",
            {"businessId": business["_id"], "title": "Viewer draft", "caption": "x", "platform": "LinkedIn"},
            format="json",
        )
        self.assertEqual(draft.status_code, 403)

    def test_content_plan_generation_and_draft_conversion(self):
        self.register("plan@example.com")
        business = self.create_business()
        with patch("apps.ai.content_plan_service.get_ai_provider", return_value=fake_groq_provider()):
            response = self.client.post(
                "/api/ai/content-plans/generate/",
                {
                    "business_id": business["_id"],
                    "platforms": ["instagram", "linkedin"],
                    "start_date": "2026-08-03",
                    "goal": "increase engagement",
                    "additional_instructions": "Focus on educational content.",
                },
                format="json",
            )
        self.assertEqual(response.status_code, 201, response.content)

        with patch("apps.ai.content_plan_service.get_ai_provider", return_value=fake_groq_provider()):
            slashless = self.client.post(
                "/api/ai/content-plans/generate",
                {
                    "business_id": business["_id"],
                    "platforms": ["instagram", "linkedin"],
                    "start_date": "2026-08-03",
                    "goal": "increase engagement",
                    "additional_instructions": "Focus on educational content.",
                },
                format="json",
            )
        self.assertEqual(slashless.status_code, 201, slashless.content)
        self.assertEqual(len(slashless.data["plan"]["items"]), 7)

        self.assertEqual(response.data["provider"], "groq")
        self.assertEqual(response.data["status"], "completed")
        self.assertEqual(len(response.data["plan"]["items"]), 7)
        self.assertEqual([item["day_number"] for item in response.data["plan"]["items"]], list(range(1, 8)))
        self.assertTrue(all(item["requires_human_review"] for item in response.data["plan"]["items"]))
        generation_id = response.data["id"]
        record = AIContentGeneration.objects.get(id=generation_id)
        self.assertEqual(record.status, AIContentGeneration.Status.COMPLETED)
        self.assertEqual(record.usage["input_tokens"], 111)
        self.assertEqual(record.usage["output_tokens"], 222)
        self.assertEqual(record.structured_output["items"][0]["caption"], "Caption 1")
        self.assertEqual(record.generated_content, record.structured_output)

        drafts = self.client.post(
            f"/api/ai/content-plans/{generation_id}/create-drafts/",
            {"item_day_numbers": [1, 2]},
            format="json",
        )
        self.assertEqual(drafts.status_code, 201, drafts.content)
        self.assertEqual(len(drafts.data["data"]), 2)
        self.assertEqual({item["status"] for item in drafts.data["data"]}, {"draft"})
        self.assertEqual({item["approvalStatus"] for item in drafts.data["data"]}, {"draft"})
        self.assertEqual({item["scheduledAt"] for item in drafts.data["data"]}, {None})
        self.assertEqual(
            set(ContentDraft.objects.filter(source_ai_generation_id=generation_id).values_list("source_plan_day", flat=True)),
            {1, 2},
        )

        duplicate = self.client.post(
            f"/api/ai/content-plans/{generation_id}/create-drafts/",
            {"item_day_numbers": [1, 2]},
            format="json",
        )
        self.assertEqual(duplicate.status_code, 201, duplicate.content)
        self.assertEqual(len(duplicate.data["data"]), 0)
        duplicate_slashless = self.client.post(
            f"/api/ai/content-plans/{generation_id}/create-drafts",
            {"item_day_numbers": [1, 2]},
            format="json",
        )
        self.assertEqual(duplicate_slashless.status_code, 201, duplicate_slashless.content)
        self.assertEqual(len(duplicate_slashless.data["data"]), 0)
        self.assertEqual(ContentDraft.objects.filter(source_ai_generation_id=generation_id).count(), 2)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ContentDraft.objects.create(
                    business_id=record.business_id,
                    title="Duplicate day",
                    caption="Duplicate",
                    platform="linkedin",
                    content_type="linkedin_post",
                    created_by=record.user,
                    source_ai_generation=record,
                    source_plan_day=1,
                )

    def test_content_plan_validation_rejects_bad_platform_and_item_count(self):
        self.register("invalid-plan@example.com")
        business = self.create_business()
        response = self.client.post(
            "/api/ai/content-plans/generate/",
            {"business_id": business["_id"], "platforms": ["myspace"], "start_date": "2026-08-03"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        with self.assertRaises(ValidationError):
            validate_content_plan({"summary": "x", "primary_goal": "awareness", "target_audience": "x", "items": []})
        duplicate_day_plan = valid_content_plan()
        duplicate_day_plan["items"][1]["day_number"] = 1
        with self.assertRaises(ValidationError):
            validate_content_plan(duplicate_day_plan)
        no_review_plan = valid_content_plan()
        no_review_plan["items"][0]["requires_human_review"] = False
        with self.assertRaises(ValidationError):
            validate_content_plan(no_review_plan)

    def test_content_plan_cross_business_and_unauthenticated_access(self):
        self.register("plan-owner@example.com")
        business = self.create_business()
        self.client.credentials()
        unauthenticated = self.client.post(
            "/api/ai/content-plans/generate/",
            {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
            format="json",
        )
        self.assertEqual(unauthenticated.status_code, 401)
        self.register("plan-other@example.com")
        denied = self.client.post(
            "/api/ai/content-plans/generate/",
            {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
            format="json",
        )
        self.assertEqual(denied.status_code, 404)

    @override_settings(AI_MAX_USER_DAILY_REQUESTS=0)
    def test_content_plan_usage_limit_returns_429(self):
        self.register("quota@example.com")
        business = self.create_business()
        response = self.client.post(
            "/api/ai/content-plans/generate/",
            {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
            format="json",
        )
        self.assertEqual(response.status_code, 429)

    @override_settings(AI_MAX_BUSINESS_MONTHLY_REQUESTS=0)
    def test_content_plan_monthly_business_quota_returns_429(self):
        self.register("business-quota@example.com")
        business = self.create_business()
        response = self.client.post(
            "/api/ai/content-plans/generate/",
            {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
            format="json",
        )
        self.assertEqual(response.status_code, 429)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_async_content_plan_queue_status_and_idempotency(self):
        self.register("async-plan@example.com")
        business = self.create_business()
        with patch("apps.ai.content_plan_service.get_ai_provider", return_value=fake_groq_provider()):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    "/api/ai/content-plans/queue/",
                    {
                        "business_id": business["_id"],
                        "platforms": ["instagram", "linkedin"],
                        "start_date": "2026-08-03",
                        "goal": "increase engagement",
                    },
                    format="json",
                    HTTP_IDEMPOTENCY_KEY="weekly-plan-1",
                )
        self.assertEqual(response.status_code, 202, response.content)
        generation_id = response.data["generation_id"]
        record = AIContentGeneration.objects.get(id=generation_id)
        self.assertEqual(record.status, AIContentGeneration.Status.COMPLETED)
        self.assertEqual(record.attempt_count, 1)
        self.assertEqual(len(record.structured_output["items"]), 7)
        self.assertEqual(record.usage["input_tokens"], 111)
        self.assertTrue(record.queued_at)
        self.assertTrue(record.started_at)
        self.assertTrue(record.completed_at)

        status_response = self.client.get(f"/api/ai/content-plans/{generation_id}/status/")
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data["status"], "completed")
        self.assertTrue(status_response.data["result_available"])
        self.assertEqual(len(status_response.data["plan"]["items"]), 7)

        with patch("apps.ai.content_plan_service.get_ai_provider", return_value=fake_groq_provider()):
            duplicate = self.client.post(
                "/api/ai/content-plans/queue/",
                {
                    "business_id": business["_id"],
                    "platforms": ["instagram", "linkedin"],
                    "start_date": "2026-08-03",
                    "goal": "increase engagement",
                },
                format="json",
                HTTP_IDEMPOTENCY_KEY="weekly-plan-1",
            )
        self.assertEqual(duplicate.status_code, 202, duplicate.content)
        self.assertEqual(duplicate.data["generation_id"], generation_id)
        self.assertEqual(AIContentGeneration.objects.filter(feature_name="weekly_content_plan").count(), 1)

        conflict = self.client.post(
            "/api/ai/content-plans/queue/",
            {
                "business_id": business["_id"],
                "platforms": ["linkedin"],
                "start_date": "2026-08-04",
                "goal": "increase engagement",
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="weekly-plan-1",
        )
        self.assertEqual(conflict.status_code, 409)

    @override_settings(AI_ASYNC_CONTENT_PLAN_ENABLED=False, CELERY_TASK_ALWAYS_EAGER=False)
    def test_async_content_plan_queue_requires_explicit_enablement(self):
        self.register("async-disabled@example.com")
        business = self.create_business()
        response = self.client.post(
            "/api/ai/content-plans/queue/",
            {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
            format="json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["message"], "Asynchronous AI generation is not enabled")

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_async_content_plan_rejects_invalid_idempotency_key_format(self):
        self.register("async-bad-key@example.com")
        business = self.create_business()
        response = self.client.post(
            "/api/ai/content-plans/queue/",
            {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="bad key with spaces",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("idempotency_key", response.data["details"])

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_async_content_plan_failure_status_is_sanitized(self):
        self.register("async-fail-plan@example.com")
        business = self.create_business()
        with patch("apps.ai.content_plan_service.get_ai_provider") as provider_factory:
            provider = fake_groq_provider()
            provider.generate_structured_json.side_effect = AIValidationError("raw invalid provider body")
            provider_factory.return_value = provider
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    "/api/ai/content-plans/queue/",
                    {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
                    format="json",
                    HTTP_IDEMPOTENCY_KEY="weekly-plan-fail",
                )
        self.assertEqual(response.status_code, 202, response.content)
        generation_id = response.data["generation_id"]
        status_response = self.client.get(f"/api/ai/content-plans/{generation_id}/status/")
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data["status"], "failed")
        self.assertEqual(status_response.data["error"]["message"], "Content plan generation failed")
        self.assertNotIn("raw invalid", str(status_response.data))

    def test_async_status_is_business_isolated(self):
        self.register("async-owner@example.com")
        business = self.create_business()
        generation = AIContentGeneration.objects.create(
            business_id=business["_id"],
            user=get_user_model().objects.get(email="async-owner@example.com"),
            feature_name="weekly_content_plan",
            objective="engagement",
            platform="linkedin",
            status=AIContentGeneration.Status.QUEUED,
        )
        self.client.credentials()
        self.register("async-other@example.com")
        denied = self.client.get(f"/api/ai/content-plans/{generation.id}/status/")
        self.assertEqual(denied.status_code, 404)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_async_content_plan_task_is_idempotent_after_completion(self):
        self.register("async-task@example.com")
        business = self.create_business()
        with patch("apps.ai.content_plan_service.get_ai_provider", return_value=fake_groq_provider()):
            with self.captureOnCommitCallbacks(execute=True):
                record = submit_weekly_content_plan_job(
                    user=get_user_model().objects.get(email="async-task@example.com"),
                    business_id=business["_id"],
                    platforms=["linkedin"],
                    start_date=timezone.now().date() + timedelta(days=1),
                    goal="engagement",
                    idempotency_key="task-idempotent-plan",
                )
        record.refresh_from_db()
        self.assertEqual(record.status, AIContentGeneration.Status.COMPLETED)
        self.assertEqual(record.versions.count(), 1)
        with patch("apps.ai.content_plan_service.get_ai_provider") as provider_factory:
            generate_content_plan_task.apply(args=[str(record.id)])
        provider_factory.assert_not_called()
        record.refresh_from_db()
        self.assertEqual(record.status, AIContentGeneration.Status.COMPLETED)
        self.assertEqual(record.versions.count(), 1)

    def test_running_async_content_plan_task_is_not_executed_twice(self):
        self.register("async-running@example.com")
        business = self.create_business()
        record = AIContentGeneration.objects.create(
            business_id=business["_id"],
            user=get_user_model().objects.get(email="async-running@example.com"),
            feature_name="weekly_content_plan",
            objective="engagement",
            platform="linkedin",
            status=AIContentGeneration.Status.RUNNING,
            task_id="same-task",
            started_at=timezone.now(),
            attempt_count=1,
        )
        with patch("apps.ai.content_plan_service.get_ai_provider") as provider_factory:
            returned = run_queued_content_plan_generation(generation_id=str(record.id), task_id="same-task")
        provider_factory.assert_not_called()
        record.refresh_from_db()
        self.assertEqual(returned.id, record.id)
        self.assertEqual(record.status, AIContentGeneration.Status.RUNNING)
        self.assertEqual(record.attempt_count, 1)

    def test_content_plan_draft_conversion_is_business_isolated(self):
        self.register("draft-owner@example.com")
        business = self.create_business()
        with patch("apps.ai.content_plan_service.get_ai_provider", return_value=fake_groq_provider()):
            response = self.client.post(
                "/api/ai/content-plans/generate/",
                {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
                format="json",
            )
        self.assertEqual(response.status_code, 201, response.content)
        generation_id = response.data["id"]

        self.client.credentials()
        self.register("draft-other@example.com")
        denied = self.client.post(
            f"/api/ai/content-plans/{generation_id}/create-drafts/",
            {"item_day_numbers": [1]},
            format="json",
        )
        self.assertEqual(denied.status_code, 400)
        self.assertEqual(ContentDraft.objects.filter(source_ai_generation_id=generation_id).count(), 0)

    def test_content_plan_draft_creation_rolls_back_on_write_error(self):
        self.register("draft-rollback@example.com")
        business = self.create_business()
        with patch("apps.ai.content_plan_service.get_ai_provider", return_value=fake_groq_provider()):
            response = self.client.post(
                "/api/ai/content-plans/generate/",
                {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
                format="json",
            )
        self.assertEqual(response.status_code, 201, response.content)
        generation = AIContentGeneration.objects.get(id=response.data["id"])
        with patch.object(ContentVersion.objects, "create", side_effect=RuntimeError("version write failed")):
            with self.assertRaises(RuntimeError):
                create_drafts_from_plan(user=generation.user, generation_id=str(generation.id), item_day_numbers=[1, 2])
        generation.refresh_from_db()
        self.assertEqual(ContentDraft.objects.filter(source_ai_generation=generation).count(), 0)
        self.assertEqual(generation.draft_links, {})

    def test_ai_generation_history_ordering_and_filtering(self):
        self.register("history-filter@example.com")
        business = self.create_business()
        business_id = business["_id"]
        other_business = self.client.post(
            "/api/business/",
            {
                "name": "Other Workspace",
                "industry": "SaaS",
                "country": "US",
                "productOrService": "Other",
                "targetAudience": "Founders",
                "goals": ["leads"],
                "knownCompetitors": [],
                "brandVoice": "Clear",
            },
            format="json",
        ).data["data"]
        rows = [
            AIContentGeneration.objects.create(
                business_id=business_id,
                user=None,
                objective="old",
                platform="linkedin",
                provider="groq",
                model="openai/gpt-oss-20b",
                status=AIContentGeneration.Status.COMPLETED,
                created_at=timezone.now() - timedelta(days=1),
            ),
            AIContentGeneration.objects.create(
                business_id=business_id,
                user=None,
                objective="new",
                platform="linkedin",
                provider="groq",
                model="openai/gpt-oss-20b",
                status=AIContentGeneration.Status.COMPLETED,
                created_at=timezone.now(),
            ),
        ]
        AIContentGeneration.objects.create(
            business_id=other_business["_id"],
            user=None,
            objective="other",
            platform="linkedin",
            provider="groq",
            model="openai/gpt-oss-20b",
            status=AIContentGeneration.Status.COMPLETED,
        )

        filtered = list(
            AIContentGeneration.objects.filter(
                business_id=business_id,
                provider="groq",
                status=AIContentGeneration.Status.COMPLETED,
            ).order_by("-created_at")
        )
        self.assertEqual([row.id for row in filtered], [rows[1].id, rows[0].id])

    def test_invalid_plan_prevents_partial_draft_creation(self):
        self.register("invalid-draft-plan@example.com")
        business = self.create_business()
        with patch("apps.ai.content_plan_service.get_ai_provider", return_value=fake_groq_provider()):
            response = self.client.post(
                "/api/ai/content-plans/generate/",
                {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
                format="json",
            )
        self.assertEqual(response.status_code, 201, response.content)
        generation = AIContentGeneration.objects.get(id=response.data["id"])
        invalid_plan = valid_content_plan()
        invalid_plan["items"][0]["caption"] = ""
        generation.structured_output = invalid_plan
        generation.generated_content = invalid_plan
        generation.save(update_fields=["structured_output", "generated_content"])
        with self.assertRaises(ValidationError):
            create_drafts_from_plan(user=generation.user, generation_id=str(generation.id), item_day_numbers=[1, 2])
        self.assertEqual(ContentDraft.objects.filter(source_ai_generation=generation).count(), 0)

    def test_failed_content_plan_generation_is_recorded_safely(self):
        self.register("fail-plan@example.com")
        business = self.create_business()
        with patch("apps.ai.content_plan_service.get_ai_provider") as provider_factory:
            provider = fake_groq_provider()
            provider.generate_structured_json = Mock(side_effect=RuntimeError("provider exploded"))
            provider_factory.return_value = provider
            response = self.client.post(
                "/api/ai/content-plans/generate/",
                {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
                format="json",
            )
        self.assertEqual(response.status_code, 500)
        record = AIContentGeneration.objects.filter(feature_name="weekly_content_plan").latest("created_at")
        self.assertEqual(record.status, "failed")
        self.assertEqual(record.error_type, "RuntimeError")

    @override_settings(AI_PROVIDER="groq", GROQ_API_KEY="")
    def test_provider_factory_missing_groq_key_raises(self):
        with self.assertRaises(AIConfigurationError):
            get_ai_provider()

    @override_settings(AI_PROVIDER="groq", GROQ_API_KEY="PASTE_YOUR_NEW_GROQ_KEY_HERE")
    def test_provider_factory_placeholder_groq_key_raises(self):
        with self.assertRaises(AIConfigurationError):
            get_ai_provider()

    @override_settings(AI_PROVIDER="groq", GROQ_API_KEY="test-key")
    def test_provider_factory_selects_groq(self):
        self.assertIsInstance(get_ai_provider(), GroqProvider)

    @override_settings(AI_PROVIDER="groq", GROQ_API_KEY="test-key")
    def test_provider_factory_defaults_to_groq_only(self):
        self.assertEqual(get_ai_provider().name, "groq")

    @override_settings(AI_PROVIDER="not-real")
    def test_provider_factory_rejects_unsupported_provider(self):
        with self.assertRaises(AIConfigurationError):
            get_ai_provider()

    @override_settings(GROQ_API_KEY="test-key", GROQ_DEFAULT_MODEL="openai/gpt-oss-20b")
    def test_groq_provider_returns_normalized_plain_text_and_structured_output(self):
        provider = GroqProvider()
        provider.client.chat.completions.create = Mock(return_value=groq_response("Plain content"))
        plain = provider.generate_text(system="system", user="user")
        self.assertEqual(plain.provider, "groq")
        self.assertEqual(plain.model, "openai/gpt-oss-20b")
        self.assertEqual(plain.content, "Plain content")
        self.assertEqual(plain.input_tokens, 111)
        self.assertEqual(plain.output_tokens, 222)
        self.assertEqual(plain.request_id, "groq-request-1")
        self.assertEqual(plain.finish_reason, "stop")

        provider.client.chat.completions.create = Mock(return_value=groq_response(json.dumps(valid_content_plan())))
        structured = provider.generate_structured_json(
            system="system",
            user="user",
            schema={"type": "object"},
            prompt_version="content-plan-v1",
        )
        self.assertEqual(structured.provider, "groq")
        self.assertEqual(structured.parsed_data["items"][0]["day_number"], 1)
        kwargs = provider.client.chat.completions.create.call_args.kwargs
        self.assertFalse(kwargs["stream"])
        self.assertEqual(kwargs["response_format"]["type"], "json_schema")
        self.assertEqual(kwargs["max_completion_tokens"], 4000)
        self.assertEqual(kwargs["reasoning_effort"], "medium")

    @override_settings(GROQ_API_KEY="test-key")
    def test_groq_provider_retries_structured_schema_failure_once(self):
        provider = GroqProvider()
        response = httpx.Response(
            400,
            request=httpx.Request("POST", "https://api.groq.com"),
            json={"error": {"code": "json_validate_failed", "message": "Generated JSON does not match the expected schema"}},
        )
        provider.client.chat.completions.create = Mock(
            side_effect=[
                GroqBadRequestError("schema failed", response=response, body=response.json()),
                groq_response(json.dumps(valid_content_plan())),
            ]
        )
        structured = provider.generate_structured_json(
            system="system",
            user="user",
            schema={"type": "object"},
            prompt_version="content-plan-v1",
        )
        self.assertEqual(structured.provider, "groq")
        self.assertEqual(provider.client.chat.completions.create.call_count, 2)
        first = provider.client.chat.completions.create.call_args_list[0].kwargs
        second = provider.client.chat.completions.create.call_args_list[1].kwargs
        self.assertEqual(first["reasoning_effort"], "medium")
        self.assertEqual(second["reasoning_effort"], "low")
        self.assertEqual(second["temperature"], 0.2)
        self.assertIn("Follow the supplied JSON Schema exactly", second["messages"][1]["content"])
        self.assertNotIn("Return exactly seven items", second["messages"][1]["content"])

    @override_settings(GROQ_API_KEY="test-key")
    def test_groq_provider_maps_errors_and_invalid_output(self):
        provider = GroqProvider()
        provider.client.chat.completions.create = Mock(side_effect=GroqAPITimeoutError(request=httpx.Request("POST", "https://api.groq.com")))
        with self.assertRaises(AITimeoutError):
            provider.generate_structured_json(system="x", user="{}", schema={"type": "object"}, prompt_version="test")

        response = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com"))
        provider.client.chat.completions.create = Mock(side_effect=GroqRateLimitError("limited", response=response, body=None))
        with self.assertRaises(AIRateLimitError):
            provider.generate_structured_json(system="x", user="{}", schema={"type": "object"}, prompt_version="test")

        provider.client.chat.completions.create = Mock(
            side_effect=GroqAPIError("failed", request=httpx.Request("POST", "https://api.groq.com"), body=None)
        )
        with self.assertRaises(AIProviderError):
            provider.generate_structured_json(system="x", user="{}", schema={"type": "object"}, prompt_version="test")

        provider.client.chat.completions.create = Mock(return_value=groq_response(""))
        with self.assertRaises(AIValidationError):
            provider.generate_structured_json(system="x", user="{}", schema={"type": "object"}, prompt_version="test")

        provider.client.chat.completions.create = Mock(return_value=groq_response("{not-json"))
        with self.assertRaises(AIValidationError):
            provider.generate_structured_json(system="x", user="{}", schema={"type": "object"}, prompt_version="test")

    def test_groq_content_plan_records_metadata_and_sanitizes_errors(self):
        self.register("groq-plan@example.com")
        business = self.create_business()
        result = AIProviderResult(
            content="",
            parsed_data=valid_content_plan(),
            provider="groq",
            model="openai/gpt-oss-20b",
            input_tokens=111,
            output_tokens=222,
            request_id="groq-request-1",
            finish_reason="stop",
        )
        with patch("apps.ai.content_plan_service.get_ai_provider") as provider_factory:
            provider = Mock(name="groq", model="openai/gpt-oss-20b")
            provider.name = "groq"
            provider.model = "openai/gpt-oss-20b"
            provider.generate_structured_json.return_value = result
            provider_factory.return_value = provider
            with self.assertLogs("apps.ai.content_plan_service", level="INFO") as logs:
                response = self.client.post(
                    "/api/ai/content-plans/generate/",
                    {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
                    format="json",
                )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.data["provider"], "groq")
        self.assertEqual(response.data["model"], "openai/gpt-oss-20b")
        self.assertEqual(response.data["usage"]["input_tokens"], 111)
        log_output = "\n".join(logs.output)
        self.assertIn("ai_generation_completed", log_output)
        self.assertIn("provider=groq", log_output)
        self.assertIn("model=openai/gpt-oss-20b", log_output)
        self.assertIn("input_tokens=111", log_output)
        self.assertNotIn("Authorization", log_output)
        self.assertNotIn("Bearer", log_output)
        self.assertNotIn("GROQ_API_KEY", log_output)
        record = AIContentGeneration.objects.get(id=response.data["id"])
        self.assertEqual(record.provider_request_id, "groq-request-1")
        self.assertEqual(record.generation_parameters["finish_reason"], "stop")

        with patch("apps.ai.content_plan_service.get_ai_provider") as provider_factory:
            provider = Mock(name="groq", model="openai/gpt-oss-20b")
            provider.name = "groq"
            provider.model = "openai/gpt-oss-20b"
            provider.generate_structured_json.side_effect = AIProviderError("raw groq secret detail")
            provider_factory.return_value = provider
            failed = self.client.post(
                "/api/ai/content-plans/generate/",
                {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
                format="json",
            )
        self.assertEqual(failed.status_code, 502)
        self.assertEqual(failed.data["message"], "AI provider request failed")
        self.assertNotIn("raw groq", str(failed.data))

    def test_schema_invalid_groq_plan_is_sanitized(self):
        self.register("groq-invalid-schema@example.com")
        business = self.create_business()
        bad_plan = valid_content_plan()
        bad_plan["items"][0]["platform"] = "invalid"
        with patch("apps.ai.content_plan_service.get_ai_provider", return_value=fake_groq_provider(AIProviderResult(
            content="",
            parsed_data=bad_plan,
            provider="groq",
            model="openai/gpt-oss-20b",
            input_tokens=1,
            output_tokens=1,
            request_id="bad-schema",
            finish_reason="stop",
        ))):
            response = self.client.post(
                "/api/ai/content-plans/generate/",
                {"business_id": business["_id"], "platforms": ["linkedin"], "start_date": "2026-08-03"},
                format="json",
            )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["message"], "AI provider returned invalid content")


@unittest.skipIf(connection.vendor == "sqlite", "SQLite does not model PostgreSQL row-lock concurrency")
class ContentPlanConcurrencyTests(TransactionTestCase):
    def test_concurrent_duplicate_draft_conversion_creates_one_draft(self):
        user = get_user_model().objects.create_user(
            email="concurrent-plan@example.com",
            password="Password123!",
            full_name="Concurrent User",
        )
        business = Business.objects.create(
            owner=user,
            name="Concurrent Business",
            industry="SaaS",
            country="US",
            product_or_service="AI tools",
            target_audience="Founders",
            goals=["engagement"],
            known_competitors=[],
            brand_voice="Clear",
        )
        generation = AIContentGeneration.objects.create(
            business=business,
            user=user,
            feature_name="weekly_content_plan",
            prompt_version="content-plan-v1",
            objective="engagement",
            platform="linkedin",
            audience="Founders",
            tone="Clear",
            content_format="seven_day_plan",
            generated_content=valid_content_plan(),
            structured_output=valid_content_plan(),
            provider="groq",
            model="openai/gpt-oss-20b",
            usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            status=AIContentGeneration.Status.COMPLETED,
        )
        barrier = threading.Barrier(2)
        errors = []

        def convert():
            try:
                close_old_connections()
                barrier.wait(timeout=5)
                create_drafts_from_plan(user=user, generation_id=str(generation.id), item_day_numbers=[1])
            except Exception as exc:  # pragma: no cover - assertion reports the collected error
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=convert), threading.Thread(target=convert)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(errors, [])
        self.assertEqual(ContentDraft.objects.filter(source_ai_generation=generation, source_plan_day=1).count(), 1)

    def test_concurrent_idempotent_plan_submission_creates_one_generation(self):
        user = get_user_model().objects.create_user(
            email="concurrent-queue@example.com",
            password="Password123!",
            full_name="Concurrent Queue",
        )
        business = Business.objects.create(
            owner=user,
            name="Concurrent Queue Business",
            industry="SaaS",
            country="US",
            product_or_service="AI tools",
            target_audience="Founders",
            goals=["engagement"],
            known_competitors=[],
            brand_voice="Clear",
        )
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def submit():
            try:
                close_old_connections()
                barrier.wait(timeout=5)
                generation = submit_weekly_content_plan_job(
                    user=user,
                    business_id=str(business.id),
                    platforms=["linkedin"],
                    start_date=timezone.now().date() + timedelta(days=1),
                    goal="engagement",
                    idempotency_key="concurrent-plan",
                )
                results.append(generation.id)
            except Exception as exc:  # pragma: no cover - assertion reports the collected error
                errors.append(exc)
            finally:
                connection.close()

        with patch("apps.ai.tasks.generate_content_plan_task.apply_async", return_value=SimpleNamespace(id="queued-task")):
            threads = [threading.Thread(target=submit), threading.Thread(target=submit)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)

        self.assertEqual(errors, [])
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(AIContentGeneration.objects.filter(business=business, idempotency_key="concurrent-plan").count(), 1)
