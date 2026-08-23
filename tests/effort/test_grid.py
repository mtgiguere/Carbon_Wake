"""Behavioral contract for the 0.01-degree effort grid.

GFW fleet-daily rows locate a cell by the latitude/longitude of its lower-left
corner, as decimal-degree floats (see data/gfw/fleet-daily-v3.schema.json). The
grid model's job is to turn those floats into exact integer cell identities —
float noise must never split one real cell into two — and to reject coordinates
that are not on the 0.01-degree grid at all, loudly, because a file on a
different grid is a wrong input, not a rounding problem.

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from carbon_atlas.effort.grid import GridCell, cell_from_lower_left

# Every lower-left corner the grid can have: latitude corners span [-90, 90)
# and longitude corners [-180, 180) — a corner AT +90 or +180 would name a cell
# lying outside the world.
_lat_indices = st.integers(min_value=-9000, max_value=8999)
_lon_indices = st.integers(min_value=-18000, max_value=17999)


def test_lower_left_corner_maps_to_centidegree_indices():
    """A lower-left corner at (55.55 N, 3.01 E) is the cell whose integer
    identity is (5555, 301) — the corner coordinates in centidegrees."""
    assert cell_from_lower_left(55.55, 3.01) == GridCell(lat_index=5555, lon_index=301)


def test_southern_and_western_hemispheres_keep_negative_indices():
    """A corner south of the equator / west of Greenwich has negative indices;
    the sign must survive the float-to-integer snap exactly."""
    assert cell_from_lower_left(-0.01, -0.01) == GridCell(lat_index=-1, lon_index=-1)


@given(lat_index=_lat_indices, lon_index=_lon_indices)
def test_every_representable_corner_round_trips_exactly(lat_index, lon_index):
    """Property: for EVERY corner the grid can express, converting the integer
    identity to decimal degrees (as a GFW CSV would print it) and back recovers
    the identity exactly. 55.55 * 100 being 5554.999... in binary must never
    split one real cell into two."""
    cell = cell_from_lower_left(lat_index / 100, lon_index / 100)

    assert cell == GridCell(lat_index=lat_index, lon_index=lon_index)


@pytest.mark.parametrize(("lat", "lon"), [(55.555, 3.01), (55.55, 3.014), (55.5549, 3.01)])
def test_coordinates_off_the_grid_are_rejected(lat, lon):
    """A coordinate that is not a 0.01-degree corner means the input is on a
    DIFFERENT grid — silently snapping it would relocate real effort. Raise."""
    with pytest.raises(ValueError):
        cell_from_lower_left(lat, lon)


@pytest.mark.parametrize(
    ("lat", "lon"),
    [(90.0, 0.0), (-90.01, 0.0), (0.0, 180.0), (0.0, -180.01), (550.55, 3.01)],
)
def test_corners_outside_the_world_are_rejected(lat, lon):
    """A lower-left corner at or beyond +90 lat / +180 lon (or below -90/-180)
    names a cell outside the world — corrupt input, not a cell. Raise."""
    with pytest.raises(ValueError):
        cell_from_lower_left(lat, lon)


@pytest.mark.parametrize(("lat", "lon"), [(-90.0, -180.0), (89.99, 179.99)])
def test_extreme_but_valid_corners_are_accepted(lat, lon):
    """The world's own corner cells are valid — the bounds are rejected only
    just PAST them, in both directions (the mutation-audit discipline)."""
    cell = cell_from_lower_left(lat, lon)

    assert cell == GridCell(lat_index=round(lat * 100), lon_index=round(lon * 100))


def test_a_cell_center_is_half_a_cell_in_from_its_lower_left_corner():
    """The center of the cell whose corner is (55.55, 3.01) is (55.555, 3.015)
    — where the carbon layer gets sampled for this cell."""
    cell = GridCell(lat_index=5555, lon_index=301)

    assert math.isclose(cell.center_lat, 55.555, rel_tol=1e-12)
    assert math.isclose(cell.center_lon, 3.015, rel_tol=1e-12)


@given(lat_index=_lat_indices, lon_index=_lon_indices)
def test_every_cell_center_lies_strictly_inside_its_own_cell(lat_index, lon_index):
    """Property: for EVERY cell, the center is strictly between the cell's
    edges — never on a boundary, where a sample could land in a neighbor."""
    cell = GridCell(lat_index=lat_index, lon_index=lon_index)

    assert lat_index / 100 < cell.center_lat < (lat_index + 1) / 100
    assert lon_index / 100 < cell.center_lon < (lon_index + 1) / 100
