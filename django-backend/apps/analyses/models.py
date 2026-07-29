import uuid

from django.db import models
from django.utils import timezone


class BusinessAnalysis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legacy_mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True, db_index=True)
    business = models.ForeignKey("businesses.Business", related_name="analyses", on_delete=models.CASCADE)
    strengths = models.JSONField(default=list, blank=True)
    weaknesses = models.JSONField(default=list, blank=True)
    opportunities = models.JSONField(default=list, blank=True)
    threats = models.JSONField(default=list, blank=True)
    growth_recommendations = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["business"]), models.Index(fields=["created_at"])]
