import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Report(models.Model):
    class ReportType(models.TextChoices):
        WEEKLY = "weekly_performance", "Weekly performance"
        MONTHLY = "monthly_performance", "Monthly performance"
        CAMPAIGN = "campaign_performance", "Campaign performance"
        COMPETITOR = "competitor_comparison", "Competitor comparison"
        EXECUTIVE = "executive_summary", "Executive summary"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="reports", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    report_type = models.CharField(max_length=64, choices=ReportType.choices)
    date_range_start = models.DateField(null=True, blank=True)
    date_range_end = models.DateField(null=True, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.READY)
    summary = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["business"]), models.Index(fields=["report_type"]), models.Index(fields=["created_at"])]
