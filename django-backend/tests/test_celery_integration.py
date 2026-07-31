import os
import time
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from celery.contrib.testing.worker import start_worker
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.ai.content_plan_service import submit_weekly_content_plan_job
from apps.ai.models import AIContentGeneration
from apps.ai.providers.base import AIProviderResult
from apps.businesses.models import Business
from apps.content_planner.models import ContentDraft
from apps.reports.models import Report
from apps.reports.services import submit_business_report_job
from common.models import BackgroundJob
from config.celery import app as celery_app


def _valid_content_plan():
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


def _fake_provider():
    provider = Mock(name="groq", model="openai/gpt-oss-20b")
    provider.name = "groq"
    provider.model = "openai/gpt-oss-20b"
    provider.generate_structured_json.return_value = AIProviderResult(
        content="",
        parsed_data=_valid_content_plan(),
        provider="groq",
        model="openai/gpt-oss-20b",
        input_tokens=111,
        output_tokens=222,
        request_id="redis-worker-test",
        finish_reason="stop",
    )
    return provider


@pytest.mark.skipif(os.environ.get("RUN_REDIS_INTEGRATION") != "true", reason="Redis broker integration is opt-in")
@pytest.mark.django_db(transaction=True)
def test_redis_worker_completes_content_plan(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = False
    user = get_user_model().objects.create_user(
        email="redis-worker@example.com",
        password="Password123!",
        full_name="Redis Worker",
    )
    business = Business.objects.create(
        owner=user,
        name="Redis Worker Business",
        industry="SaaS",
        country="US",
        product_or_service="AI tools",
        target_audience="Founders",
        goals=["engagement"],
        known_competitors=[],
        brand_voice="Clear",
    )

    with patch("apps.ai.content_plan_service.get_ai_provider", return_value=_fake_provider()):
        with start_worker(celery_app, perform_ping_check=False, pool="solo", concurrency=1):
            record = submit_weekly_content_plan_job(
                user=user,
                business_id=str(business.id),
                platforms=["linkedin"],
                start_date=timezone.now().date() + timedelta(days=1),
                goal="engagement",
                idempotency_key="redis-worker-plan",
            )
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                record.refresh_from_db()
                if record.status == AIContentGeneration.Status.COMPLETED:
                    break
                time.sleep(0.5)

    record.refresh_from_db()
    assert record.status == AIContentGeneration.Status.COMPLETED
    assert record.attempt_count == 1
    assert len(record.structured_output["items"]) == 7
    assert record.usage["input_tokens"] == 111
    assert record.usage["output_tokens"] == 222
    assert record.versions.count() == 1


@pytest.mark.skipif(os.environ.get("RUN_REDIS_INTEGRATION") != "true", reason="Redis broker integration is opt-in")
@pytest.mark.django_db(transaction=True)
def test_redis_worker_completes_business_report(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = False
    settings.ASYNC_REPORTS_ENABLED = True
    settings.REPORT_AI_RECOMMENDATIONS_ENABLED = False
    user = get_user_model().objects.create_user(
        email="redis-report@example.com",
        password="Password123!",
        full_name="Redis Report",
    )
    business = Business.objects.create(
        owner=user,
        name="Redis Report Business",
        industry="SaaS",
        country="US",
        product_or_service="AI tools",
        target_audience="Founders",
        goals=["engagement"],
        known_competitors=[],
        brand_voice="Clear",
    )
    ContentDraft.objects.create(
        business=business,
        title="Report draft",
        caption="Draft",
        platform="linkedin",
        content_type="linkedin_post",
        created_by=user,
        status=ContentDraft.Status.DRAFT,
    )

    with start_worker(celery_app, perform_ping_check=False, pool="solo", concurrency=1):
        job = submit_business_report_job(
            user=user,
            business_id=str(business.id),
            report_type=Report.ReportType.BUSINESS_PERFORMANCE,
            period_start=timezone.localdate() - timedelta(days=1),
            period_end=timezone.localdate(),
            include_ai_recommendations=False,
            idempotency_key="redis-worker-report",
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            job.refresh_from_db()
            if job.status == BackgroundJob.Status.COMPLETED:
                break
            time.sleep(0.5)

    job.refresh_from_db()
    assert job.status == BackgroundJob.Status.COMPLETED
    assert job.attempt_count == 1
    report = Report.objects.get(job=job)
    assert report.summary["draft_total"] == 1
    assert report.structured_content["metrics"]["draft_total"] == 1
    assert Report.objects.filter(job=job).count() == 1
