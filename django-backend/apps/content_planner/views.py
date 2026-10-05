from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.teams.permissions import can_approve_content, can_write_content
from common.utilities.access import get_owned_business

from .models import Campaign, ContentDraft, ContentVersion, ReviewComment
from .serializers import CampaignSerializer, ContentDraftSerializer, ContentVersionSerializer, ReviewCommentSerializer


class CampaignView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        campaigns = Campaign.objects.filter(business=business).order_by("-created_at")
        return Response({"success": True, "data": CampaignSerializer(campaigns, many=True).data})

    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        if not can_write_content(request.user, business):
            raise PermissionDenied("Not allowed to create campaigns")
        serializer = CampaignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = serializer.save(business=business)
        return Response({"success": True, "data": CampaignSerializer(campaign).data}, status=status.HTTP_201_CREATED)


class DraftView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        qs = ContentDraft.objects.filter(business=business)
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        if request.query_params.get("platform"):
            qs = qs.filter(platform=request.query_params["platform"])
        return Response({"success": True, "data": ContentDraftSerializer(qs.order_by("-created_at")[:100], many=True).data})

    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        if not can_write_content(request.user, business):
            raise PermissionDenied("Not allowed to create content")
        serializer = ContentDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        draft = serializer.save(business=business, created_by=request.user)
        ContentVersion.objects.create(
            draft=draft,
            business=business,
            version_number=1,
            title=draft.title,
            caption=draft.caption,
            changed_by=request.user,
            change_summary="Initial draft",
        )
        return Response({"success": True, "data": ContentDraftSerializer(draft).data}, status=status.HTTP_201_CREATED)


class DraftDetailView(APIView):
    @extend_schema(operation_id="planner_draft_detail", responses={200: ContentDraftSerializer, 404: None})
    def get(self, request, draft_id):
        business = get_owned_business(request.user)
        draft = ContentDraft.objects.filter(id=draft_id, business=business).first()
        if not draft:
            return Response({"success": False, "message": "Draft not found"}, status=404)
        return Response({"success": True, "data": ContentDraftSerializer(draft).data})

    @extend_schema(operation_id="planner_draft_update", request=ContentDraftSerializer, responses={200: ContentDraftSerializer, 404: None})
    def put(self, request, draft_id):
        business = get_owned_business(request.user)
        draft = ContentDraft.objects.filter(id=draft_id, business=business).first()
        if not draft:
            return Response({"success": False, "message": "Draft not found"}, status=404)
        if not can_write_content(request.user, business):
            raise PermissionDenied("Not allowed to update content")
        serializer = ContentDraftSerializer(draft, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        draft = serializer.save()
        version = draft.versions.count() + 1
        ContentVersion.objects.create(
            draft=draft, business=business, version_number=version, title=draft.title,
            caption=draft.caption, changed_by=request.user, change_summary=request.data.get("changeSummary", "Updated draft"),
        )
        return Response({"success": True, "data": ContentDraftSerializer(draft).data})


class DraftActionView(APIView):
    @extend_schema(operation_id="planner_draft_action", request=None, responses={200: ContentDraftSerializer})
    def post(self, request, draft_id, action):
        business = get_owned_business(request.user)
        draft = ContentDraft.objects.filter(id=draft_id, business=business).first()
        if not draft:
            return Response({"success": False, "message": "Draft not found"}, status=404)
        if action == "request-review":
            draft.status = ContentDraft.Status.IN_REVIEW
            draft.approval_status = "review_requested"
        elif action == "request-changes":
            draft.status = ContentDraft.Status.CHANGES_REQUESTED
            draft.approval_status = "changes_requested"
        elif action == "approve":
            if not can_approve_content(request.user, business):
                raise PermissionDenied("Not allowed to approve content")
            draft.status = ContentDraft.Status.APPROVED
            draft.approval_status = "approved"
        elif action == "schedule":
            if draft.status != ContentDraft.Status.APPROVED:
                return Response({"success": False, "message": "Only approved content can be scheduled"}, status=422)
            draft.status = ContentDraft.Status.SCHEDULED
            draft.scheduled_at = parse_datetime(request.data.get("scheduledAt")) if request.data.get("scheduledAt") else draft.scheduled_at
        else:
            return Response({"success": False, "message": "Unsupported action"}, status=400)
        draft.save()
        Notification.objects.create(
            business=business, user=request.user, notification_type=Notification.Type.APPROVAL,
            title="Content workflow updated", message=f"{draft.title} is now {draft.status}.",
        )
        return Response({"success": True, "data": ContentDraftSerializer(draft).data})


class DraftVersionsView(APIView):
    def get(self, request, draft_id):
        business = get_owned_business(request.user)
        draft = ContentDraft.objects.filter(id=draft_id, business=business).first()
        if not draft:
            return Response({"success": False, "message": "Draft not found"}, status=404)
        return Response({"success": True, "data": ContentVersionSerializer(draft.versions.order_by("-version_number"), many=True).data})


class DraftCommentsView(APIView):
    def post(self, request, draft_id):
        business = get_owned_business(request.user)
        draft = ContentDraft.objects.filter(id=draft_id, business=business).first()
        if not draft:
            return Response({"success": False, "message": "Draft not found"}, status=404)
        comment = ReviewComment.objects.create(
            draft=draft, business=business, user=request.user,
            comment=request.data.get("comment", ""), mentions=request.data.get("mentions", []),
        )
        return Response({"success": True, "data": ReviewCommentSerializer(comment).data}, status=status.HTTP_201_CREATED)
