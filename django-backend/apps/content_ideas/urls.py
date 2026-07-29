from django.urls import path

from .views import ContentIdeasView, DeleteContentIdeaView, GenerateContentIdeasView, SaveContentIdeaView

urlpatterns = [
    path("", ContentIdeasView.as_view()),
    path("generate", GenerateContentIdeasView.as_view()),
    path("<str:idea_id>/save", SaveContentIdeaView.as_view()),
    path("<str:idea_id>", DeleteContentIdeaView.as_view()),
]
