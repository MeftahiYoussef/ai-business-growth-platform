import csv
import hashlib
import io
import json
import logging
import re
import time
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.ai.exceptions import AIIdempotencyConflictError, AIValidationError
from apps.ai.models import AIContentGeneration
from apps.ai.providers.factory import get_ai_provider
from apps.businesses.models import Business
from apps.competitors.models import Competitor
from apps.content_planner.models import ContentDraft
from apps.integrations.models import SocialPost
from apps.notifications.models import Notification
from apps.trends.models import Trend
from common.models import BackgroundJob
from common.utilities.access import get_owned_business

from .models import Report

logger = logging.getLogger(__name__)

REPORT_PROMPT_VERSION = "business-performance-report-v1"
MAX_IDEMPOTENCY_KEY_LENGTH = 128
IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")
RAPID_DUPLICATE_WINDOW_SECONDS = 60


def normalize_report_idempotency_key(raw_key: str | None) -> str:
    key = (raw_key or "").strip()
    if not key:
        return ""
    if len(key) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise ValidationError({"idempotency_key": ["Idempotency-Key is too long"]})
    if not IDEMPOTENCY_KEY_PATTERN.fullmatch(key):
        raise ValidationError({"idempotency_key": ["Idempotency-Key contains unsupported characters"]})
    return key


def report_request_payload(*, report_type: str, period_start, period_end, include_ai_recommendations: bool) -> dict[str, Any]:
    return {
        "report_type": report_type,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "include_ai_recommendations": bool(include_ai_recommendations),
    }


def request_fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_report_request(*, report_type: str, period_start, period_end) -> None:
    if report_type != Report.ReportType.BUSINESS_PERFORMANCE:
        raise ValidationError({"report_type": ["Unsupported report type"]})
    if period_start > period_end:
        raise ValidationError({"period_end": ["Period end must be on or after period start"]})
    today = timezone.localdate()
    if period_start > today or period_end > today:
        raise ValidationError({"period_end": ["Future reporting periods are not supported"]})
    if (period_end - period_start).days + 1 > settings.REPORT_MAX_PERIOD_DAYS:
        raise ValidationError({"period_end": [f"Reporting period cannot exceed {settings.REPORT_MAX_PERIOD_DAYS} days"]})


def submit_business_report_job(
    *,
    user,
    business_id: str,
    report_type: str,
    period_start,
    period_end,
    include_ai_recommendations: bool = False,
    idempotency_key: str | None = None,
) -> BackgroundJob:
    business = get_owned_business(user, business_id)
    validate_report_request(report_type=report_type, period_start=period_start, period_end=period_end)
    key = normalize_report_idempotency_key(idempotency_key)
    payload = report_request_payload(
        report_type=report_type,
        period_start=period_start,
        period_end=period_end,
        include_ai_recommendations=include_ai_recommendations,
    )
    fingerprint = request_fingerprint(payload)
    now = timezone.now()
    with transaction.atomic():
        if key:
            existing = BackgroundJob.objects.select_for_update().filter(
                user=user,
                business=business,
                job_type=BackgroundJob.JobType.BUSINESS_REPORT,
                idempotency_key=key,
            ).first()
            if existing:
                if existing.request_fingerprint != fingerprint:
                    raise AIIdempotencyConflictError("Idempotency-Key was already used for a different report request")
                return existing
        else:
            existing = BackgroundJob.objects.select_for_update().filter(
                user=user,
                business=business,
                job_type=BackgroundJob.JobType.BUSINESS_REPORT,
                request_fingerprint=fingerprint,
                status__in=[BackgroundJob.Status.QUEUED, BackgroundJob.Status.RUNNING, BackgroundJob.Status.RETRYING],
                created_at__gte=now - timedelta(seconds=RAPID_DUPLICATE_WINDOW_SECONDS),
            ).first()
            if existing:
                return existing
        try:
            job = BackgroundJob.objects.create(
                user=user,
                business=business,
                job_type=BackgroundJob.JobType.BUSINESS_REPORT,
                status=BackgroundJob.Status.QUEUED,
                idempotency_key=key,
                request_fingerprint=fingerprint,
                input_payload=payload,
                progress=0,
                progress_label="queued",
                queued_at=now,
            )
        except IntegrityError:
            lookup = {
                "user": user,
                "business": business,
                "job_type": BackgroundJob.JobType.BUSINESS_REPORT,
            }
            if key:
                lookup["idempotency_key"] = key
            else:
                lookup["request_fingerprint"] = fingerprint
                lookup["status__in"] = [BackgroundJob.Status.QUEUED, BackgroundJob.Status.RUNNING, BackgroundJob.Status.RETRYING]
            existing = BackgroundJob.objects.select_for_update().get(**lookup)
            if existing.request_fingerprint != fingerprint:
                raise AIIdempotencyConflictError("Idempotency-Key was already used for a different report request")
            return existing

        def enqueue_task() -> None:
            from apps.reports.tasks import generate_business_report_task

            async_result = generate_business_report_task.apply_async(args=[str(job.id)])
            BackgroundJob.objects.filter(id=job.id).update(task_id=async_result.id)

        transaction.on_commit(enqueue_task)
        return job


