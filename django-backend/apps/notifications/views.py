from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utilities.access import get_owned_business

from .models import Notification, NotificationPreference
from .serializers import NotificationPreferenceSerializer, NotificationSerializer


class NotificationView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        rows = Notification.objects.filter(business=business, user=request.user).order_by("-created_at")[:100]
        return Response({"success": True, "data": NotificationSerializer(rows, many=True).data})


class NotificationReadView(APIView):
    def post(self, request, notification_id):
        business = get_owned_business(request.user)
        notification = Notification.objects.filter(id=notification_id, business=business, user=request.user).first()
        if not notification:
            return Response({"success": False, "message": "Notification not found"}, status=404)
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
        return Response({"success": True, "data": NotificationSerializer(notification).data})


class NotificationPreferenceView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        pref, _ = NotificationPreference.objects.get_or_create(business=business, user=request.user)
        return Response({"success": True, "data": NotificationPreferenceSerializer(pref).data})

    def put(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        pref, _ = NotificationPreference.objects.get_or_create(business=business, user=request.user)
        serializer = NotificationPreferenceSerializer(pref, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": NotificationPreferenceSerializer(pref).data})
