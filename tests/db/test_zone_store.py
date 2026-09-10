"""Behavioral contract for the reference-zone store (ADR-0018).

Zones are a snapshot (re-storing a source replaces it), each with its 5 km
ring precomputed in SQL so the measurement is cheap. The measurement is
PostGIS's job — hours inside a farm and in its ring, apportioned by the
intersected fraction of each cell, over the FULL zone areas — and its per-run
result is stored, like the footprint, so the API never re-measures.

Written test-first per TDD_CONTRACT.md.
"""

import json
import math
from pathlib import Path

import pytest

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.db.store import (
    list_wind_farm_zones,
    load_zone_contrast,
    measure_zone_contrast,
    store_overlap,
    store_wind_farm_zones,
    store_zone_contrast,
)
from carbon_atlas.effort.grid import BoundingBox, GridCell
from carbon_atlas.overlap import OverlapResult, TrawledCell
from carbon_atlas.zones import WindFarmZone, parse_emodnet_windfarms

pytestmark = pytest.mark.integration

_REAL = Path(__file__).parent.parent / "fixtures" / "real" / "emodnet"
_DENSITY = CarbonDensity(mean=1.5652642, uncertainty=2.4579988)


def _square(cell: GridCell) -> dict:
    """The cell's own 0.01-degree square as a GeoJSON Polygon."""
    lon0, lat0 = cell.lon_index / 100, cell.lat_index / 100
    lon1, lat1 = lon0 + 0.01, lat0 + 0.01
    return {
        "type": "Polygon",
        "coordinates": [[[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]],
    }


def _zone(name, cell, year, country="Testland", status="Production"):
    return WindFarmZone(
        name=name,
        country=country,
        status=status,
        commissioned_year=year,
        power_mw=None,
        turbines=None,
        area_km2=None,
        geometry=_square(cell),
    )


def test_zones_store_as_a_replaceable_snapshot_and_list_back_with_geojson(conn):
    collection = json.loads(
        (_REAL / "windfarms_polygons.german-bight.geojson").read_text(encoding="utf-8")
    )
    zones = parse_emodnet_windfarms(
        collection, region=BoundingBox(lat_min=49.3, lat_max=62.4, lon_min=-10.4, lon_max=13.6)
    )

    assert store_wind_farm_zones(conn, zones, source="emodnet test") == 4
    assert store_wind_farm_zones(conn, zones, source="emodnet test") == 4  # replaced, not doubled
    stored = list_wind_farm_zones(conn)

    assert len(stored) == 4
    by_name = {z.name: z for z in stored}
    nord = by_name["Nordergründe"]
    assert nord.country == "Germany"
    assert nord.status == "Production"
    assert nord.commissioned_year == 2017
    assert math.isclose(nord.area_km2, 3.42193592317)
    assert nord.source == "emodnet test"
    assert nord.geometry["type"] == "MultiPolygon"
    assert by_name["Gode Wind 01"].commissioned_year is None
    assert [z.id for z in stored] == sorted(z.id for z in stored)


def test_measurement_apportions_hours_by_intersected_area_over_full_zone_areas(conn):
    """A farm exactly covering the hotspot cell (10 h) with one neighbour cell
    (4 h) sitting wholly inside its 5 km ring: inside density = 10 h over the
    cell's true area; ring hours = 4 (the whole neighbour); ring area = the
    5 km annulus. A farm with no commissioning year is counted but not
    measured; a farm commissioned after the cutoff is ignored; a farm still
    UNDER CONSTRUCTION excludes nothing yet and is neither measured nor
    counted, whatever year it carries."""
    hotspot = GridCell(lat_index=5390, lon_index=764)
    neighbour = GridCell(lat_index=5390, lon_index=766)  # ~1.3 km east: inside the ring
    run_id = store_overlap(
        conn,
        OverlapResult(
            trawled=(
                TrawledCell(
                    cell=hotspot, fishing_hours_by_gear={"trawlers": 10.0}, carbon=_DENSITY
                ),
                TrawledCell(
                    cell=neighbour, fishing_hours_by_gear={"trawlers": 4.0}, carbon=_DENSITY
                ),
            ),
            unmapped_effort={},
        ),
        effort_source="e",
        carbon_source="c",
        effort_year=2024,
    )
    store_wind_farm_zones(
        conn,
        [
            _zone("measured", hotspot, 2010),
            _zone("year unknown", GridCell(lat_index=5400, lon_index=800), None),
            _zone("too new", GridCell(lat_index=5410, lon_index=810), 2024),
            _zone("elsewhere", GridCell(lat_index=5500, lon_index=900), 2005, country="Farland"),
            _zone("building", GridCell(lat_index=5420, lon_index=820), 2010, status="Construction"),
        ],
        source="synthetic",
    )

    rows = measure_zone_contrast(conn, run_id, cutoff_year=2023)

    by_country = {row.country: row for row in rows}
    assert set(by_country) == {"Testland", "Farland"}
    t = by_country["Testland"]
    assert t.farms == 1
    assert t.farms_without_year == 1
    # PostGIS measures on the WGS84 ellipsoid; GridCell.area_m2 is spherical
    # (R = 6371 km): they agree to ~0.4 %, never exactly.
    assert math.isclose(t.farm_km2, hotspot.area_m2 / 1e6, rel_tol=1e-2)
    assert math.isclose(t.inside_hours, 10.0, rel_tol=1e-6)
    assert math.isclose(t.ring_hours, 4.0, rel_tol=1e-6)
    annulus_km2 = math.pi * (5.0 + 0.4) ** 2 - t.farm_km2  # order of magnitude: ~90 km2
    assert 0.7 * annulus_km2 < t.ring_km2 < 1.3 * annulus_km2
    f = by_country["Farland"]
    assert f.farms == 1 and f.inside_hours == 0.0 and f.ring_hours == 0.0


def test_measurement_of_an_unknown_run_fails_loudly(conn):
    with pytest.raises(KeyError, match="31337"):
        measure_zone_contrast(conn, 31337, cutoff_year=2023)


def test_a_stored_contrast_loads_back_per_run_and_absent_is_none(conn):
    run_id = store_overlap(
        conn,
        OverlapResult(trawled=(), unmapped_effort={}),
        effort_source="e",
        carbon_source="c",
        effort_year=2024,
    )
    store_wind_farm_zones(
        conn, [_zone("z", GridCell(lat_index=5390, lon_index=764), 2010)], source="s"
    )
    assert load_zone_contrast(conn, run_id) is None

    rows = measure_zone_contrast(conn, run_id, cutoff_year=2023)
    store_zone_contrast(conn, run_id, cutoff_year=2023, rows=rows)
    loaded = load_zone_contrast(conn, run_id)

    assert loaded.run_id == run_id
    assert loaded.cutoff_year == 2023
    assert loaded.rows == rows
    assert loaded.computed_at is not None
    # Re-measuring replaces the run's rows rather than stacking them.
    store_zone_contrast(conn, run_id, cutoff_year=2023, rows=rows)
    assert len(load_zone_contrast(conn, run_id).rows) == len(rows)
