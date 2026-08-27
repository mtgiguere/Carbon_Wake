"""HTTP contract for the bbox-scoped trawled-cells endpoint.

This is the map's data feed: GeoJSON features whose geometry is the real
0.01-degree cell polygon and whose properties carry fishing hours — per gear
class AND totalled — plus the FULL carbon pair, never a bare mean. Errors are
loud and specific: an unknown run is a 404 naming the id, a missing or
malformed bbox is a 400.

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.db.store import store_overlap
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.overlap import OverlapResult, TrawledCell

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

_RESULT = OverlapResult(
    trawled=(
        TrawledCell(
            cell=GridCell(lat_index=5390, lon_index=764),
            fishing_hours_by_gear={"trawlers": 15.0057, "dredge_fishing": 0.5},
            carbon=CarbonDensity(mean=1.5652642, uncertainty=2.4579988),
        ),
        TrawledCell(
            cell=GridCell(lat_index=5395, lon_index=770),
            fishing_hours_by_gear={"trawlers": 3.0},
            carbon=CarbonDensity(mean=4.2, uncertainty=1.1),
        ),
    ),
    unmapped_effort={GridCell(lat_index=5390, lon_index=765): {"trawlers": 7.25}},
)


@pytest.fixture
def run_id(raw_conn):
    return store_overlap(raw_conn, _RESULT, effort_source="e", carbon_source="c", effort_year=2012)


def test_cells_in_a_bbox_are_geojson_features_with_the_full_carbon_pair(client, run_id):
    """A bbox inside one cell returns exactly that cell: its true polygon
    (closed ring on the 0.01-degree corners) and properties carrying hours
    plus BOTH halves of the carbon value."""
    response = client.get(f"/api/runs/{run_id}/cells/?bbox=7.643,53.902,7.647,53.908")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["count"] == 1
    feature = body["features"][0]
    assert feature["type"] == "Feature"
    assert feature["geometry"] == {
        "type": "Polygon",
        "coordinates": [[[7.64, 53.9], [7.65, 53.9], [7.65, 53.91], [7.64, 53.91], [7.64, 53.9]]],
    }
    assert math.isclose(feature["properties"]["fishing_hours"], 15.5057, rel_tol=1e-12)
    by_gear = feature["properties"]["fishing_hours_by_gear"]
    assert math.isclose(by_gear["trawlers"], 15.0057, rel_tol=1e-12)
    assert math.isclose(by_gear["dredge_fishing"], 0.5, rel_tol=1e-12)
    assert math.isclose(feature["properties"]["oc_density"]["mean"], 1.5652642, rel_tol=1e-9)
    assert math.isclose(feature["properties"]["oc_density"]["uncertainty"], 2.4579988, rel_tol=1e-9)


def test_unmapped_cells_do_not_appear_as_trawled_features(client, run_id):
    """The unmapped neighbor (7.65-7.66) must not leak into the trawled layer
    even when the bbox covers it — it has no carbon value to show."""
    response = client.get(f"/api/runs/{run_id}/cells/?bbox=7.60,53.88,7.70,53.92")

    body = response.json()
    assert body["count"] == 1  # only the mapped (5390, 764) cell


def test_a_bbox_with_no_cells_is_an_empty_collection(client, run_id):
    """No overlap in the window is a valid answer: an empty FeatureCollection."""
    response = client.get(f"/api/runs/{run_id}/cells/?bbox=0.0,50.0,0.1,50.1")

    assert response.status_code == 200
    assert response.json() == {"type": "FeatureCollection", "count": 0, "features": []}


def test_an_unknown_run_is_a_404_naming_the_id(client, db):
    """The 404 names the missing run so the caller isn't left guessing."""
    response = client.get("/api/runs/4242/cells/?bbox=7.6,53.9,7.7,53.95")

    assert response.status_code == 404
    assert "4242" in response.json()["detail"]


@pytest.mark.parametrize(
    "query",
    ["", "?bbox=", "?bbox=1,2,3", "?bbox=a,b,c,d", "?bbox=7.7,53.9,7.6,53.95"],
    ids=["missing", "empty", "three-values", "not-numbers", "inverted"],
)
def test_a_missing_or_malformed_bbox_is_a_400(client, run_id, query):
    """Every broken bbox — absent, empty, wrong arity, non-numeric, inverted —
    is refused with a 400, never guessed into a default window."""
    response = client.get(f"/api/runs/{run_id}/cells/{query}")

    assert response.status_code == 400
