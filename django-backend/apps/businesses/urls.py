from django.urls import path

from .views import BusinessCollectionView, BusinessDetailView, MyBusinessView

urlpatterns = [
    path("", BusinessCollectionView.as_view()),
    path("me", MyBusinessView.as_view()),
    path("<str:business_id>", BusinessDetailView.as_view()),
]
