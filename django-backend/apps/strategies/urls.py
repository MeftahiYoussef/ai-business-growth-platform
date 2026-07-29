from django.urls import path

from .views import GenerateStrategyView, StrategyView

urlpatterns = [
    path("", StrategyView.as_view()),
    path("generate", GenerateStrategyView.as_view()),
]
