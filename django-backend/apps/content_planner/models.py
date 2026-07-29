import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone as django_timezone


class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="campaigns", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    objective = models.CharField(max_length=255, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    platforms = models.JSONField(default=list, blank=True)
    goals = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(default=django_timezone.now)


class ContentDraft(models.Model):
    class Status(models.TextChoices):
        IDEA = "idea", "Idea"
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In review"
        CHANGES_REQUESTED = "changes_requested", "Changes requested"
        APPROVED = "approved", "Approved"
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHING = "publishing", "Publishing"
        PUBLISHED = "published", "Published"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="content_drafts", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    caption = models.TextField(blank=True, default="")
    platform = models.CharField(max_length=64)
    content_type = models.CharField(max_length=80, blank=True, default="")
    hashtags = models.JSONField(default=list, blank=True)
    cta = models.TextField(blank=True, default="")
    campaign = models.ForeignKey(Campaign, null=True, blank=True, related_name="drafts", on_delete=models.SET_NULL)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="assigned_drafts", on_delete=models.SET_NULL)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="created_drafts", on_delete=models.SET_NULL)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    approval_status = models.CharField(max_length=32, default="draft")
    provider_post_id = models.CharField(max_length=255, blank=True, default="")
    source_ai_generation = models.ForeignKey(
        "ai.AIContentGeneration", null=True, blank=True, related_name="created_drafts", on_delete=models.SET_NULL
    )
    source_plan_day = models.IntegerField(null=True, blank=True)
    publication_result = models.JSONField(default=dict, blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_ai_generation", "source_plan_day"],
                condition=Q(source_ai_generation__isnull=False, source_plan_day__isnull=False),
                name="unique_ai_generation_plan_day_draft",
            )
        ]
        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["business", "status", "scheduled_at"]),
            models.Index(fields=["source_ai_generation", "source_plan_day"]),
            models.Index(fields=["status"]),
            models.Index(fields=["scheduled_at"]),
        ]


class ContentVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draft = models.ForeignKey(ContentDraft, related_name="versions", on_delete=models.CASCADE)
    business = models.ForeignKey("businesses.Business", related_name="content_versions", on_delete=models.CASCADE)
    version_number = models.IntegerField()
    title = models.CharField(max_length=255)
    caption = models.TextField(blank=True, default="")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    change_summary = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        unique_together = ("draft", "version_number")


class ReviewComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draft = models.ForeignKey(ContentDraft, related_name="comments", on_delete=models.CASCADE)
    business = models.ForeignKey("businesses.Business", related_name="review_comments", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    comment = models.TextField()
    mentions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=django_timezone.now)
