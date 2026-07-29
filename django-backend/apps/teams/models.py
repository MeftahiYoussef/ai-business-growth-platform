import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class BusinessMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        CREATOR = "content_creator", "Content creator"
        ANALYST = "analyst", "Analyst"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="memberships", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="business_memberships", on_delete=models.CASCADE)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.VIEWER)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("business", "user")
        indexes = [models.Index(fields=["business"]), models.Index(fields=["user"]), models.Index(fields=["role"])]


class TeamInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="team_invitations", on_delete=models.CASCADE)
    email = models.EmailField()
    role = models.CharField(max_length=32, choices=BusinessMember.Role.choices, default=BusinessMember.Role.VIEWER)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="sent_team_invitations", on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["business"]), models.Index(fields=["email"]), models.Index(fields=["status"])]


class ActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", related_name="activity_logs", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=120, blank=True, default="")
    entity_id = models.CharField(max_length=120, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["business"]), models.Index(fields=["action"]), models.Index(fields=["created_at"])]
