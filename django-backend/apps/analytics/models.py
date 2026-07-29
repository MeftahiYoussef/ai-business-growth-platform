import uuid

from django.db import models
from django.utils import timezone


class Goal(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        AT_RISK = "at_risk", "At risk"
        REACHED = "reached", "Reached"
        PAUSED = "paused", "Paused"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="performance_goals", on_delete=models.CASCADE)
    metric = models.CharField(max_length=120)
    current_value = models.FloatField(default=0)
    target_value = models.FloatField()
    start_date = models.DateField()
    deadline = models.DateField(null=True, blank=True)
    platform = models.CharField(max_length=64, blank=True, default="")
    campaign = models.ForeignKey("content_planner.Campaign", null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    recommended_next_actions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    @property
    def progress_percentage(self):
        if not self.target_value:
            return 0
        return min(100, round((self.current_value / self.target_value) * 100, 2))
