from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.views import AnalyticsSummaryView
from apps.notifications.models import Notification
from common.utilities.access import get_owned_business

from .models import Report
from .serializers import ReportSerializer


class ReportView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        reports = Report.objects.filter(business=business).order_by("-created_at")
        return Response({"success": True, "data": ReportSerializer(reports, many=True).data})

    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        summary_response = AnalyticsSummaryView().get(request)
        report = Report.objects.create(
            business=business,
            title=request.data.get("title") or f"Executive summary {timezone.now().date()}",
            report_type=request.data.get("reportType") or Report.ReportType.EXECUTIVE,
            filters=request.data.get("filters") or {},
            summary=summary_response.data.get("data", {}),
            created_by=request.user,
        )
        Notification.objects.create(
            business=business, user=request.user, notification_type=Notification.Type.REPORT_READY,
            title="Report ready", message=f"{report.title} is ready to review.",
        )
        return Response({"success": True, "data": ReportSerializer(report).data}, status=status.HTTP_201_CREATED)