def _date_range_filter(start, end, field: str = "created_at") -> dict[str, Any]:
    return {f"{field}__date__gte": start, f"{field}__date__lte": end}


def _counts_by(queryset, field: str) -> list[dict[str, Any]]:
    rows = queryset.exclude(**{field: ""}).values(field).annotate(count=Count("id")).order_by(field)
    return [{"name": row[field] or "unknown", "count": row["count"]} for row in rows]


def collect_business_report_metrics(*, business: Business, period_start, period_end) -> dict[str, Any]:
    drafts = ContentDraft.objects.filter(business=business, **_date_range_filter(period_start, period_end))
    ai_generations = AIContentGeneration.objects.filter(business=business, **_date_range_filter(period_start, period_end))
    trends = Trend.objects.filter(business=business, **_date_range_filter(period_start, period_end))
    social_posts = SocialPost.objects.filter(business=business, published_at__date__gte=period_start, published_at__date__lte=period_end)
    usage_rows = ai_generations.values_list("usage", flat=True)
    input_tokens = sum(int((row or {}).get("input_tokens", 0) or 0) for row in usage_rows)
    output_tokens = sum(int((row or {}).get("output_tokens", 0) or 0) for row in ai_generations.values_list("usage", flat=True))
    platform_breakdown = _counts_by(drafts, "platform")
    social_platforms = social_posts.values("account__platform").annotate(count=Count("id")).order_by("account__platform")
    for row in social_platforms:
        platform_breakdown.append({"name": row["account__platform"] or "unknown", "count": row["count"], "source": "published_posts"})
    metrics = {
        "content_total": drafts.count() + social_posts.count(),
        "draft_total": drafts.filter(status=ContentDraft.Status.DRAFT).count(),
        "approved_total": drafts.filter(status=ContentDraft.Status.APPROVED).count(),
        "scheduled_total": drafts.filter(status=ContentDraft.Status.SCHEDULED).count(),
        "published_total": drafts.filter(status=ContentDraft.Status.PUBLISHED).count() + social_posts.count(),
        "ai_generation_total": ai_generations.count(),
        "ai_generation_completed": ai_generations.filter(status=AIContentGeneration.Status.COMPLETED).count(),
        "ai_generation_failed": ai_generations.filter(status=AIContentGeneration.Status.FAILED).count(),
        "ai_input_tokens": input_tokens,
        "ai_output_tokens": output_tokens,
        "trend_total": trends.count(),
        "competitor_total": Competitor.objects.filter(business=business).count(),
    }
    return {
        "metrics": metrics,
        "platform_breakdown": platform_breakdown,
        "content_type_breakdown": _counts_by(drafts, "content_type"),
        "objective_breakdown": _counts_by(ai_generations, "objective"),
        "recent_trends": list(trends.order_by("-created_at").values("topic", "momentum_label", "trend_score")[:10]),
        "competitor_observations": list(
            Competitor.objects.filter(business=business).order_by("name").values("name", "platform", "status", "followers")[:10]
        ),
    }


