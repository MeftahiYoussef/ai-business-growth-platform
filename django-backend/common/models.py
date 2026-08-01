import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class BackgroundJob(models.Model):
    class JobType(models.TextChoices):
        BUSINESS_REPORT = "business_report", "Business report"
        SOCIAL_ACCOUNT_SYNC = "social_account_sync", "Social account sync"
        ANALYTICS_IMPORT = "analytics_import", "Analytics import"
        COMPETITOR_REFRESH = "competitor_refresh", "Competitor refresh"
        WEEKLY_REPORT = "weekly_report", "Weekly report"
        TREND_REFRESH = "trend_refresh", "Trend refresh"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        RETRYING = "retrying", "Retrying"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="background_jobs", on_delete=models.SET_NULL)
    business = models.ForeignKey("businesses.Business", related_name="background_jobs", on_delete=models.CASCADE)
    job_type = models.CharField(max_length=64, choices=JobType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    task_id = models.CharField(max_length=255, blank=True, default="")
    idempotency_key = models.CharField(max_length=128, blank=True, default="")
    request_fingerprint = models.CharField(max_length=64, blank=True, default="")
    input_payload = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    progress = models.PositiveSmallIntegerField(default=0)
    progress_label = models.CharField(max_length=80, blank=True, default="")
    attempt_count = models.PositiveIntegerField(default=0)
    queued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=120, blank=True, default="")
    error_message = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(progress__gte=0, progress__lte=100), name="background_job_progress_0_100"),
            models.UniqueConstraint(
                fields=["user", "business", "job_type", "idempotency_key"],
                condition=Q(idempotency_key__gt=""),
                name="unique_background_job_idempotency_key",
            ),
            models.UniqueConstraint(
                fields=["user", "business", "job_type", "request_fingerprint"],
                condition=Q(
                    idempotency_key="",
                    request_fingerprint__gt="",
                    status__in=["queued", "running", "retrying"],
                ),
                name="unique_active_background_job_fingerprint",
            ),
        ]
        indexes = [
            models.Index(fields=["business", "status", "created_at"]),
            models.Index(fields=["user", "business", "status"]),
            models.Index(fields=["job_type", "status"]),
            models.Index(fields=["task_id"]),
            models.Index(fields=["queued_at"]),
            models.Index(fields=["request_fingerprint"]),
            models.Index(fields=["created_at"]),
        ]
