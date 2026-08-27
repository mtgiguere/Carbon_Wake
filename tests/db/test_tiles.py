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
    by_key = {
        (f["properties"]["lat_index"], f["properties"]["lon_index"]): f["properties"] for f in cells
    }
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


def test_low_zoom_tiles_aggregate_to_tenth_degree_bins(conn):
    """Below z8 a 0.01-degree cell is subpixel — rendered raw it antialiases
    into invisibility (the contract's 0.4px road-layer story, replayed on our
    own map at first run). Low-zoom tiles therefore aggregate to 0.1-degree
    bins: hours summed per bin per mapped-class, with the bin's true seabed
    area aboard so the style can color by hours per km2 at every zoom. The
    per-cell carbon pair does not survive aggregation (a bin-average would be
    a new, unpublished number) — inspection happens zoomed in."""
    run_id = store_overlap(conn, _RESULT, effort_source="e", carbon_source="c")
    x, y = _slippy_tile(53.905, 7.645, 7)

    tile = mapbox_vector_tile.decode(cells_tile_mvt(conn, run_id, z=7, x=x, y=y))

    features = tile["cells"]["features"]
    by_key = {
        (
            f["properties"]["bin_lat_index"],
            f["properties"]["bin_lon_index"],
            f["properties"]["mapped"],
        ): f["properties"]
        for f in features
    }
    # All three seeded cells share the 0.1-degree bin (539, 76); the two
    # mapped cells aggregate, the unmapped one stays its own feature.
    assert set(by_key) == {(539, 76, True), (539, 76, False)}

    mapped = by_key[(539, 76, True)]
    assert math.isclose(mapped["fishing_hours"], 15.5057 + 3.0, rel_tol=1e-9)
    assert mapped["cells"] == 2
    expected_km2 = (
        GridCell(lat_index=5390, lon_index=764).area_m2
        + GridCell(lat_index=5391, lon_index=765).area_m2
    ) / 1e6
    assert math.isclose(mapped["area_km2"], expected_km2, rel_tol=1e-2)  # spheroid vs sphere
    assert "oc_density_mean" not in mapped

    unmapped = by_key[(539, 76, False)]
    assert math.isclose(unmapped["fishing_hours"], 7.25, rel_tol=1e-9)
    assert unmapped["cells"] == 1


def test_full_zoom_tiles_carry_each_cells_own_area(conn):
    """From z8 up, tiles stay per-cell — and each cell now carries its own
    seabed area so the hours-per-km2 color ramp works identically at every
    zoom."""
    run_id = store_overlap(conn, _RESULT, effort_source="e", carbon_source="c")
    x, y = _slippy_tile(53.905, 7.645, 8)

    tile = mapbox_vector_tile.decode(cells_tile_mvt(conn, run_id, z=8, x=x, y=y))

    hotspot = next(
        f["properties"]
        for f in tile["cells"]["features"]
        if f["properties"].get("lat_index") == 5390 and f["properties"].get("lon_index") == 764
    )
    assert math.isclose(
        hotspot["area_km2"], GridCell(lat_index=5390, lon_index=764).area_m2 / 1e6, rel_tol=1e-2
    )
    assert math.isclose(hotspot["oc_density_mean"], 1.5652642, rel_tol=1e-6)


def test_a_tile_with_no_cells_is_empty_bytes(conn):
    """An ocean tile far from the data is an empty (zero-length) payload —
    a valid 'nothing here', not an error."""
    run_id = store_overlap(conn, _RESULT, effort_source="e", carbon_source="c")

    assert cells_tile_mvt(conn, run_id, z=10, x=0, y=0) == b""


def test_an_unknown_run_fails_loudly(conn):
    """Same rule as every lookup: an unknown run raises naming itself."""
    with pytest.raises(KeyError, match="8888"):
        cells_tile_mvt(conn, 8888, z=10, x=533, y=329)
