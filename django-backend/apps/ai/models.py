import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class AIContentGeneration(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        RETRYING = "retrying", "Retrying"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="ai_generations", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    feature_name = models.CharField(max_length=120, default="studio")
    prompt_version = models.CharField(max_length=80, blank=True, default="")
    objective = models.CharField(max_length=255)
    platform = models.CharField(max_length=64)
    audience = models.CharField(max_length=255, blank=True, default="")
    tone = models.CharField(max_length=120, blank=True, default="")
    language = models.CharField(max_length=64, blank=True, default="English")
    content_format = models.CharField(max_length=120, blank=True, default="")
    prompt = models.JSONField(default=dict, blank=True)
    input_snapshot = models.JSONField(default=dict, blank=True)
    generated_content = models.JSONField(default=dict, blank=True)
    structured_output = models.JSONField(default=dict, blank=True)
    provider = models.CharField(max_length=64, default="groq")
    model = models.CharField(max_length=120, default="mock-social-content-v1")
    generation_parameters = models.JSONField(default=dict, blank=True)
    usage = models.JSONField(default=dict, blank=True)
    feedback = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.COMPLETED)
    error_type = models.CharField(max_length=120, blank=True, default="")
    last_error_code = models.CharField(max_length=120, blank=True, default="")
    last_error_message = models.CharField(max_length=255, blank=True, default="")
    provider_request_id = models.CharField(max_length=255, blank=True, default="")
    latency_ms = models.PositiveIntegerField(default=0)
    draft_links = models.JSONField(default=dict, blank=True)
    task_id = models.CharField(max_length=255, blank=True, default="")
    queued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    idempotency_key = models.CharField(max_length=128, blank=True, default="")
    request_fingerprint = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "business", "idempotency_key"],
                condition=Q(idempotency_key__gt=""),
                name="unique_ai_generation_idempotency_key",
            )
        ]
        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["business", "created_at"]),
            models.Index(fields=["business", "status", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["user", "business", "status"]),
            models.Index(fields=["feature_name"]),
            models.Index(fields=["provider"]),
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["task_id"]),
            models.Index(fields=["queued_at"]),
            models.Index(fields=["idempotency_key"]),
            models.Index(fields=["request_fingerprint"]),
            models.Index(fields=["created_at"]),
        ]


class AIContentGenerationVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    generation = models.ForeignKey(AIContentGeneration, related_name="versions", on_delete=models.CASCADE)
    business = models.ForeignKey("businesses.Business", related_name="ai_generation_versions", on_delete=models.CASCADE)
    version_number = models.IntegerField()
    action = models.CharField(max_length=80, default="initial")
    generated_content = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("generation", "version_number")
