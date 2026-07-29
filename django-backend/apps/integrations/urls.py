from django.urls import path

from .views import SocialAccountsView, SocialConnectionView, SocialPostsView, SocialSyncView

urlpatterns = [
    path("connections", SocialConnectionView.as_view()),
    path("connections/<str:connection_id>/sync", SocialSyncView.as_view()),
    path("accounts", SocialAccountsView.as_view()),
    path("posts", SocialPostsView.as_view()),
]
