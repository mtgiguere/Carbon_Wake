"""Behavioral contract for the PostGIS overlap store (ADR-0010).

The store persists an OverlapResult with full fidelity — both sides, exact
values, deterministic order — and the schema itself enforces the honesty rules
(non-negative quantities, never half a carbon pair) so that not even a buggy
future writer can corrupt the table. All tests here run against a real
PostGIS; the constraints are the point, and only the database can prove them.

Written test-first per TDD_CONTRACT.md.
"""

import math

import psycopg.errors
import pytest

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.db.store import (
    apply_schema,
    get_run,
    list_runs,
    load_overlap,
    store_overlap,
    trawled_cells_intersecting,
)
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
        # A dredge-only cell with a recorded zero: 0.0 hours is DATA (looked,
        # found none) and must survive the round trip as 0.0, never as absent.
        TrawledCell(
            cell=GridCell(lat_index=5391, lon_index=760),
            fishing_hours_by_gear={"dredge_fishing": 0.0},
            carbon=CarbonDensity(mean=0.0, uncertainty=0.7),
        ),
    ),
    unmapped_effort={GridCell(lat_index=5366, lon_index=748): {"trawlers": 7.25}},
)


def _store(conn):
    return store_overlap(
        conn, _RESULT, effort_source="GFW fleet-daily v3, 2012", carbon_source="Diesing 2021"
    )


def test_the_schema_applies_idempotently(conn):
    """Applying the schema to a database that already has it is a no-op, so
    every ETL run can apply-then-write without caring who went first."""
    apply_schema(conn)
    apply_schema(conn)


def test_a_stored_overlap_loads_back_exactly(conn):
    """Round trip is identity: both sides, every value, the deterministic cell
    order — nothing gained, lost, or rounded on the way through the database."""
    run_id = _store(conn)

    assert load_overlap(conn, run_id) == _RESULT


def test_each_run_records_its_provenance_including_the_honest_label(conn):
    """The etl_run row carries sources, both sides' totals, and the ADR-0009
    effort-layer label VERBATIM — persistence keeps the honesty layer intact."""
    run_id = _store(conn)

    row = conn.execute(
        "SELECT effort_source, carbon_source, effort_layer_label, cells_mapped,"
        " cells_unmapped, fishing_hours_mapped, fishing_hours_unmapped"
        " FROM etl_run WHERE id = %s",
        (run_id,),
    ).fetchone()

    assert row[0] == "GFW fleet-daily v3, 2012"
    assert row[1] == "Diesing 2021"
    assert "midwater" in row[2].lower()
    assert row[3] == 2
    assert row[4] == 1
    assert math.isclose(row[5], 15.5057, rel_tol=1e-12)  # 15.0057 trawl + 0.5 dredge
    assert math.isclose(row[6], 7.25, rel_tol=1e-12)


def test_an_empty_overlap_is_a_valid_run_not_an_error(conn):
    """A year with zero effort in the region stores a real run — provenance
    with zero counts — and loads back as the empty result it was. An honest
    zero, distinguishable (via the run row) from 'never ran'."""
    empty = OverlapResult(trawled=(), unmapped_effort={})

    run_id = store_overlap(conn, empty, effort_source="s", carbon_source="c")

    assert load_overlap(conn, run_id) == empty
    counts = conn.execute(
        "SELECT cells_mapped, cells_unmapped FROM etl_run WHERE id = %s", (run_id,)
    ).fetchone()
    assert counts == (0, 0)


def test_runs_list_newest_first_with_full_provenance(conn):
    """list_runs surfaces every run's provenance record — newest first, since
    the newest run is what the map shows by default."""
    first = _store(conn)
    second = store_overlap(conn, _RESULT, effort_source="e2", carbon_source="c2")

    runs = list_runs(conn)

    assert [r.id for r in runs] == [second, first]
    newest = runs[0]
    assert newest.effort_source == "e2"
    assert newest.carbon_source == "c2"
    assert "midwater" in newest.effort_layer_label.lower()
    assert (newest.cells_mapped, newest.cells_unmapped) == (2, 1)
    assert math.isclose(newest.fishing_hours_mapped, 15.5057, rel_tol=1e-12)
    assert math.isclose(newest.fishing_hours_unmapped, 7.25, rel_tol=1e-12)
    assert newest.created_at is not None


def test_an_empty_database_lists_no_runs(conn):
    """No runs is a valid answer — an empty tuple, not an error."""
    assert list_runs(conn) == ()


def test_get_run_returns_one_run_and_unknown_ids_fail_loudly(conn):
    """get_run is the single-run lookup the API's 404 depends on: a real id
    returns its record, an unknown id raises naming itself."""
    run_id = _store(conn)

    assert get_run(conn, run_id).id == run_id
    with pytest.raises(KeyError, match="4242"):
        get_run(conn, 4242)


def test_loading_an_unknown_run_fails_loudly(conn):
    """A missing run must raise naming the id — not return an empty result a
    caller could mistake for a real run that found nothing."""
    with pytest.raises(KeyError, match="9999"):
        load_overlap(conn, 9999)


