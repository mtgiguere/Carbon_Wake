"""Behavioral contract for the store's cross-year view and the footprint
summary table.

The cumulative footprint (carbon_atlas.footprint) needs every run's cells
merged BY CELL across years — a view the per-run store never offered — and
somewhere to keep its result, because a union over a decade of cells is an
offline computation, not a request. The table enforces the bracket's own
invariant (floor <= union <= ceiling) as a constraint, in the ADR-0010 spirit:
the database refuses a summary that contradicts itself.

Written test-first per TDD_CONTRACT.md.
"""

import math

import psycopg.errors
import pytest

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.db.store import (
    iter_cell_histories,
    latest_footprint_summary,
    store_footprint_summary,
    store_overlap,
)
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.footprint import CumulativeFootprint, FootprintBracket
from carbon_atlas.overlap import OverlapResult, TrawledCell

pytestmark = pytest.mark.integration

_DENSITY = CarbonDensity(mean=1.5652642, uncertainty=2.4579988)
_HOTSPOT = GridCell(lat_index=5390, lon_index=764)
_NEIGHBOUR = GridCell(lat_index=5391, lon_index=760)
_UNMAPPED = GridCell(lat_index=5366, lon_index=748)

_RUN_2012 = OverlapResult(
    trawled=(
        TrawledCell(
            cell=_HOTSPOT,
            fishing_hours_by_gear={"trawlers": 15.0, "dredge_fishing": 0.5},
            carbon=_DENSITY,
        ),
        TrawledCell(
            cell=_NEIGHBOUR, fishing_hours_by_gear={"dredge_fishing": 2.0}, carbon=_DENSITY
        ),
    ),
    unmapped_effort={_UNMAPPED: {"trawlers": 7.25}},
)
_RUN_2013 = OverlapResult(
    trawled=(
        TrawledCell(cell=_HOTSPOT, fishing_hours_by_gear={"trawlers": 40.0}, carbon=_DENSITY),
    ),
    unmapped_effort={},
)


def _store(conn, result, year):
    return store_overlap(
        conn, result, effort_source=f"y{year}", carbon_source="c", effort_year=year
    )


def test_cell_histories_merge_runs_by_cell_keyed_by_each_runs_year(conn):
    """Two years, one shared cell: the hotspot's history holds both years
    (per gear), the 2012-only cells hold one, and the unmapped cell is
    present with mapped=False. Ordered by cell (south to north, west to
    east), so identical inputs stream identically."""
    id_2012 = _store(conn, _RUN_2012, 2012)
    id_2013 = _store(conn, _RUN_2013, 2013)

    histories = list(iter_cell_histories(conn, [id_2012, id_2013]))

    assert [h.cell for h in histories] == [_UNMAPPED, _HOTSPOT, _NEIGHBOUR]
    unmapped, hotspot, neighbour = histories
    assert unmapped.mapped is False
    assert unmapped.hours_by_year == {2012: {"trawlers": 7.25}}
    assert hotspot.mapped is True
    assert hotspot.hours_by_year == {
        2012: {"trawlers": 15.0, "dredge_fishing": 0.5},
        2013: {"trawlers": 40.0},
    }
    assert neighbour.hours_by_year == {2012: {"dredge_fishing": 2.0}}


def test_two_runs_for_the_same_year_are_refused(conn):
    """A cell cannot have two histories for one year; picking one silently
    would hide a real ambiguity in what the caller asked for."""
    a = _store(conn, _RUN_2012, 2012)
    b = _store(conn, _RUN_2013, 2012)

    with pytest.raises(ValueError, match="2012"):
        list(iter_cell_histories(conn, [a, b]))


def test_runs_that_disagree_on_whether_a_cell_is_mapped_are_refused(conn):
    """The same cell mapped in one run and unmapped in another means the runs
    were joined against different carbon layers; a union across them would
    mix denominators. Refused, naming the cell."""
    mapped = _store(conn, _RUN_2012, 2012)
    unmapped = _store(
        conn,
        OverlapResult(trawled=(), unmapped_effort={_HOTSPOT: {"trawlers": 1.0}}),
        2013,
    )

    with pytest.raises(ValueError, match="5390, 764"):
        list(iter_cell_histories(conn, [mapped, unmapped]))


def test_an_unknown_run_id_fails_loudly(conn):
    with pytest.raises(KeyError, match="31337"):
        list(iter_cell_histories(conn, [31337]))


def test_no_runs_requested_is_refused(conn):
    with pytest.raises(ValueError):
        list(iter_cell_histories(conn, []))


_SUMMARY = CumulativeFootprint(
    years=(2012, 2013),
    cells=3,
    mapped=FootprintBracket(lower_m2=1.0e9, poisson_m2=1.4e9, upper_m2=1.8e9),
    all_effort=FootprintBracket(lower_m2=1.2e9, poisson_m2=1.7e9, upper_m2=2.3e9),
    per_year_mapped_m2={2012: 6.0e8, 2013: 1.0e9},
)


def test_a_stored_summary_is_the_latest_and_loads_back_exactly(conn):
    id_2012 = _store(conn, _RUN_2012, 2012)
    id_2013 = _store(conn, _RUN_2013, 2013)

    assert latest_footprint_summary(conn) is None
    summary_id = store_footprint_summary(
        conn, _SUMMARY, run_ids=[id_2012, id_2013], mapped_seabed_area_m2=5.0e10
    )
    record = latest_footprint_summary(conn)

    assert record.id == summary_id
    assert record.run_ids == (id_2012, id_2013)
    assert record.years == (2012, 2013)
    assert record.cells == 3
    assert record.mapped_seabed_area_m2 == 5.0e10
    assert record.mapped == _SUMMARY.mapped
    assert record.all_effort == _SUMMARY.all_effort
    assert record.per_year_mapped_m2 == {2012: 6.0e8, 2013: 1.0e9}
    assert math.isclose(record.fractions.poisson, 1.4e9 / 5.0e10)
    assert record.computed_at is not None


def test_the_newest_summary_wins(conn):
    run = _store(conn, _RUN_2012, 2012)
    store_footprint_summary(conn, _SUMMARY, run_ids=[run], mapped_seabed_area_m2=5.0e10)
    newer = store_footprint_summary(conn, _SUMMARY, run_ids=[run], mapped_seabed_area_m2=6.0e10)

    assert latest_footprint_summary(conn).id == newer


def test_the_database_itself_rejects_a_self_contradicting_bracket(conn):
    """floor <= union <= ceiling is a table constraint, not only Python."""
    run = _store(conn, _RUN_2012, 2012)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO footprint_summary (run_ids, years, cells, mapped_seabed_area_m2,"
            " mapped_lower_m2, mapped_poisson_m2, mapped_upper_m2,"
            " all_lower_m2, all_poisson_m2, all_upper_m2, per_year_mapped_m2)"
            " VALUES (%s, %s, 1, 1.0, 3.0, 2.0, 1.0, 1.0, 2.0, 3.0, '{}')",
            ([run], [2012]),
        )


def test_a_summary_must_reference_real_runs(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        store_footprint_summary(conn, _SUMMARY, run_ids=[], mapped_seabed_area_m2=1.0)
