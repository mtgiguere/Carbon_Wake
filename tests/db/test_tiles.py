"""Behavioral contract for the MVT tile query (ADR-0015).

The map's data feed at scale: one slippy tile of the run's cells as Mapbox
Vector Tile bytes, built by PostGIS itself (ST_AsMVT over the GiST-indexed
geometry). The encoder is transport, not science — but the tile must carry
BOTH sides of the join (per-gear hours, the carbon pair where mapped, a
`mapped` flag) so the style can honor "unmapped is not zero" visually.

Tiles are verified by decoding real bytes with mapbox-vector-tile — asserting
on opaque blobs would be a hollow test.

Written test-first per TDD_CONTRACT.md.
"""

import math

import mapbox_vector_tile
import pytest

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.db.store import cells_tile_mvt, store_overlap
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.overlap import OverlapResult, TrawledCell

pytestmark = pytest.mark.integration

_RESULT = OverlapResult(
    trawled=(
        TrawledCell(
            cell=GridCell(lat_index=5390, lon_index=764),
            fishing_hours_by_gear={"trawlers": 15.0057, "dredge_fishing": 0.5},
            carbon=CarbonDensity(mean=1.5652642, uncertainty=2.4579988),
        ),
        TrawledCell(
            cell=GridCell(lat_index=5391, lon_index=765),
            fishing_hours_by_gear={"trawlers": 3.0},
            carbon=CarbonDensity(mean=4.2, uncertainty=1.1),
        ),
    ),
    unmapped_effort={GridCell(lat_index=5390, lon_index=765): {"dredge_fishing": 7.25}},
)


def _slippy_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """The OSM slippy-tile (x, y) containing a WGS84 point — the standard
    addressing definition, spelled out so the test's expectations are
    independent of the code under test."""
    n = 2**zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def test_the_covering_tile_carries_both_sides_with_honest_properties(conn):
    """The z=10 tile over the seeded cells decodes to a 'cells' layer holding
    all three cells: per-gear hours as stored; the full carbon pair on mapped
    cells; NO carbon keys (not zeros!) on the unmapped cell; and a `mapped`
    flag the style can switch on."""
    run_id = store_overlap(conn, _RESULT, effort_source="e", carbon_source="c")
    x, y = _slippy_tile(53.905, 7.645, 10)

    tile = mapbox_vector_tile.decode(cells_tile_mvt(conn, run_id, z=10, x=x, y=y))

    cells = tile["cells"]["features"]
    by_key = {(f["properties"]["lat_index"], f["properties"]["lon_index"]): f["properties"] for f in cells}
    assert set(by_key) == {(5390, 764), (5391, 765), (5390, 765)}

    hotspot = by_key[(5390, 764)]
    assert hotspot["mapped"] is True
    assert math.isclose(hotspot["fishing_hours_trawlers"], 15.0057, rel_tol=1e-9)
    assert math.isclose(hotspot["fishing_hours_dredge_fishing"], 0.5, rel_tol=1e-9)
    assert math.isclose(hotspot["fishing_hours"], 15.5057, rel_tol=1e-9)
    assert math.isclose(hotspot["oc_density_mean"], 1.5652642, rel_tol=1e-6)
    assert math.isclose(hotspot["oc_density_uncertainty"], 2.4579988, rel_tol=1e-6)

    unmapped = by_key[(5390, 765)]
    assert unmapped["mapped"] is False
    assert "oc_density_mean" not in unmapped
    assert "oc_density_uncertainty" not in unmapped
    assert math.isclose(unmapped["fishing_hours_dredge_fishing"], 7.25, rel_tol=1e-9)
    assert "fishing_hours_trawlers" not in unmapped  # no record != zero


def test_a_tile_with_no_cells_is_empty_bytes(conn):
    """An ocean tile far from the data is an empty (zero-length) payload —
    a valid 'nothing here', not an error."""
    run_id = store_overlap(conn, _RESULT, effort_source="e", carbon_source="c")

    assert cells_tile_mvt(conn, run_id, z=10, x=0, y=0) == b""


def test_an_unknown_run_fails_loudly(conn):
    """Same rule as every lookup: an unknown run raises naming itself."""
    with pytest.raises(KeyError, match="8888"):
        cells_tile_mvt(conn, 8888, z=10, x=533, y=329)
