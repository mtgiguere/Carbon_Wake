"""DRF views for the read-only v1 API."""

from dataclasses import asdict

import psycopg
from django.db import connection
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from carbon_atlas.db.store import get_run, list_runs, load_overlap, trawled_cells_intersecting
from carbon_atlas.disturbance import DEFAULT_GEAR_PROFILES
from carbon_atlas.effort.grid import BoundingBox
from carbon_atlas.estimates import (
    ESTIMATE_CAVEATS,
    CO2Quantity,
    disturbed_from_cells,
    estimate_region_co2,
)
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


def _co2_payload(quantity: CO2Quantity | None) -> dict | None:
    if quantity is None:
        return None
    return {"mean_kg": quantity.mean_kg, "uncertainty_kg": quantity.uncertainty_kg}


class RunEstimateView(APIView):
    """A run's region CO2 estimate — the headline number, served the only way
    this project allows: as a cited range with uncertainty, wrapped in its
    own provenance (coverage disclosure, gear profiles, model caveats).

    Wiring only: the store supplies the run's cells, and the pure disturbance
    + estimates modules do every piece of arithmetic — per cell, under the
    saturation bound (ADR-0014), which a linear SQL sum cannot express.
    """

    def get(self, request: Request, run_id: int) -> Response:
        conn = _store_connection()
        try:
            run = get_run(conn, run_id)
        except KeyError as exc:
            raise NotFound(str(exc)) from exc

        result = load_overlap(conn, run_id)
        disturbed = disturbed_from_cells(result.trawled, DEFAULT_GEAR_PROFILES)
        region = estimate_region_co2(disturbed, PUBLISHED_PRESETS)

        return Response(
            {
                "run_id": run.id,
                "effort_layer_label": run.effort_layer_label,
                "effort_coverage": {
                    "cells_mapped": run.cells_mapped,
                    "cells_unmapped": run.cells_unmapped,
                    "fishing_hours_mapped": run.fishing_hours_mapped,
                    "fishing_hours_unmapped": run.fishing_hours_unmapped,
                },
                "disturbed_carbon": {
                    "mean_kg": disturbed.mean_kg,
                    "uncertainty_kg": disturbed.uncertainty_kg,
                },
                "gear_profiles": [
                    asdict(profile)
                    for _, profile in sorted(DEFAULT_GEAR_PROFILES.items())
                ],
                "estimates": [
                    {
                        "preset": asdict(entry.preset),
                        "aqueous_co2": _co2_payload(entry.aqueous),
                        "atmospheric_co2": _co2_payload(entry.atmospheric),
                    }
                    for entry in region.per_preset
                ],
                "range": {
                    "low": {
                        "preset_key": region.low.preset.key,
                        "aqueous_co2": _co2_payload(region.low.aqueous),
                    },
                    "high": {
                        "preset_key": region.high.preset.key,
                        "aqueous_co2": _co2_payload(region.high.aqueous),
                    },
                },
                "caveats": list(ESTIMATE_CAVEATS),
            }
        )
