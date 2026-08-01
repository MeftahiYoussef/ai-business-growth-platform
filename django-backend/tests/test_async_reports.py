from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ai.models import AIContentGeneration
from apps.ai.providers.base import AIProviderResult
from apps.businesses.models import Business
from apps.competitors.models import Competitor
from apps.content_planner.models import ContentDraft
from apps.reports.models import Report
from apps.reports.tasks import generate_business_report_task
from apps.trends.models import Trend
from common.models import BackgroundJob


def fake_report_provider():
    provider = Mock(name="groq", model="openai/gpt-oss-20b")
    provider.name = "groq"
    provider.model = "openai/gpt-oss-20b"
    provider.generate_structured_json.return_value = AIProviderResult(
        content="",
        parsed_data={
            "highlights": ["Draft pipeline is active."],
            "risks": ["No scheduled content is recorded."],
            "recommendations": [{"text": "Review drafts before scheduling.", "requires_human_review": True}],
        },
        provider="groq",
        model="openai/gpt-oss-20b",
        input_tokens=12,
        output_tokens=34,
        request_id="report-provider-request",
        finish_reason="stop",
    )
    return provider


class AsyncReportTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def register(self, email="report-owner@example.com"):
        response = self.client.post(
            "/api/auth/register",
            {"fullName": "Report Owner", "email": email, "password": "Password123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['token']}")
        return get_user_model().objects.get(email=email)

    def create_business(self, user=None):
        user = user or get_user_model().objects.get(email="report-owner@example.com")
        return Business.objects.create(
            owner=user,
            name="Report Studio",
            industry="SaaS",
            country="US",
            product_or_service="AI workflows",
            target_audience="Founders",
            goals=["engagement"],
            known_competitors=["OtherCo"],
            brand_voice="Clear",
        )

    def seed_report_data(self, business, user):
        ContentDraft.objects.create(
            business=business,
            title="Draft one",
            caption="Draft",
            platform="linkedin",
            content_type="linkedin_post",
            created_by=user,
            status=ContentDraft.Status.DRAFT,
            approval_status="draft",
        )
        ContentDraft.objects.create(
            business=business,
            title="Approved one",
            caption="Approved",
            platform="instagram",
            content_type="carousel",
            created_by=user,
            status=ContentDraft.Status.APPROVED,
            approval_status="approved",
        )
        AIContentGeneration.objects.create(
            business=business,
            user=user,
            feature_name="weekly_content_plan",
            objective="increase engagement",
            platform="linkedin",
            status=AIContentGeneration.Status.COMPLETED,
            usage={"input_tokens": 10, "output_tokens": 20},
        )
        AIContentGeneration.objects.create(
            business=business,
            user=user,
            feature_name="weekly_content_plan",
            objective="increase leads",
            platform="instagram",
            status=AIContentGeneration.Status.FAILED,
            usage={"input_tokens": 3, "output_tokens": 0},
        )
        Trend.objects.create(
            business=business,
            topic="Founder-led education",
            hashtags=["#founders"],
            hooks=["Teach one thing"],
            format="carousel",
            momentum_label=Trend.Momentum.EMERGING,
            trend_score=81,
        )
        Competitor.objects.create(business=business, name="OtherCo", platform="LinkedIn", followers=100)

    def queue_payload(self, business):
        today = timezone.localdate()
        return {
            "business_id": str(business.id),
            "report_type": "business_performance",
            "period_start": (today - timedelta(days=7)).isoformat(),
            "period_end": today.isoformat(),
            "include_ai_recommendations": False,
        }

    @override_settings(ASYNC_REPORTS_ENABLED=True, CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_async_business_report_queue_status_detail_and_exports(self):
        user = self.register()
        business = self.create_business(user)
        self.seed_report_data(business, user)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/reports/queue/", self.queue_payload(business), format="json", HTTP_IDEMPOTENCY_KEY="report-1")
        self.assertEqual(response.status_code, 202, response.content)
        job_id = response.data["job_id"]
        job = BackgroundJob.objects.get(id=job_id)
        self.assertEqual(job.status, BackgroundJob.Status.COMPLETED)
        self.assertEqual(job.progress, 100)
        report = Report.objects.get(job=job)
        self.assertEqual(report.report_type, Report.ReportType.BUSINESS_PERFORMANCE)
        self.assertEqual(report.summary["draft_total"], 1)
        self.assertEqual(report.summary["approved_total"], 1)
        self.assertEqual(report.summary["ai_generation_total"], 2)
        self.assertEqual(report.summary["ai_generation_completed"], 1)
        self.assertEqual(report.summary["ai_generation_failed"], 1)
        self.assertEqual(report.summary["ai_input_tokens"], 13)
        self.assertEqual(report.summary["ai_output_tokens"], 20)
        self.assertTrue(report.structured_content["data_limitations"])

        status_response = self.client.get(f"/api/reports/jobs/{job_id}/status/")
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.data["result_available"])
        self.assertEqual(status_response.data["report_id"], str(report.id))
        detail = self.client.get(f"/api/reports/{report.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["data"]["_id"], str(report.id))
        csv_response = self.client.get(f"/api/reports/{report.id}/export.csv/")
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(csv_response["Content-Type"], "text/csv")
        json_response = self.client.get(f"/api/reports/{report.id}/export.json/")
        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(json_response["Content-Type"], "application/json")

        duplicate = self.client.post("/api/reports/queue/", self.queue_payload(business), format="json", HTTP_IDEMPOTENCY_KEY="report-1")
        self.assertEqual(duplicate.status_code, 202)
        self.assertEqual(duplicate.data["job_id"], job_id)
        self.assertEqual(BackgroundJob.objects.filter(job_type=BackgroundJob.JobType.BUSINESS_REPORT).count(), 1)

        conflict_payload = {**self.queue_payload(business), "period_start": (timezone.localdate() - timedelta(days=8)).isoformat()}
        conflict = self.client.post("/api/reports/queue/", conflict_payload, format="json", HTTP_IDEMPOTENCY_KEY="report-1")
        self.assertEqual(conflict.status_code, 409)

    @override_settings(
        ASYNC_REPORTS_ENABLED=True,
        REPORT_AI_RECOMMENDATIONS_ENABLED=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    )
    def test_async_business_report_can_store_mocked_ai_recommendations(self):
        user = self.register("report-ai@example.com")
        business = self.create_business(user)
        self.seed_report_data(business, user)
        payload = {**self.queue_payload(business), "include_ai_recommendations": True}
        with patch("apps.reports.services.get_ai_provider", return_value=fake_report_provider()):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post("/api/reports/queue/", payload, format="json", HTTP_IDEMPOTENCY_KEY="report-ai")
        self.assertEqual(response.status_code, 202, response.content)
        report = Report.objects.get(job_id=response.data["job_id"])
        self.assertEqual(report.provider, "groq")
        self.assertEqual(report.model, "openai/gpt-oss-20b")
        self.assertEqual(report.usage["input_tokens"], 12)
        self.assertTrue(all(item["requires_human_review"] for item in report.structured_content["recommendations"]))

    @override_settings(ASYNC_REPORTS_ENABLED=True, CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_report_access_is_business_isolated_and_invalid_dates_are_rejected(self):
        user = self.register("report-access@example.com")
        business = self.create_business(user)
        bad = self.client.post(
            "/api/reports/queue/",
            {**self.queue_payload(business), "period_start": timezone.localdate().isoformat(), "period_end": (timezone.localdate() - timedelta(days=1)).isoformat()},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)
        with self.captureOnCommitCallbacks(execute=True):
            queued = self.client.post("/api/reports/queue/", self.queue_payload(business), format="json", HTTP_IDEMPOTENCY_KEY="report-owned")
        self.assertEqual(queued.status_code, 202)
        report = Report.objects.get(job_id=queued.data["job_id"])
        self.client.credentials()
        self.register("report-other@example.com")
        self.assertEqual(self.client.get(f"/api/reports/jobs/{queued.data['job_id']}/status/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/reports/{report.id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/reports/{report.id}/export.csv/").status_code, 404)

    @override_settings(ASYNC_REPORTS_ENABLED=False, CELERY_TASK_ALWAYS_EAGER=False)
    def test_async_report_queue_requires_enablement(self):
        user = self.register("report-disabled@example.com")
        business = self.create_business(user)
        response = self.client.post("/api/reports/queue/", self.queue_payload(business), format="json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["message"], "Asynchronous report generation is not enabled")

    @override_settings(ASYNC_REPORTS_ENABLED=True, CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_report_task_is_idempotent_after_completion(self):
        user = self.register("report-task@example.com")
        business = self.create_business(user)
        with self.captureOnCommitCallbacks(execute=True):
            queued = self.client.post("/api/reports/queue/", self.queue_payload(business), format="json", HTTP_IDEMPOTENCY_KEY="report-task")
        job_id = queued.data["job_id"]
        report_id = str(Report.objects.get(job_id=job_id).id)
        generate_business_report_task.apply(args=[job_id])
        self.assertEqual(Report.objects.filter(job_id=job_id).count(), 1)
        self.assertEqual(str(Report.objects.get(job_id=job_id).id), report_id)

