from django.urls import path

from .views import NotificationPreferenceView, NotificationReadView, NotificationView

urlpatterns = [
    path("", NotificationView.as_view()),
    path("<str:notification_id>/read", NotificationReadView.as_view()),
    path("<str:notification_id>/read/", NotificationReadView.as_view()),
    path("preferences", NotificationPreferenceView.as_view()),
]
