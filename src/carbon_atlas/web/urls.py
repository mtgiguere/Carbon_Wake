"""URL routes for the read-only v1 API."""

from django.urls import path

from carbon_atlas.api.views import PresetCatalogView, RunListView

urlpatterns = [
    path("api/presets/", PresetCatalogView.as_view()),
    path("api/runs/", RunListView.as_view()),
]
