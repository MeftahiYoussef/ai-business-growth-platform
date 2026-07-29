import uuid

from django.db import models
from django.utils import timezone


class Strategy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legacy_mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True, db_index=True)
    business = models.ForeignKey("businesses.Business", related_name="strategies", on_delete=models.CASCADE)
    weekly_calendar = models.JSONField(default=list, blank=True)
    best_posting_times = models.JSONField(default=list, blank=True)
    recommended_hashtags = models.JSONField(default=list, blank=True)
    target_audience_recommendation = models.TextField(blank=True, default="")
    next_best_actions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["business"]), models.Index(fields=["created_at"])]
