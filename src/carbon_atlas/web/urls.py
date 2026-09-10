"""URL routes for the read-only v1 API."""

from django.urls import path

from carbon_atlas.api.views import (
    AtlasPageView,
    FootprintView,
    PresetCatalogView,
    RunCellsView,
    RunEstimateView,
    RunListView,
    RunTilesView,
    RunZoneContrastView,
    WindFarmZonesView,
)

urlpatterns = [
    path("", AtlasPageView.as_view()),
    path("api/presets/", PresetCatalogView.as_view()),
    path("api/runs/", RunListView.as_view()),
    path("api/runs/<int:run_id>/cells/", RunCellsView.as_view()),
    path("api/runs/<int:run_id>/estimate/", RunEstimateView.as_view()),
    path("api/runs/<int:run_id>/tiles/<int:z>/<int:x>/<int:y>.mvt", RunTilesView.as_view()),
    path("api/footprint/", FootprintView.as_view()),
    path("api/zones/wind-farms/", WindFarmZonesView.as_view()),
    path("api/runs/<int:run_id>/zone-contrast/", RunZoneContrastView.as_view()),
]
