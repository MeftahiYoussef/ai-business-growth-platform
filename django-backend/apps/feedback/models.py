import uuid

from django.db import models
from django.utils import timezone


class Feedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legacy_mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True, db_index=True)
    business = models.ForeignKey("businesses.Business", related_name="feedback", on_delete=models.CASCADE)
    content_idea = models.ForeignKey("content_ideas.ContentIdea", related_name="feedback", on_delete=models.CASCADE)
    liked = models.BooleanField()
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["business"]), models.Index(fields=["content_idea"]), models.Index(fields=["created_at"])]
