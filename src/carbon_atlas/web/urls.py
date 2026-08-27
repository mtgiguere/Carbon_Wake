"""URL routes for the read-only v1 API."""

from django.urls import path

from carbon_atlas.api.views import (
    PresetCatalogView,
    RunCellsView,
    RunEstimateView,
    RunListView,
    RunTilesView,
)

urlpatterns = [
    path("api/presets/", PresetCatalogView.as_view()),
    path("api/runs/", RunListView.as_view()),
    path("api/runs/<int:run_id>/cells/", RunCellsView.as_view()),
    path("api/runs/<int:run_id>/estimate/", RunEstimateView.as_view()),
    path("api/runs/<int:run_id>/tiles/<int:z>/<int:x>/<int:y>.mvt", RunTilesView.as_view()),
]
