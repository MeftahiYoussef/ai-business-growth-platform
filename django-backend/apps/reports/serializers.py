from rest_framework import serializers

from common.models import BackgroundJob
from common.serializers import dt
from common.utilities.ids import external_id

from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    reportType = serializers.CharField(source="report_type")
    jobId = serializers.SerializerMethodField()
    dateRangeStart = serializers.DateField(source="date_range_start", required=False, allow_null=True)
    dateRangeEnd = serializers.DateField(source="date_range_end", required=False, allow_null=True)
    structuredContent = serializers.JSONField(source="structured_content", required=False)
    createdAt = serializers.SerializerMethodField()
    updatedAt = serializers.SerializerMethodField()
    generatedAt = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "_id", "businessId", "jobId", "title", "reportType", "dateRangeStart", "dateRangeEnd", "filters",
            "status", "summary", "structuredContent", "provider", "model", "usage", "generatedAt", "createdAt", "updatedAt",
        ]

    def get__id(self, obj: Report) -> str:
        return str(obj.id)

    def get_businessId(self, obj: Report) -> str:
        return external_id(obj.business)

    def get_jobId(self, obj: Report) -> str | None:
        return str(obj.job_id) if obj.job_id else None

    def get_createdAt(self, obj: Report) -> str | None:
        return dt(obj.created_at)

    def get_updatedAt(self, obj: Report) -> str | None:
        return dt(obj.updated_at)

    def get_generatedAt(self, obj: Report) -> str | None:
        return dt(obj.generated_at)


class ReportQueueRequestSerializer(serializers.Serializer):
    business_id = serializers.CharField(required=False, allow_blank=True)
    businessId = serializers.CharField(required=False, allow_blank=True)
    report_type = serializers.ChoiceField(choices=[Report.ReportType.BUSINESS_PERFORMANCE], required=False)
    reportType = serializers.ChoiceField(choices=[Report.ReportType.BUSINESS_PERFORMANCE], required=False)
    period_start = serializers.DateField(required=False)
    periodStart = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)
    periodEnd = serializers.DateField(required=False)
    include_ai_recommendations = serializers.BooleanField(required=False, default=False)
    includeAiRecommendations = serializers.BooleanField(required=False)

    def validate(self, attrs):
        attrs["business_id"] = attrs.get("business_id") or attrs.get("businessId")
        attrs["report_type"] = attrs.get("report_type") or attrs.get("reportType") or Report.ReportType.BUSINESS_PERFORMANCE
        attrs["period_start"] = attrs.get("period_start") or attrs.get("periodStart")
        attrs["period_end"] = attrs.get("period_end") or attrs.get("periodEnd")
        if attrs.get("includeAiRecommendations") is not None:
            attrs["include_ai_recommendations"] = attrs["includeAiRecommendations"]
        if not attrs.get("business_id"):
            raise serializers.ValidationError({"business_id": ["This field is required"]})
        if not attrs.get("period_start"):
            raise serializers.ValidationError({"period_start": ["This field is required"]})
        if not attrs.get("period_end"):
            raise serializers.ValidationError({"period_end": ["This field is required"]})
        return attrs


class ReportQueueResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    job_id = serializers.CharField()
    status = serializers.CharField()
    status_url = serializers.CharField()


class ReportJobStatusSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    job_id = serializers.CharField()
    status = serializers.CharField()
    progress = serializers.IntegerField()
    progress_label = serializers.CharField()
    attempt_count = serializers.IntegerField()
    report_id = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    queued_at = serializers.DateTimeField(allow_null=True)
    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    failed_at = serializers.DateTimeField(allow_null=True)
    error = serializers.JSONField(allow_null=True)
    result_available = serializers.BooleanField()
    report = ReportSerializer(required=False)


class BackgroundJobSerializer(serializers.ModelSerializer):
    businessId = serializers.SerializerMethodField()
    userId = serializers.SerializerMethodField()
    jobType = serializers.CharField(source="job_type")
    progressLabel = serializers.CharField(source="progress_label")
    attemptCount = serializers.IntegerField(source="attempt_count")
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = BackgroundJob
        fields = ["id", "businessId", "userId", "jobType", "status", "progress", "progressLabel", "attemptCount", "createdAt"]

    def get_businessId(self, obj: BackgroundJob) -> str:
        return external_id(obj.business)

    def get_userId(self, obj: BackgroundJob) -> str | None:
        return external_id(obj.user) if obj.user else None

    def get_createdAt(self, obj: BackgroundJob) -> str | None:
        return dt(obj.created_at)
