"""Behavioral contract for the effort-carbon overlap join.

This is the project's central query: where does trawling effort sit on mapped
seafloor carbon? The join is pure — the carbon layer arrives as an injected
sampler callable — so the contract can be tested to exhaustion here, and the
raster-backed wiring is proven separately against real committed samples.

Effort travels PER GEAR CLASS end to end (ADR-0012: the disturbed-carbon
model prices the classes differently), and the honesty rule shapes the result
type: effort on UNMAPPED seafloor is reported (cells + per-gear hours), never
silently dropped — a map that quietly discards what it cannot color is lying
by omission.

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
    TrawledCell carrying the PER-GEAR hours AND the full mean+uncertainty
    pair — gear identity survives the join."""
    result = overlap_effort_with_carbon(
        {_SEA: {"trawlers": 12.5, "dredge_fishing": 0.5}}, lambda lat, lon: _DENSITY
    )

    assert result.trawled == (
        TrawledCell(
            cell=_SEA,
            fishing_hours_by_gear={"trawlers": 12.5, "dredge_fishing": 0.5},
            carbon=_DENSITY,
        ),
    )
    assert result.unmapped_effort == {}


def test_a_trawled_cell_totals_its_own_hours():
    """The map often wants one intensity number per cell; the total is the
    sum over the cell's gear classes, derived, never stored separately."""
    cell = TrawledCell(
        cell=_SEA, fishing_hours_by_gear={"trawlers": 12.5, "dredge_fishing": 0.5}, carbon=_DENSITY
    )

    assert math.isclose(cell.total_fishing_hours, 13.0, rel_tol=1e-12)


def test_the_carbon_layer_is_sampled_at_the_cell_center():
    """The sampler must be asked at the cell's CENTER — sampling the lower-left
    corner would systematically shift every cell half a cell south-west."""
    asked = []

    def recording_sampler(lat, lon):
        asked.append((lat, lon))
        return _DENSITY

    overlap_effort_with_carbon({_SEA: {"trawlers": 1.0}}, recording_sampler)

    assert asked == [(_SEA.center_lat, _SEA.center_lon)]


def test_effort_on_unmapped_seafloor_is_reported_not_dropped():
    """A cell whose center samples to None keeps its identity and its per-gear
    hours in unmapped_effort — the honest 'we trawled here but have no carbon
    data'."""
    result = overlap_effort_with_carbon({_LAND: {"dredge_fishing": 7.0}}, lambda lat, lon: None)

    assert result.trawled == ()
    assert result.unmapped_effort == {_LAND: {"dredge_fishing": 7.0}}


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
    effort = {
        north: {"trawlers": 1.0},
        south_east: {"trawlers": 2.0},
        south_west: {"trawlers": 3.0},
    }

    result = overlap_effort_with_carbon(effort, lambda lat, lon: _DENSITY)

    assert [t.cell for t in result.trawled] == [south_west, south_east, north]


def test_the_result_totals_its_hours_on_both_sides():
    """The honesty summary the map and the PR both need: how many fishing
    hours (all gears) landed on mapped carbon, and how many fell off the
    mapped area."""
    sampler = lambda lat, lon: _DENSITY if lat > 53.7 else None  # noqa: E731

    result = overlap_effort_with_carbon(
        {_SEA: {"trawlers": 12.5, "dredge_fishing": 0.5}, _LAND: {"trawlers": 7.0}}, sampler
    )

    assert math.isclose(result.trawled_fishing_hours, 13.0, rel_tol=1e-12)
    assert math.isclose(result.unmapped_fishing_hours, 7.0, rel_tol=1e-12)


_cells = st.builds(
    GridCell,
    lat_index=st.integers(min_value=-9000, max_value=8999),
    lon_index=st.integers(min_value=-18000, max_value=17999),
)
_by_gear = st.dictionaries(
    st.sampled_from(["trawlers", "dredge_fishing"]),
    st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=2,
)
_efforts = st.dictionaries(_cells, _by_gear, max_size=40)


@given(effort=_efforts)
def test_every_effort_cell_lands_on_exactly_one_side_with_its_gears_intact(effort):
    """Property: the join is a clean partition — each input cell appears
    exactly once, on exactly one side, with its per-gear hours unchanged;
    nothing invented, lost, or reattributed, however the sampler splits the
    world."""
    sampler = lambda lat, lon: _DENSITY if (round(lat * 200) % 2) else None  # noqa: E731

    result = overlap_effort_with_carbon(effort, sampler)

    trawled_cells = [t.cell for t in result.trawled]
    key = lambda c: (c.lat_index, c.lon_index)  # noqa: E731
    assert sorted(trawled_cells + list(result.unmapped_effort), key=key) == sorted(effort, key=key)
    for t in result.trawled:
        assert t.fishing_hours_by_gear == effort[t.cell]
    for cell, by_gear in result.unmapped_effort.items():
        assert by_gear == effort[cell]
