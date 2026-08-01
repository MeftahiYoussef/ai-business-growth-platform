import json

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.exceptions import AIIdempotencyConflictError
from apps.analytics.views import AnalyticsSummaryView
from apps.notifications.models import Notification
from common.models import BackgroundJob
from common.utilities.access import accessible_businesses, get_owned_business

from .models import Report
from .serializers import (
    ReportJobStatusSerializer,
    ReportQueueRequestSerializer,
    ReportQueueResponseSerializer,
    ReportSerializer,
)
from .services import export_report_csv, submit_business_report_job, validate_report_request


class ReportView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        try:
            page = max(int(request.query_params.get("page", 1)), 1)
            limit = min(max(int(request.query_params.get("limit", 50)), 1), 100)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"pagination": ["Page and limit must be integers"]}) from exc
        reports = Report.objects.filter(business=business).order_by("-created_at")
        total = reports.count()
        start = (page - 1) * limit
        end = start + limit
        return Response({
            "success": True,
            "data": ReportSerializer(reports[start:end], many=True).data,
            "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit},
        })

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


def _job_status_payload(job: BackgroundJob) -> dict:
    report = getattr(job, "report", None)
    result_available = job.status == BackgroundJob.Status.COMPLETED and report is not None
    payload = {
        "success": True,
        "job_id": str(job.id),
        "status": job.status,
        "progress": job.progress,
        "progress_label": job.progress_label,
        "attempt_count": job.attempt_count,
        "report_id": str(report.id) if report else None,
        "created_at": job.created_at.isoformat().replace("+00:00", "Z"),
        "queued_at": job.queued_at.isoformat().replace("+00:00", "Z") if job.queued_at else None,
        "started_at": job.started_at.isoformat().replace("+00:00", "Z") if job.started_at else None,
        "completed_at": job.completed_at.isoformat().replace("+00:00", "Z") if job.completed_at else None,
        "failed_at": job.failed_at.isoformat().replace("+00:00", "Z") if job.failed_at else None,
        "error": None,
        "result_available": result_available,
    }
    if job.status == BackgroundJob.Status.FAILED:
        payload["error"] = {"code": job.error_code or "report_generation_failed", "message": job.error_message or "Report generation failed"}
    if result_available:
        payload["report"] = ReportSerializer(report).data
    return payload


class ReportQueueView(APIView):
    @extend_schema(
        request=ReportQueueRequestSerializer,
        responses={202: ReportQueueResponseSerializer, 409: None},
        operation_id="report_queue",
    )
    def post(self, request):
        if not settings.ASYNC_REPORTS_ENABLED and not settings.CELERY_TASK_ALWAYS_EAGER:
            return Response({"success": False, "message": "Asynchronous report generation is not enabled"}, status=503)
        serializer = ReportQueueRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            validate_report_request(
                report_type=data["report_type"],
                period_start=data["period_start"],
                period_end=data["period_end"],
            )
            job = submit_business_report_job(
                user=request.user,
                business_id=data["business_id"],
                report_type=data["report_type"],
                period_start=data["period_start"],
                period_end=data["period_end"],
                include_ai_recommendations=data.get("include_ai_recommendations", False),
                idempotency_key=request.headers.get("Idempotency-Key"),
            )
        except AIIdempotencyConflictError as exc:
            return Response({"success": False, "message": str(exc)}, status=409)
        return Response(
            {
                "success": True,
                "job_id": str(job.id),
                "status": job.status,
                "status_url": f"/api/reports/jobs/{job.id}/status/",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ReportJobStatusView(APIView):
    @extend_schema(responses={200: ReportJobStatusSerializer, 404: None}, operation_id="report_job_status")
    def get(self, request, job_id):
        job = BackgroundJob.objects.filter(
            id=job_id,
            job_type=BackgroundJob.JobType.BUSINESS_REPORT,
            business__in=accessible_businesses(request.user),
        ).select_related("business", "user").first()
        if not job:
            return Response({"success": False, "message": "Report job not found"}, status=404)
        return Response(_job_status_payload(job))


class ReportDetailView(APIView):
    @extend_schema(responses={200: ReportSerializer, 404: None}, operation_id="report_detail")
    def get(self, request, report_id):
        report = Report.objects.filter(id=report_id, business__in=accessible_businesses(request.user)).select_related("business", "job").first()
        if not report:
            return Response({"success": False, "message": "Report not found"}, status=404)
        return Response({"success": True, "data": ReportSerializer(report).data})


class ReportExportView(APIView):
    @extend_schema(responses={200: None, 404: None}, operation_id="report_export")
    def get(self, request, report_id, export_format):
        report = Report.objects.filter(id=report_id, business__in=accessible_businesses(request.user)).first()
        if not report:
            return Response({"success": False, "message": "Report not found"}, status=404)
        safe_name = f"business-report-{report.id}"
        if export_format == "json":
            response = HttpResponse(json.dumps(report.structured_content or report.summary, ensure_ascii=True), content_type="application/json")
            response["Content-Disposition"] = f'attachment; filename="{safe_name}.json"'
            return response
        if export_format == "csv":
            response = HttpResponse(export_report_csv(report), content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{safe_name}.csv"'
            return response
        raise ValidationError({"format": ["Unsupported export format"]})
