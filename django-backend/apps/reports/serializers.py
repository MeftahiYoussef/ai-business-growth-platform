from rest_framework import serializers

from common.serializers import dt
from common.utilities.ids import external_id

from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    reportType = serializers.CharField(source="report_type")
    dateRangeStart = serializers.DateField(source="date_range_start", required=False, allow_null=True)
    dateRangeEnd = serializers.DateField(source="date_range_end", required=False, allow_null=True)
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ["_id", "businessId", "title", "reportType", "dateRangeStart", "dateRangeEnd", "filters", "status", "summary", "createdAt"]

    def get__id(self, obj):
        return str(obj.id)

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_createdAt(self, obj):
        return dt(obj.created_at)
