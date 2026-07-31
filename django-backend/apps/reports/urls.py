from django.urls import path

from .views import ReportDetailView, ReportExportView, ReportJobStatusView, ReportQueueView, ReportView

urlpatterns = [
    path("", ReportView.as_view()),
    path("queue/", ReportQueueView.as_view()),
    path("jobs/<uuid:job_id>/status/", ReportJobStatusView.as_view()),
    path("<uuid:report_id>/", ReportDetailView.as_view()),
    path("<uuid:report_id>/export.<str:export_format>/", ReportExportView.as_view()),
]
