"""DRF views for the read-only v1 API, plus the map page."""

from dataclasses import asdict

import psycopg
from django.db import connection
from django.http import HttpResponse
from django.views.generic import TemplateView
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from carbon_atlas.anchors import AnchorCount, anchor_counts
from carbon_atlas.db.store import (
    ZONE_RING_M,
    ZoneMeasurement,
    cells_tile_mvt,
    get_run,
    latest_footprint_summary,
    list_runs,
    list_wind_farm_zones,
    load_overlap,
    load_zone_contrast,
    overlap_intersecting,
    trawled_cells_intersecting,
)
from carbon_atlas.disturbance import gear_profiles_for_year
from carbon_atlas.effort.gears import EFFORT_LAYER_LABEL
from carbon_atlas.effort.grid import BoundingBox
from carbon_atlas.estimates import (
    ESTIMATE_CAVEATS,
    CO2Quantity,
    area_estimate_caveats,
    disturbed_from_cells,
    estimate_region_co2,
)
from carbon_atlas.footprint import FOOTPRINT_CAVEATS, FOOTPRINT_METHOD, FootprintBracket
from carbon_atlas.overlap import TrawledCell
from carbon_atlas.reactivity.presets import PUBLISHED_PRESETS
from carbon_atlas.zones import EMODNET_WINDFARMS_SOURCE, ZONE_CAVEATS, zone_contrast


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


