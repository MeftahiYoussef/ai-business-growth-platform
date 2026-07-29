import uuid

from django.db import models
from django.utils import timezone


class Competitor(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legacy_mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True, db_index=True)
    business = models.ForeignKey("businesses.Business", related_name="competitors", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    platform = models.CharField(max_length=120)
    profile_url = models.URLField(max_length=500, blank=True, default="")
    followers = models.IntegerField(default=0)
    engagement_rate = models.FloatField(default=0)
    posting_frequency = models.CharField(max_length=120, default="Unknown", blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["name"]),
            models.Index(fields=["platform"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.platform})"
