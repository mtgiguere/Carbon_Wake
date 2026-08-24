"""DRF views for the read-only v1 API."""

from dataclasses import asdict

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from carbon_atlas.reactivity.presets import PUBLISHED_PRESETS


class PresetCatalogView(APIView):
    """The published reactivity presets, verbatim from the pure core.

    Faithful transport of the catalog and its honesty invariants: a derived
    fraction ships with its derivation note, an unquantified atmospheric
    fraction ships as null. No CO2 figures — none exist to serve (ADR-0011).
    """

    def get(self, request: Request) -> Response:
        return Response({"presets": [asdict(preset) for preset in PUBLISHED_PRESETS]})
