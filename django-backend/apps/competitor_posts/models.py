import uuid

from django.db import models
from django.utils import timezone


class CompetitorPost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legacy_mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True, db_index=True)
    competitor = models.ForeignKey("competitors.Competitor", related_name="posts", on_delete=models.CASCADE)
    business = models.ForeignKey("businesses.Business", related_name="competitor_posts", on_delete=models.CASCADE)
    platform = models.CharField(max_length=120)
    post_url = models.URLField(max_length=500, blank=True, default="")
    caption = models.TextField()
    hashtags = models.JSONField(default=list, blank=True)
    hook = models.TextField()
    format = models.CharField(max_length=120)
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    engagement_score = models.FloatField(default=0)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["competitor"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["published_at"]),
        ]
