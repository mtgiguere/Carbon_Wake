"""Behavioral contract for effort aggregation.

The ETL's question to this module: for each grid cell, how many fishing hours
of each included gear class landed there? Per-gear matters because the
disturbed-carbon model (ADR-0012) prices the classes differently — summing
them first would silently price dredge hours as trawler hours. A record that
would poison the sums (negative hours, NaN) is rejected at construction,
never absorbed.

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from carbon_atlas.effort.aggregate import EffortRecord, aggregate_fishing_hours
from carbon_atlas.effort.grid import GridCell

_CELL_A = GridCell(lat_index=5555, lon_index=301)
_CELL_B = GridCell(lat_index=5556, lon_index=301)


def _record(cell: GridCell, geartype: str, fishing_hours: float) -> EffortRecord:
    return EffortRecord(cell=cell, geartype=geartype, fishing_hours=fishing_hours)


def test_hours_sum_per_cell_per_gear_class():
    """Gear classes stay separate within a cell — the disturbed-carbon model
    prices them differently, so summing here would corrupt every estimate —
    while records of the SAME gear in the same cell add up."""
    totals = aggregate_fishing_hours(
        [
            _record(_CELL_A, "trawlers", 2.5),
            _record(_CELL_A, "dredge_fishing", 1.0),
            _record(_CELL_A, "trawlers", 1.5),
            _record(_CELL_B, "trawlers", 4.0),
        ]
    )

    assert totals == {
        _CELL_A: {"trawlers": 4.0, "dredge_fishing": 1.0},
        _CELL_B: {"trawlers": 4.0},
    }


def test_excluded_gear_contributes_nothing_not_even_the_cell():
    """A cell fished only by excluded gear is ABSENT from the result — absent
    means 'no included effort observed', which is different from a present 0.0
    (and the difference matters when the map colors cells)."""
    totals = aggregate_fishing_hours(
        [
            _record(_CELL_A, "trawlers", 2.0),
            _record(_CELL_B, "purse_seines", 9.0),
        ]
    )

    assert totals == {_CELL_A: {"trawlers": 2.0}}


def test_no_records_aggregate_to_an_empty_mapping():
    """The empty-input edge (TDD_CONTRACT.md Bug #2): no records is a valid
    answer — an empty mapping, not a crash."""
    assert aggregate_fishing_hours([]) == {}


def test_zero_fishing_hours_is_a_valid_record():
    """GFW emits rows where a vessel was present but no fishing was detected —
    fishing_hours 0.0 is real data, and it does surface its cell and gear
    (effort was looked for and none found: a true zero, not an unknown)."""
    totals = aggregate_fishing_hours([_record(_CELL_A, "trawlers", 0.0)])

    assert totals == {_CELL_A: {"trawlers": 0.0}}


def test_negative_fishing_hours_is_rejected_at_construction():
    """Negative hours are physically meaningless; absorbed into a sum they
    silently shrink real effort. Reject at the record, before any sum exists."""
    with pytest.raises(ValueError):
        _record(_CELL_A, "trawlers", -0.1)


def test_nan_fishing_hours_is_rejected_at_construction():
    """NaN poisons every sum it touches and survives most comparisons. It must
    be impossible to construct, not merely unlikely to be aggregated."""
    with pytest.raises(ValueError):
        _record(_CELL_A, "trawlers", float("nan"))


# Bounded hours: one fleet-day in one cell cannot exceed 24 h/vessel; 1e6 leaves
# room for absurd-but-finite inputs while keeping sums away from float overflow.
_hours = st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False)
_cells = st.builds(
    GridCell,
    lat_index=st.integers(min_value=-9000, max_value=8999),
    lon_index=st.integers(min_value=-18000, max_value=17999),
)
_geartypes = st.sampled_from(
    ["trawlers", "dredge_fishing", "purse_seines", "drifting_longlines", "fishing"]
)
_records = st.lists(
    st.builds(EffortRecord, cell=_cells, geartype=_geartypes, fishing_hours=_hours),
    max_size=50,
)

_INCLUDED = ("trawlers", "dredge_fishing")


@given(records=_records)
def test_aggregate_conserves_hours_exactly_per_gear_class(records):
    """Property: for EACH included gear class, the aggregate's grand total
    equals the sum of that class's record hours — no effort invented, lost,
    or reattributed to another gear, however records interleave."""
    totals = aggregate_fishing_hours(records)

    for gear in _INCLUDED:
        aggregated = sum(by_gear.get(gear, 0.0) for by_gear in totals.values())
        recorded = sum(r.fishing_hours for r in records if r.geartype == gear)
        assert math.isclose(aggregated, recorded, rel_tol=1e-9, abs_tol=1e-9)


@given(records=_records)
def test_every_aggregated_cell_and_gear_traces_back_to_a_record(records):
    """Property: no cell appears from nowhere and no gear appears in a cell
    without a record of that gear in that cell."""
    totals = aggregate_fishing_hours(records)

    assert set(totals) == {r.cell for r in records if r.geartype in _INCLUDED}
    for cell, by_gear in totals.items():
        assert set(by_gear) == {
            r.geartype for r in records if r.cell == cell and r.geartype in _INCLUDED
        }