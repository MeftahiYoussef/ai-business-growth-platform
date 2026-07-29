import uuid

from django.db import models
from django.utils import timezone


class Trend(models.Model):
    class Momentum(models.TextChoices):
        EMERGING = "Emerging", "Emerging"
        PEAKING = "Peaking", "Peaking"
        FADING = "Fading", "Fading"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legacy_mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True, db_index=True)
    business = models.ForeignKey("businesses.Business", related_name="trends", on_delete=models.CASCADE)
    topic = models.CharField(max_length=255)
    hashtags = models.JSONField(default=list, blank=True)
    hooks = models.JSONField(default=list, blank=True)
    format = models.CharField(max_length=120)
    momentum_label = models.CharField(max_length=16, choices=Momentum.choices)
    trend_score = models.FloatField()
    growth_rate = models.FloatField(default=0)
    confidence = models.FloatField(default=0.75)
    explanation = models.TextField(blank=True, default="")
    source_posts = models.ManyToManyField("competitor_posts.CompetitorPost", blank=True, related_name="source_trends")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["topic"]),
            models.Index(fields=["momentum_label"]),
            models.Index(fields=["created_at"]),
        ]
