import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Business(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legacy_mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="businesses", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    product_or_service = models.CharField(max_length=255)
    target_audience = models.CharField(max_length=255)
    goals = models.JSONField(default=list, blank=True)
    known_competitors = models.JSONField(default=list, blank=True)
    brand_voice = models.CharField(max_length=500, default="Clear, confident, and helpful", blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["owner"]), models.Index(fields=["name"]), models.Index(fields=["legacy_mongo_id"])]

    def __str__(self):
        return self.name
