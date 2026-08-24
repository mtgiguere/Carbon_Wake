"""URL routes for the read-only v1 API."""

from django.urls import path

from carbon_atlas.api.views import PresetCatalogView, RunCellsView, RunListView

urlpatterns = [
    path("api/presets/", PresetCatalogView.as_view()),
    path("api/runs/", RunListView.as_view()),
    path("api/runs/<int:run_id>/cells/", RunCellsView.as_view()),
]
