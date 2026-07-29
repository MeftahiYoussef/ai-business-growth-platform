from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utilities.access import get_owned_business

from .models import ActivityLog, BusinessMember, TeamInvitation
from .permissions import can_manage_team
from .serializers import ActivityLogSerializer, BusinessMemberSerializer, TeamInvitationSerializer


class TeamView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        return Response({"success": True, "data": BusinessMemberSerializer(business.memberships.select_related("user"), many=True).data})


class TeamInviteView(APIView):
    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        if not can_manage_team(request.user, business):
            raise PermissionDenied("Only owners and admins can invite team members")
        invitation = TeamInvitation.objects.create(
            business=business,
            email=request.data.get("email", "").lower(),
            role=request.data.get("role") or BusinessMember.Role.VIEWER,
            invited_by=request.user,
        )
        ActivityLog.objects.create(business=business, user=request.user, action="team.invited", entity_type="TeamInvitation", entity_id=str(invitation.id))
        return Response({"success": True, "data": TeamInvitationSerializer(invitation).data}, status=status.HTTP_201_CREATED)


class TeamInvitationRespondView(APIView):
    def post(self, request, token):
        invitation = TeamInvitation.objects.filter(token=token, email=request.user.email, status=TeamInvitation.Status.PENDING).first()
        if not invitation:
            return Response({"success": False, "message": "Invitation not found"}, status=404)
        accept = request.data.get("accept", True)
        invitation.status = TeamInvitation.Status.ACCEPTED if accept else TeamInvitation.Status.REJECTED
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=["status", "responded_at"])
        if accept:
            BusinessMember.objects.get_or_create(business=invitation.business, user=request.user, defaults={"role": invitation.role})
        return Response({"success": True, "data": TeamInvitationSerializer(invitation).data})


class TeamMemberDetailView(APIView):
    def put(self, request, member_id):
        member = BusinessMember.objects.select_related("business").filter(id=member_id).first()
        if not member or not can_manage_team(request.user, member.business):
            raise PermissionDenied("Not allowed to update this team member")
        member.role = request.data.get("role", member.role)
        member.save(update_fields=["role"])
        return Response({"success": True, "data": BusinessMemberSerializer(member).data})

    def delete(self, request, member_id):
        member = BusinessMember.objects.select_related("business").filter(id=member_id).first()
        if not member or not can_manage_team(request.user, member.business):
            raise PermissionDenied("Not allowed to remove this team member")
        member.delete()
        return Response({"success": True, "data": {"id": member_id}})


class ActivityView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        logs = ActivityLog.objects.filter(business=business).select_related("user").order_by("-created_at")[:50]
        return Response({"success": True, "data": ActivityLogSerializer(logs, many=True).data})


def user_by_email(email):
    return get_user_model().objects.filter(email=email.lower()).first()
