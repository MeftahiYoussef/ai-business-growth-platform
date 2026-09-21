from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view

from .views import ContentIdeasView, DeleteContentIdeaView, GenerateContentIdeasView, SaveContentIdeaView


@extend_schema_view(post=extend_schema(exclude=True))
class GenerateContentIdeasAliasView(GenerateContentIdeasView):
    pass


@extend_schema_view(put=extend_schema(exclude=True))
class SaveContentIdeaAliasView(SaveContentIdeaView):
    pass


@extend_schema_view(delete=extend_schema(exclude=True))
class DeleteContentIdeaAliasView(DeleteContentIdeaView):
    pass


urlpatterns = [
    path("", ContentIdeasView.as_view()),
    path("generate", GenerateContentIdeasView.as_view()),
    path("generate/", GenerateContentIdeasAliasView.as_view()),
    path("<str:idea_id>/save", SaveContentIdeaView.as_view()),
    path("<str:idea_id>/save/", SaveContentIdeaAliasView.as_view()),
    path("<str:idea_id>", DeleteContentIdeaView.as_view()),
    path("<str:idea_id>/", DeleteContentIdeaAliasView.as_view()),
]
