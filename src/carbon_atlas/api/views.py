"""DRF views for the read-only v1 API."""

from dataclasses import asdict

import psycopg
from django.db import connection
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from carbon_atlas.db.store import get_run, list_runs, trawled_cells_intersecting
from carbon_atlas.effort.grid import BoundingBox
from carbon_atlas.overlap import TrawledCell
from carbon_atlas.reactivity.presets import PUBLISHED_PRESETS


def _store_connection() -> psycopg.Connection:
    """The raw psycopg connection under Django's — what the store functions
    speak (ADR-0011: views call the tested store, never an ORM)."""
    connection.ensure_connection()
    return connection.connection


class PresetCatalogView(APIView):
    """The published reactivity presets, verbatim from the pure core.

    Faithful transport of the catalog and its honesty invariants: a derived
    fraction ships with its derivation note, an unquantified atmospheric
    fraction ships as null. No CO2 figures — none exist to serve (ADR-0011).
    """

    def get(self, request: Request) -> Response:
        return Response({"presets": [asdict(preset) for preset in PUBLISHED_PRESETS]})


class RunListView(APIView):
    """Every ETL run's provenance, newest first.

    Provenance is the honesty layer at the API: sources, the ADR-0009 label
    verbatim, and BOTH sides' totals — mapped and unmapped effort alike.
    """

    def get(self, request: Request) -> Response:
        return Response({"runs": [asdict(run) for run in list_runs(_store_connection())]})


def _parse_bbox(request: Request) -> BoundingBox:
    """The ``bbox`` query param (lon_min,lat_min,lon_max,lat_max) as a
    BoundingBox — refused with a 400, never guessed, when absent, of the
    wrong arity, non-numeric, or inverted."""
    raw = request.query_params.get("bbox")
    if raw is None:
        raise ParseError("missing required query parameter bbox=lon_min,lat_min,lon_max,lat_max")
    parts = raw.split(",")
    if len(parts) != 4:
        raise ParseError(f"bbox must be 4 comma-separated numbers; got {raw!r}")
    try:
        lon_min, lat_min, lon_max, lat_max = (float(part) for part in parts)
        return BoundingBox(lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max)
    except ValueError as exc:
        raise ParseError(f"invalid bbox {raw!r}: {exc}") from exc


def _feature(trawled: TrawledCell) -> dict:
    """One trawled cell as a GeoJSON Feature: the true cell polygon (closed
    ring on the 0.01-degree corners), hours per gear class and totalled, and
    the FULL carbon pair."""
    cell = trawled.cell
    lon0, lat0 = cell.lon_index / 100, cell.lat_index / 100
    lon1, lat1 = (cell.lon_index + 1) / 100, (cell.lat_index + 1) / 100
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]],
        },
        "properties": {
            "fishing_hours": trawled.total_fishing_hours,
            "fishing_hours_by_gear": trawled.fishing_hours_by_gear,
            "oc_density": {
                "mean": trawled.carbon.mean,
                "uncertainty": trawled.carbon.uncertainty,
            },
        },
    }


class RunCellsView(APIView):
    """A run's trawled cells intersecting a bbox, as GeoJSON."""

    def get(self, request: Request, run_id: int) -> Response:
        conn = _store_connection()
        bbox = _parse_bbox(request)
        try:
            get_run(conn, run_id)
        except KeyError as exc:
            raise NotFound(str(exc)) from exc
        cells = trawled_cells_intersecting(
            conn,
            run_id,
            lat_min=bbox.lat_min,
            lat_max=bbox.lat_max,
            lon_min=bbox.lon_min,
            lon_max=bbox.lon_max,
        )
        return Response(
            {
                "type": "FeatureCollection",
                "count": len(cells),
                "features": [_feature(cell) for cell in cells],
            }
        )
