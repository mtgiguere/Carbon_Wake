"""HTTP contract for the reference-zone endpoints (ADR-0018).

The zones ship as GeoJSON with their source and license on every feature;
the contrast ships per country through the pure layer's arithmetic, with the
unmeasured (year-unknown) farms counted, the cutoff year stated, and the
caveats attached. Nothing measured -> 404, never a zero.

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.db.store import (
    ZoneMeasurement,
    store_overlap,
    store_wind_farm_zones,
    store_zone_contrast,
)
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.overlap import OverlapResult, TrawledCell
from carbon_atlas.zones import WindFarmZone

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

_SQUARE = {
    "type": "Polygon",
    "coordinates": [[[7.64, 53.9], [7.65, 53.9], [7.65, 53.91], [7.64, 53.91], [7.64, 53.9]]],
}
_ZONE = WindFarmZone(
    name="Test Farm",
    country="Testland",
    status="Production",
    commissioned_year=2015,
    power_mw=300.0,
    turbines=40,
    area_km2=0.73,
    geometry=_SQUARE,
)
_ROWS = (
    ZoneMeasurement("Farland", 2, 0, 50.0, 0.0, 400.0, 400.0),
    ZoneMeasurement("Testland", 3, 1, 100.0, 50.0, 400.0, 600.0),
    ZoneMeasurement("Unknownia", 0, 2, 0.0, 0.0, 0.0, 0.0),
)


@pytest.fixture
def run_id(raw_conn):
    run_id = store_overlap(
        raw_conn,
        OverlapResult(
            trawled=(
                TrawledCell(
                    cell=GridCell(lat_index=5390, lon_index=764),
                    fishing_hours_by_gear={"trawlers": 10.0},
                    carbon=CarbonDensity(mean=1.5, uncertainty=2.4),
                ),
            ),
            unmapped_effort={},
        ),
        effort_source="e",
        carbon_source="c",
        effort_year=2024,
    )
    store_wind_farm_zones(raw_conn, [_ZONE], source="EMODnet test; fetched 2026-09-08")
    return run_id


def test_zones_are_served_as_geojson_with_source_and_license_per_feature(client, run_id):
    response = client.get("/api/zones/wind-farms/")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["count"] == 1
    (feature,) = body["features"]
    assert feature["geometry"]["type"] == "MultiPolygon"
    props = feature["properties"]
    assert props["name"] == "Test Farm"
    assert props["country"] == "Testland"
    assert props["status"] == "Production"
    assert props["commissioned_year"] == 2015
    assert props["power_mw"] == 300.0
    assert props["turbines"] == 40
    assert props["source"].startswith("EMODnet")
    assert "CC-BY 4.0" in body["license"]
    assert body["kind"] == "offshore wind farms in production or under construction"


def test_no_zones_is_an_empty_collection_not_an_error(client, db):
    body = client.get("/api/zones/wind-farms/").json()
    assert body["count"] == 0 and body["features"] == []


def test_the_contrast_is_served_per_country_through_the_pure_layer(client, raw_conn, run_id):
    store_zone_contrast(raw_conn, run_id, cutoff_year=2023, rows=_ROWS)

    response = client.get(f"/api/runs/{run_id}/zone-contrast/")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["effort_year"] == 2024
    assert body["cutoff_year"] == 2023
    assert body["ring_width_m"] == 5000.0

    by_country = {row["country"]: row for row in body["countries"]}
    testland = by_country["Testland"]
    assert testland["farms"] == 3 and testland["farms_without_year"] == 1
    assert math.isclose(testland["inside_density"], 0.5)
    assert math.isclose(testland["ring_density"], 1.5)
    assert math.isclose(testland["ratio"], 1.0 / 3.0)
    farland = by_country["Farland"]
    assert farland["inside_density"] == 0.0 and math.isclose(farland["ratio"], 0.0)
    # Only year-unknown farms: nothing measurable, so no densities — not zeros.
    unknownia = by_country["Unknownia"]
    assert unknownia["farms"] == 0 and unknownia["farms_without_year"] == 2
    assert unknownia["inside_density"] is None and unknownia["ratio"] is None

    total = body["total"]
    assert total["farms"] == 5 and total["farms_without_year"] == 3
    assert math.isclose(total["inside_density"], 50.0 / 150.0)
    assert math.isclose(total["ring_density"], 1000.0 / 800.0)

    caveats = " ".join(body["caveats"]).lower()
    assert "matched" in caveats and "united kingdom" in caveats
    assert "EMODnet" in body["source"]


def test_an_unmeasured_run_is_a_404_with_a_message(client, run_id):
    response = client.get(f"/api/runs/{run_id}/zone-contrast/")
    assert response.status_code == 404
    assert "contrast" in response.json()["detail"].lower()


def test_an_unknown_run_is_a_404_naming_it(client, db):
    response = client.get("/api/runs/31337/zone-contrast/")
    assert response.status_code == 404
    assert "31337" in response.json()["detail"]