def _deterministic_sections(*, business: Business, metrics: dict[str, Any]) -> dict[str, list[dict[str, str]] | list[str]]:
    strengths: list[str] = []
    risks: list[str] = []
    recommendations: list[dict[str, Any]] = []
    limitations = [
        "Only stored application data is included.",
        "Impressions, reach, clicks, engagement, revenue, and conversions are unavailable unless imported from connected provider metrics.",
        "AI recommendations require human review before acting on them.",
    ]
    if metrics["ai_generation_completed"]:
        strengths.append("AI generation activity is producing completed planning artifacts.")
    if metrics["draft_total"]:
        strengths.append("The content pipeline has draft material ready for review.")
    if not strengths:
        strengths.append("A baseline report is available; more stored activity will improve future analysis.")
    if metrics["ai_generation_failed"]:
        risks.append("Some AI generation requests failed during the period.")
    if metrics["scheduled_total"] == 0:
        risks.append("No scheduled content is recorded for the reporting period.")
    recommendations.append({"text": f"Review draft content for {business.name} and approve only items ready for publication.", "requires_human_review": True})
    recommendations.append({"text": "Use the data limitations section before presenting performance claims externally.", "requires_human_review": True})
    return {"highlights": strengths, "risks": risks, "recommendations": recommendations, "data_limitations": limitations}


def _recommendation_schema() -> dict[str, Any]:
    item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "text": {"type": "string"},
            "requires_human_review": {"type": "boolean", "const": True},
        },
        "required": ["text", "requires_human_review"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "highlights": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
            "risks": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
            "recommendations": {"type": "array", "items": item, "minItems": 1, "maxItems": 5},
        },
        "required": ["highlights", "risks", "recommendations"],
    }


