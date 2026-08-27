"""HTTP contract for the MVT tile endpoint (ADR-0015).

The map's bulk data feed: `GET /api/runs/<id>/tiles/<z>/<x>/<y>.mvt` returns
Mapbox Vector Tile bytes with the proper content type. Errors are loud and
specific: an unknown run is a 404 naming the id; tile coordinates outside the
slippy scheme (zoom past 22, x or y beyond 2^z) are a 400, never clamped.

Written test-first per TDD_CONTRACT.md.
"""

import math

import mapbox_vector_tile
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
            fishing_hours_by_gear={"trawlers": 15.0057},
            carbon=CarbonDensity(mean=1.5652642, uncertainty=2.4579988),
        ),
    ),
    unmapped_effort={},
)


@pytest.fixture
def run_id(raw_conn):
    return store_overlap(raw_conn, _RESULT, effort_source="e", carbon_source="c", effort_year=2012)


def test_a_tile_is_served_as_decodable_mvt_bytes(client, run_id):
    """The tile over the seeded cell comes back with the MVT media type and
    decodes to the 'cells' layer holding the cell."""
    response = client.get(f"/api/runs/{run_id}/tiles/10/533/329.mvt")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/vnd.mapbox-vector-tile"
    tile = mapbox_vector_tile.decode(response.content)
    properties = tile["cells"]["features"][0]["properties"]
    assert (properties["lat_index"], properties["lon_index"]) == (5390, 764)
    assert math.isclose(properties["fishing_hours"], 15.0057, rel_tol=1e-9)


def test_an_empty_tile_is_a_valid_empty_response(client, run_id):
    """An ocean tile is 200 with zero bytes — MapLibre treats it as 'nothing
    to draw', which is exactly the truth."""
    response = client.get(f"/api/runs/{run_id}/tiles/10/0/0.mvt")

    assert response.status_code == 200
    assert response.content == b""


def test_an_unknown_run_is_a_404_naming_the_id(client, db):
    response = client.get("/api/runs/6060/tiles/10/533/329.mvt")

    assert response.status_code == 404
    assert "6060" in response.json()["detail"]


@pytest.mark.parametrize(
    ("z", "x", "y"),
    [(23, 0, 0), (10, 1024, 0), (10, 0, 1024), (0, 1, 0)],
    ids=["zoom-past-22", "x-beyond-2^z", "y-beyond-2^z", "x-beyond-2^0"],
)
def test_coordinates_outside_the_slippy_scheme_are_a_400(client, run_id, z, x, y):
    """z/x/y that name no real tile are refused, never clamped onto one."""
    response = client.get(f"/api/runs/{run_id}/tiles/{z}/{x}/{y}.mvt")

    assert response.status_code == 400
