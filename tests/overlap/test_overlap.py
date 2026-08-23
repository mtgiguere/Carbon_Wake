"""Behavioral contract for the effort-carbon overlap join.

This is the project's central query: where does trawling effort sit on mapped
seafloor carbon? The join is pure — the carbon layer arrives as an injected
sampler callable — so the contract can be tested to exhaustion here, and the
raster-backed wiring is proven separately against real committed samples.

The honesty rule that shapes the result type: effort on UNMAPPED seafloor is
reported (cells + hours), never silently dropped — a map that quietly discards
what it cannot color is lying by omission.

Written test-first per TDD_CONTRACT.md.
"""

import math

from hypothesis import given
from hypothesis import strategies as st

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.overlap import TrawledCell, overlap_effort_with_carbon

_SEA = GridCell(lat_index=5390, lon_index=759)
_LAND = GridCell(lat_index=5366, lon_index=748)
_DENSITY = CarbonDensity(mean=1.5, uncertainty=2.3)


def test_effort_on_mapped_carbon_joins_into_a_trawled_cell():
    """A cell with effort whose center samples to a carbon value becomes one
    TrawledCell carrying the hours AND the full mean+uncertainty pair."""
    result = overlap_effort_with_carbon({_SEA: 12.5}, lambda lat, lon: _DENSITY)

    assert result.trawled == (TrawledCell(cell=_SEA, fishing_hours=12.5, carbon=_DENSITY),)
    assert result.unmapped_effort == {}


def test_the_carbon_layer_is_sampled_at_the_cell_center():
    """The sampler must be asked at the cell's CENTER — sampling the lower-left
    corner would systematically shift every cell half a cell south-west."""
    asked = []

    def recording_sampler(lat, lon):
        asked.append((lat, lon))
        return _DENSITY

    overlap_effort_with_carbon({_SEA: 1.0}, recording_sampler)

    assert asked == [(_SEA.center_lat, _SEA.center_lon)]


def test_effort_on_unmapped_seafloor_is_reported_not_dropped():
    """A cell whose center samples to None keeps its identity and its hours in
    unmapped_effort — the honest 'we trawled here but have no carbon data'."""
    result = overlap_effort_with_carbon({_LAND: 7.0}, lambda lat, lon: None)

    assert result.trawled == ()
    assert result.unmapped_effort == {_LAND: 7.0}


def test_no_effort_joins_to_an_empty_result():
    """The empty-input edge: no effort is a valid answer, not a crash."""
    result = overlap_effort_with_carbon({}, lambda lat, lon: _DENSITY)

    assert result.trawled == ()
    assert result.unmapped_effort == {}


def test_trawled_cells_come_out_sorted_by_cell_identity():
    """Output order is deterministic (south-to-north, then west-to-east), not
    whatever the effort mapping's insertion order happened to be — so two ETL
    runs over the same data produce identical artifacts."""
    north = GridCell(lat_index=5400, lon_index=700)
    south_east = GridCell(lat_index=5300, lon_index=800)
    south_west = GridCell(lat_index=5300, lon_index=700)
    effort = {north: 1.0, south_east: 2.0, south_west: 3.0}

    result = overlap_effort_with_carbon(effort, lambda lat, lon: _DENSITY)

    assert [t.cell for t in result.trawled] == [south_west, south_east, north]


def test_the_result_totals_its_hours_on_both_sides():
    """The honesty summary the map and the PR both need: how many fishing
    hours landed on mapped carbon, and how many fell off the mapped area."""
    sampler = lambda lat, lon: _DENSITY if lat > 53.7 else None  # noqa: E731

    result = overlap_effort_with_carbon({_SEA: 12.5, _LAND: 7.0}, sampler)

    assert math.isclose(result.trawled_fishing_hours, 12.5, rel_tol=1e-12)
    assert math.isclose(result.unmapped_fishing_hours, 7.0, rel_tol=1e-12)


_cells = st.builds(
    GridCell,
    lat_index=st.integers(min_value=-9000, max_value=8999),
    lon_index=st.integers(min_value=-18000, max_value=17999),
)
_efforts = st.dictionaries(
    _cells,
    st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    max_size=40,
)


@given(effort=_efforts)
def test_every_effort_cell_lands_on_exactly_one_side_and_hours_are_conserved(effort):
    """Property: the join is a clean partition — each input cell appears exactly
    once, on exactly one side, with its hours intact; nothing invented, nothing
    lost, regardless of how the sampler splits the world."""
    sampler = lambda lat, lon: _DENSITY if (round(lat * 200) % 2) else None  # noqa: E731

    result = overlap_effort_with_carbon(effort, sampler)

    trawled_cells = [t.cell for t in result.trawled]
    assert sorted(
        trawled_cells + list(result.unmapped_effort), key=lambda c: (c.lat_index, c.lon_index)
    ) == sorted(effort, key=lambda c: (c.lat_index, c.lon_index))
    for t in result.trawled:
        assert t.fishing_hours == effort[t.cell]
    for cell, hours in result.unmapped_effort.items():
        assert hours == effort[cell]
