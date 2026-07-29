import uuid

from django.db import models
from django.utils import timezone


class ContentIdea(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SAVED = "saved", "Saved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legacy_mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True, db_index=True)
    business = models.ForeignKey("businesses.Business", related_name="content_ideas", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    hook = models.TextField()
    caption = models.TextField()
    cta = models.TextField()
    hashtags = models.JSONField(default=list, blank=True)
    format = models.CharField(max_length=120)
    engagement_potential_score = models.FloatField()
    trend_match_score = models.FloatField()
    reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["title"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]
