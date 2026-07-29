import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class SocialConnection(models.Model):
    class Provider(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox"
        INSTAGRAM = "instagram", "Instagram"
        FACEBOOK = "facebook", "Facebook"
        LINKEDIN = "linkedin", "LinkedIn"

    class Status(models.TextChoices):
        CONNECTED = "connected", "Connected"
        NEEDS_RECONNECT = "needs_reconnect", "Needs reconnect"
        REVOKED = "revoked", "Revoked"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="social_connections", on_delete=models.CASCADE)
    provider = models.CharField(max_length=32, choices=Provider.choices)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.CONNECTED)
    display_name = models.CharField(max_length=255)
    encrypted_access_token = models.TextField(blank=True, default="")
    encrypted_refresh_token = models.TextField(blank=True, default="")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    required_permissions = models.JSONField(default=list, blank=True)
    last_successful_sync_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    connected_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["business"]), models.Index(fields=["provider"]), models.Index(fields=["status"])]


class SocialAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(SocialConnection, related_name="accounts", on_delete=models.CASCADE)
    business = models.ForeignKey("businesses.Business", related_name="social_accounts", on_delete=models.CASCADE)
    platform = models.CharField(max_length=32)
    provider_account_id = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    profile_url = models.URLField(max_length=500, blank=True, default="")
    followers = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("connection", "provider_account_id")
        indexes = [models.Index(fields=["business"]), models.Index(fields=["platform"])]


class SocialPost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="social_posts", on_delete=models.CASCADE)
    account = models.ForeignKey(SocialAccount, related_name="posts", on_delete=models.CASCADE)
    provider_post_id = models.CharField(max_length=255)
    caption = models.TextField(blank=True, default="")
    content_type = models.CharField(max_length=80, blank=True, default="")
    published_at = models.DateTimeField(default=timezone.now)
    permalink = models.URLField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("account", "provider_post_id")
        indexes = [models.Index(fields=["business"]), models.Index(fields=["published_at"])]


class SocialPostMetricSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(SocialPost, related_name="metric_snapshots", on_delete=models.CASCADE)
    business = models.ForeignKey("businesses.Business", related_name="post_metric_snapshots", on_delete=models.CASCADE)
    snapshot_date = models.DateField()
    reach = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    video_views = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("post", "snapshot_date")
        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["business", "snapshot_date"]),
            models.Index(fields=["snapshot_date"]),
        ]


class SocialAccountMetricSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(SocialAccount, related_name="metric_snapshots", on_delete=models.CASCADE)
    business = models.ForeignKey("businesses.Business", related_name="account_metric_snapshots", on_delete=models.CASCADE)
    snapshot_date = models.DateField()
    followers = models.IntegerField(default=0)
    reach = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    engagement = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("account", "snapshot_date")
        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["business", "snapshot_date"]),
            models.Index(fields=["snapshot_date"]),
        ]


class SynchronizationJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="sync_jobs", on_delete=models.CASCADE)
    connection = models.ForeignKey(SocialConnection, related_name="sync_jobs", on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)


class SynchronizationError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(SynchronizationJob, related_name="errors", on_delete=models.CASCADE)
    business = models.ForeignKey("businesses.Business", related_name="sync_errors", on_delete=models.CASCADE)
    message = models.TextField()
    safe_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