def test_the_database_itself_rejects_half_a_carbon_pair(conn):
    """The never-half-a-pair rule as a table constraint: a direct INSERT (as a
    buggy future writer would do) with a mean but no uncertainty is refused by
    PostgreSQL, not by our Python."""
    run_id = _store(conn)

    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO overlap_cell (run_id, lat_index, lon_index,"
            " fishing_hours_trawlers, oc_density_mean, oc_density_uncertainty, geom)"
            " VALUES (%s, 5400, 700, 1.0, 2.5, NULL,"
            " ST_MakeEnvelope(7.00, 54.00, 7.01, 54.01, 4326))",
            (run_id,),
        )


def test_the_database_itself_rejects_negative_fishing_hours(conn):
    """Same last-line defense for the effort side, per gear column."""
    run_id = _store(conn)

    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO overlap_cell (run_id, lat_index, lon_index,"
            " fishing_hours_trawlers, oc_density_mean, oc_density_uncertainty, geom)"
            " VALUES (%s, 5400, 700, -0.1, NULL, NULL,"
            " ST_MakeEnvelope(7.00, 54.00, 7.01, 54.01, 4326))",
            (run_id,),
        )


def test_the_database_itself_rejects_a_cell_with_no_gear_at_all(conn):
    """A row where every per-gear column is NULL claims effort happened while
    recording none of it — not a cell, a bug. Refused by the schema."""
    run_id = _store(conn)

    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO overlap_cell (run_id, lat_index, lon_index,"
            " fishing_hours_trawlers, fishing_hours_dredge_fishing,"
            " oc_density_mean, oc_density_uncertainty, geom)"
            " VALUES (%s, 5400, 700, NULL, NULL, NULL, NULL,"
            " ST_MakeEnvelope(7.00, 54.00, 7.01, 54.01, 4326))",
            (run_id,),
        )


def test_the_total_hours_column_is_generated_and_cannot_drift(conn):
    """`fishing_hours` is a GENERATED column: the database computes the total
    from the per-gear columns (NULL counting as 0), so no writer can ever
    store a total that disagrees with its parts."""
    run_id = _store(conn)

    rows = conn.execute(
        "SELECT fishing_hours_trawlers, fishing_hours_dredge_fishing, fishing_hours"
        " FROM overlap_cell WHERE run_id = %s ORDER BY lat_index",
        (run_id,),
    ).fetchall()

    assert rows == [(7.25, None, 7.25), (15.0057, 0.5, 15.5057), (None, 0.0, 0.0)]


def test_spatial_query_finds_the_cells_a_bbox_intersects(conn):
    """The stored geometry does real spatial work: a bbox strictly inside one
    cell returns exactly that trawled cell — the seed of every future map-tile
    and region query."""
    run_id = _store(conn)

    hits = trawled_cells_intersecting(
        conn, run_id, lat_min=53.902, lat_max=53.908, lon_min=7.643, lon_max=7.647
    )

    assert hits == (_RESULT.trawled[0],)


def test_a_real_years_overlap_stores_and_summarizes_correctly(conn):
    """End to end into persistence: the committed real German Bight fixtures
    flow through the whole pipeline into PostGIS, and SQL aggregation over the
    stored rows reproduces the independently pinned ground truth
    (fixtures/real/gfw/README.md): 220 mapped / 97 unmapped cells,
    139.7554 / 168.4296 fishing hours."""
    from pathlib import Path

    from carbon_atlas.effort.aggregate import aggregate_fishing_hours
    from carbon_atlas.ingest.diesing import DensityRasterPair
    from carbon_atlas.ingest.gfw import parse_fleet_daily
    from carbon_atlas.overlap import overlap_effort_with_carbon

    real = Path(__file__).parent.parent / "fixtures" / "real"
    with (real / "gfw" / "fleet-daily-100-v3-2012.german-bight-box.csv").open(
        encoding="utf-8"
    ) as f:
        effort = aggregate_fishing_hours(parse_fleet_daily(f))
    with DensityRasterPair(
        real / "diesing2021" / "OCdensity_quantrf_mean.win60.tif",
        real / "diesing2021" / "OCdensity_quantrf_tot.unc.win60.tif",
    ) as pair:
        result = overlap_effort_with_carbon(effort, pair.sample)

    run_id = store_overlap(
        conn, result, effort_source="GFW fleet-daily v3, 2012", carbon_source="Diesing 2021"
    )

    mapped, unmapped, mapped_hours, unmapped_hours = conn.execute(
        "SELECT count(*) FILTER (WHERE oc_density_mean IS NOT NULL),"
        " count(*) FILTER (WHERE oc_density_mean IS NULL),"
        " coalesce(sum(fishing_hours) FILTER (WHERE oc_density_mean IS NOT NULL), 0),"
        " coalesce(sum(fishing_hours) FILTER (WHERE oc_density_mean IS NULL), 0)"
        " FROM overlap_cell WHERE run_id = %s",
        (run_id,),
    ).fetchone()

    assert (mapped, unmapped) == (220, 97)
    assert math.isclose(mapped_hours, 139.7554, rel_tol=1e-9)
    assert math.isclose(unmapped_hours, 168.4296, rel_tol=1e-9)
    assert load_overlap(conn, run_id) == result
