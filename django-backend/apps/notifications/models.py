import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    class Type(models.TextChoices):
        COMPETITOR_POST = "new_competitor_post", "New competitor post"
        TREND = "new_relevant_trend", "New relevant trend"
        APPROVAL = "content_awaiting_approval", "Content awaiting approval"
        SCHEDULE_FAILED = "scheduled_post_failed", "Scheduled post failed"
        REPORT_READY = "report_ready", "Report ready"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="notifications", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="notifications", on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=64, choices=Type.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["business", "user", "created_at"]),
            models.Index(fields=["user"]),
            models.Index(fields=["read_at"]),
        ]


class NotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="notification_preferences", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="notification_preferences", on_delete=models.CASCADE)
    enabled_alert_types = models.JSONField(default=list, blank=True)
    in_app = models.BooleanField(default=True)
    email = models.BooleanField(default=False)
    daily_digest = models.BooleanField(default=False)
    weekly_digest = models.BooleanField(default=True)
    thresholds = models.JSONField(default=dict, blank=True)
    quiet_hours = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("business", "user")