def _anchor_payload(counted: AnchorCount) -> dict:
    """An anchored count with its anchor's citation and comparability basis
    on the same object — an anchored number is never a bare number."""
    return {
        "key": counted.anchor.key,
        "unit_label": counted.anchor.unit_label,
        "mean_units": counted.mean_units,
        "uncertainty_units": counted.uncertainty_units,
        "citation": counted.anchor.citation,
        "basis": counted.anchor.basis,
    }


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

        profiles = gear_profiles_for_year(run.effort_year)
        # An optional bbox scopes the estimate to the visitor's own box
        # (IDEAS.md #1): same pure chain, over the cells the box intersects,
        # with the box's own coverage disclosure and caveats.
        bbox = _parse_bbox(request) if "bbox" in request.query_params else None
        if bbox is None:
            result = load_overlap(conn, run_id)
            coverage = {
                "cells_mapped": run.cells_mapped,
                "cells_unmapped": run.cells_unmapped,
                "fishing_hours_mapped": run.fishing_hours_mapped,
                "fishing_hours_unmapped": run.fishing_hours_unmapped,
            }
            caveats = list(ESTIMATE_CAVEATS)
        else:
            result = overlap_intersecting(
                conn,
                run_id,
                lat_min=bbox.lat_min,
                lat_max=bbox.lat_max,
                lon_min=bbox.lon_min,
                lon_max=bbox.lon_max,
            )
            coverage = {
                "cells_mapped": len(result.trawled),
                "cells_unmapped": len(result.unmapped_effort),
                "fishing_hours_mapped": result.trawled_fishing_hours,
                "fishing_hours_unmapped": result.unmapped_fishing_hours,
            }
            caveats = list(area_estimate_caveats(cells_mapped=len(result.trawled)))
        disturbed = disturbed_from_cells(result.trawled, profiles)
        region = estimate_region_co2(disturbed, PUBLISHED_PRESETS)

        payload = {
            "run_id": run.id,
            "effort_year": run.effort_year,
            "effort_layer_label": run.effort_layer_label,
            "effort_coverage": coverage,
            "disturbed_carbon": {
                "mean_kg": disturbed.mean_kg,
                "uncertainty_kg": disturbed.uncertainty_kg,
            },
            "gear_profiles": [asdict(profile) for _, profile in sorted(profiles.items())],
            "estimates": [
                {
                    "preset": asdict(entry.preset),
                    "aqueous_co2": _co2_payload(entry.aqueous),
                    "atmospheric_co2": _co2_payload(entry.atmospheric),
                    "anchors": [
                        _anchor_payload(counted) for counted in anchor_counts(entry.aqueous)
                    ],
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
            "caveats": caveats,
        }
        if bbox is not None:
            payload["area"] = {
                "bbox": {
                    "lon_min": bbox.lon_min,
                    "lat_min": bbox.lat_min,
                    "lon_max": bbox.lon_max,
                    "lat_max": bbox.lat_max,
                },
                **coverage,
            }
        return Response(payload)


class RunTilesView(APIView):
    """A run's cells as one Mapbox Vector Tile (ADR-0015).

    Wiring only: PostGIS builds the tile in the tested store layer. Tile
    coordinates that name no real slippy tile are refused with a 400, never
    clamped onto one.
    """

    def get(self, request: Request, run_id: int, z: int, x: int, y: int) -> Response:
        if z > 22 or x >= 2**z or y >= 2**z:
            raise ParseError(f"no such tile: z={z}, x={x}, y={y} (0 <= x,y < 2^z, z <= 22)")
        conn = _store_connection()
        try:
            get_run(conn, run_id)
        except KeyError as exc:
            raise NotFound(str(exc)) from exc
        tile = cells_tile_mvt(conn, run_id, z=z, x=x, y=y)
        return HttpResponse(tile, content_type="application/vnd.mapbox-vector-tile")


def _bracket_payload(bracket: FootprintBracket) -> dict:
    return {
        "lower_m2": bracket.lower_m2,
        "poisson_m2": bracket.poisson_m2,
        "upper_m2": bracket.upper_m2,
    }


class FootprintView(APIView):
    """The cumulative trawling footprint (ADR-0017): the newest stored summary
    as a bracket — floor, Poisson union, ceiling — in area and as fractions of
    the carbon-mapped seabed, with the runs and years it rests on, the cited
    method and its published comparator, and the caveats naming both
    directions of bias. Nothing computed yet is a 404, never a zero.
    """

    def get(self, request: Request) -> Response:
        record = latest_footprint_summary(_store_connection())
        if record is None:
            raise NotFound("no cumulative footprint has been computed for this database yet")
        fractions = record.fractions
        return Response(
            {
                "summary_id": record.id,
                "computed_at": record.computed_at,
                "years": list(record.years),
                "run_ids": list(record.run_ids),
                "cells": record.cells,
                "mapped_seabed_area_m2": record.mapped_seabed_area_m2,
                "mapped_seabed": {
                    **_bracket_payload(record.mapped),
                    "fraction": {
                        "lower": fractions.lower,
                        "poisson": fractions.poisson,
                        "upper": fractions.upper,
                    },
                },
                "all_effort": _bracket_payload(record.all_effort),
                "per_year_mapped_m2": {
                    str(year): area for year, area in sorted(record.per_year_mapped_m2.items())
                },
                "per_year_mapped_fraction": {
                    str(year): fraction for year, fraction in fractions.per_year.items()
                },
                "method": dict(FOOTPRINT_METHOD),
                "caveats": list(FOOTPRINT_CAVEATS),
            }
        )


class WindFarmZonesView(APIView):
    """The reference zones (ADR-0018) as GeoJSON: every stored offshore wind
    farm in production or under construction, with EMODnet's facts, its
    source, and the license, per feature. No zones is an empty collection."""

    def get(self, request: Request) -> Response:
        zones = list_wind_farm_zones(_store_connection())
        return Response(
            {
                "type": "FeatureCollection",
                "kind": "offshore wind farms in production or under construction",
                "license": "CC-BY 4.0 (EMODnet Human Activities)",
                "count": len(zones),
                "features": [
                    {
                        "type": "Feature",
                        "id": zone.id,
                        "geometry": zone.geometry,
                        "properties": {
                            "name": zone.name,
                            "country": zone.country,
                            "status": zone.status,
                            "commissioned_year": zone.commissioned_year,
                            "power_mw": zone.power_mw,
                            "turbines": zone.turbines,
                            "area_km2": zone.area_km2,
                            "source": zone.source,
                        },
                    }
                    for zone in zones
                ],
            }
        )


def _contrast_payload(m: ZoneMeasurement) -> dict:
    """One measurement with its densities and ratio from the pure layer — or
    without them when nothing was measurable (only year-unknown farms)."""
    payload = {
        "country": m.country,
        "farms": m.farms,
        "farms_without_year": m.farms_without_year,
        "farm_km2": m.farm_km2,
        "inside_hours": m.inside_hours,
        "ring_km2": m.ring_km2,
        "ring_hours": m.ring_hours,
        "inside_density": None,
        "ring_density": None,
        "ratio": None,
    }
    if m.farm_km2 > 0.0 and m.ring_km2 > 0.0:
        contrast = zone_contrast(
            farm_km2=m.farm_km2,
            inside_hours=m.inside_hours,
            ring_km2=m.ring_km2,
            ring_hours=m.ring_hours,
        )
        payload.update(
            inside_density=contrast.inside_density,
            ring_density=contrast.ring_density,
            ratio=contrast.ratio,
        )
    return payload


class RunZoneContrastView(APIView):
    """A run's trawl density inside wind farms versus their 5 km rings, per
    country and in total (ADR-0018), with the cutoff year, the count of farms
    that could not be measured, the source, and the caveats. Not measured
    yet is a 404, never a zero."""

    def get(self, request: Request, run_id: int) -> Response:
        conn = _store_connection()
        try:
            run = get_run(conn, run_id)
        except KeyError as exc:
            raise NotFound(str(exc)) from exc
        record = load_zone_contrast(conn, run_id)
        if record is None:
            raise NotFound(f"no zone contrast has been measured for run {run_id} yet")
        total = ZoneMeasurement(
            country="all",
            farms=sum(m.farms for m in record.rows),
            farms_without_year=sum(m.farms_without_year for m in record.rows),
            farm_km2=sum(m.farm_km2 for m in record.rows),
            inside_hours=sum(m.inside_hours for m in record.rows),
            ring_km2=sum(m.ring_km2 for m in record.rows),
            ring_hours=sum(m.ring_hours for m in record.rows),
        )
        return Response(
            {
                "run_id": run.id,
                "effort_year": run.effort_year,
                "cutoff_year": record.cutoff_year,
                "computed_at": record.computed_at,
                "ring_width_m": ZONE_RING_M,
                "countries": [_contrast_payload(m) for m in record.rows],
                "total": _contrast_payload(total),
                "source": EMODNET_WINDFARMS_SOURCE,
                "caveats": list(ZONE_CAVEATS),
            }
        )


class AtlasPageView(TemplateView):
    """The map page (ADR-0015). The template carries the honesty text — the
    ADR-0009 label verbatim and the full attribution stack — and atlas.js
    renders the newest run's tiles under the visual-honesty policy."""

    template_name = "atlas.html"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["effort_layer_label"] = EFFORT_LAYER_LABEL
        return context