def _ai_sections(*, business: Business, report: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    provider = get_ai_provider()
    minimal_input = {
        "business": {
            "name": business.name,
            "industry": business.industry,
            "product_or_service": business.product_or_service,
            "target_audience": business.target_audience,
            "goals": business.goals,
        },
        "period": report["period"],
        "metrics": report["metrics"],
        "platform_breakdown": report["platform_breakdown"],
        "content_type_breakdown": report["content_type_breakdown"],
        "objective_breakdown": report["objective_breakdown"],
        "data_limitations": report["data_limitations"],
    }
    result = provider.generate_structured_json(
        system=(
            "You write concise business performance report notes from aggregate metrics only. "
            "Never claim reach, impressions, revenue, conversions, or engagement rates unless included in metrics. "
            "Every recommendation must require human review."
        ),
        user=json.dumps(minimal_input, ensure_ascii=True),
        schema=_recommendation_schema(),
        prompt_version=REPORT_PROMPT_VERSION,
    )
    if not isinstance(result.parsed_data, dict):
        raise AIValidationError("AI provider did not return report recommendations")
    recommendations = result.parsed_data.get("recommendations", [])
    if not all(item.get("requires_human_review") is True for item in recommendations if isinstance(item, dict)):
        raise AIValidationError("AI report recommendations must require human review")
    usage = {
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "total_tokens": result.input_tokens + result.output_tokens,
        "provider": result.provider,
        "model": result.model,
        "request_id": result.request_id or "",
        "finish_reason": result.finish_reason or "",
    }
    return result.parsed_data, usage


def build_business_performance_report(*, business: Business, period_start, period_end, include_ai_recommendations: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    collected = collect_business_report_metrics(business=business, period_start=period_start, period_end=period_end)
    report = {
        "report_type": Report.ReportType.BUSINESS_PERFORMANCE,
        "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
        "business_overview": {
            "name": business.name,
            "industry": business.industry,
            "country": business.country,
            "product_or_service": business.product_or_service,
            "target_audience": business.target_audience,
            "goals": business.goals,
        },
        **collected,
    }
    report.update(_deterministic_sections(business=business, metrics=collected["metrics"]))
    usage: dict[str, Any] = {}
    if include_ai_recommendations and settings.REPORT_AI_RECOMMENDATIONS_ENABLED:
        ai_sections, usage = _ai_sections(business=business, report=report)
        report["highlights"] = ai_sections["highlights"]
        report["risks"] = ai_sections["risks"]
        report["recommendations"] = ai_sections["recommendations"]
    elif include_ai_recommendations:
        report["data_limitations"].append("AI recommendations are disabled in this environment.")
    return report, usage


def run_business_report_job(*, job_id: str, task_id: str = "") -> BackgroundJob | None:
    with transaction.atomic():
        job = BackgroundJob.objects.select_for_update().select_related("business").filter(id=job_id).first()
        if not job:
            return None
        if job.status in {BackgroundJob.Status.COMPLETED, BackgroundJob.Status.CANCELLED}:
            return job
        if job.status == BackgroundJob.Status.RUNNING:
            stale_after = timezone.now() - timedelta(seconds=settings.CELERY_TASK_TIME_LIMIT + 60)
            if job.started_at and job.started_at > stale_after:
                return job
        job.status = BackgroundJob.Status.RUNNING
        job.started_at = job.started_at or timezone.now()
        job.failed_at = None
        job.attempt_count += 1
        job.progress = 20
        job.progress_label = "collecting_data"
        if task_id and not job.task_id:
            job.task_id = task_id
        job.save(update_fields=["status", "started_at", "failed_at", "attempt_count", "progress", "progress_label", "task_id", "updated_at"])

    started = time.monotonic()
    payload = job.input_payload
    period_start = date.fromisoformat(payload["period_start"])
    period_end = date.fromisoformat(payload["period_end"])
    try:
        BackgroundJob.objects.filter(id=job.id).update(progress=45, progress_label="aggregating_metrics")
        report_payload, usage = build_business_performance_report(
            business=job.business,
            period_start=period_start,
            period_end=period_end,
            include_ai_recommendations=bool(payload.get("include_ai_recommendations")),
        )
        BackgroundJob.objects.filter(id=job.id).update(progress=90, progress_label="saving_report")
        with transaction.atomic():
            locked = BackgroundJob.objects.select_for_update().select_related("business").get(id=job.id)
            existing = Report.objects.filter(job=locked).first()
            if existing:
                report = existing
            else:
                report = Report.objects.create(
                    business=locked.business,
                    created_by=locked.user,
                    job=locked,
                    title=f"Business performance report {period_start.isoformat()} to {period_end.isoformat()}",
                    report_type=Report.ReportType.BUSINESS_PERFORMANCE,
                    date_range_start=period_start,
                    date_range_end=period_end,
                    filters={"include_ai_recommendations": bool(payload.get("include_ai_recommendations"))},
                    status=Report.Status.READY,
                    summary=report_payload["metrics"],
                    structured_content=report_payload,
                    provider=usage.get("provider", ""),
                    model=usage.get("model", ""),
                    usage=usage,
                    generated_at=timezone.now(),
                )
            locked.status = BackgroundJob.Status.COMPLETED
            locked.progress = 100
            locked.progress_label = "completed"
            locked.result_payload = {"report_id": str(report.id), "latency_ms": round((time.monotonic() - started) * 1000)}
            locked.completed_at = timezone.now()
            locked.failed_at = None
            locked.error_code = ""
            locked.error_message = ""
            locked.save()
            _create_report_notification_once(job=locked, report=report)
            logger.info("report_generation_completed job_id=%s report_id=%s business_id=%s status=%s", locked.id, report.id, locked.business_id, locked.status)
            return locked
    except Exception as exc:
        mark_report_job_failed(job_id=str(job.id), exc=exc)
        raise


def _create_report_notification_once(*, job: BackgroundJob, report: Report) -> None:
    if not job.user:
        return
    exists = Notification.objects.filter(
        business=job.business,
        user=job.user,
        notification_type=Notification.Type.REPORT_READY,
        metadata__job_id=str(job.id),
    ).exists()
    if exists:
        return
    Notification.objects.create(
        business=job.business,
        user=job.user,
        notification_type=Notification.Type.REPORT_READY,
        title="Report ready",
        message="Your business performance report is ready to review.",
        metadata={"job_id": str(job.id), "report_id": str(report.id)},
    )


def mark_report_job_retrying(*, job_id: str, exc: Exception) -> None:
    BackgroundJob.objects.filter(id=job_id).exclude(status=BackgroundJob.Status.COMPLETED).update(
        status=BackgroundJob.Status.RETRYING,
        progress=70,
        progress_label="generating_recommendations",
        error_code=exc.__class__.__name__,
        error_message="Temporary report generation failure; retrying",
        failed_at=None,
    )


def mark_report_job_failed(*, job_id: str, exc: Exception, message: str = "Report generation failed") -> None:
    BackgroundJob.objects.filter(id=job_id).exclude(status=BackgroundJob.Status.COMPLETED).update(
        status=BackgroundJob.Status.FAILED,
        progress=100,
        progress_label="failed",
        error_code=exc.__class__.__name__,
        error_message=message,
        failed_at=timezone.now(),
    )
    Report.objects.filter(job_id=job_id).update(status=Report.Status.FAILED)


def export_report_csv(report: Report) -> str:
    structured = report.structured_content or {}
    metrics = structured.get("metrics") or report.summary or {}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    for key in sorted(metrics):
        writer.writerow([key, metrics[key]])
    return output.getvalue()
