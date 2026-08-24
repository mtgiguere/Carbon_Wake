"""Store and load overlap results in PostGIS (ADR-0010).

The store is faithful both ways: an OverlapResult round-trips exactly — both
sides, every value, the deterministic cell order — and every run carries its
provenance (sources, the ADR-0009 effort-layer label verbatim, both sides'
totals). Cell geometry is built in SQL from the integer cell indices, so the
database holds real WGS84 polygons a GiST index can do spatial work on.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psycopg

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.effort.gears import EFFORT_LAYER_LABEL
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.overlap import OverlapResult, TrawledCell


@dataclass(frozen=True)
class RunRecord:
    """One ETL run's provenance row, as stored."""

    id: int
    created_at: datetime
    effort_source: str
    carbon_source: str
    effort_layer_label: str
    cells_mapped: int
    cells_unmapped: int
    fishing_hours_mapped: float
    fishing_hours_unmapped: float


_SELECT_RUNS = (
    "SELECT id, created_at, effort_source, carbon_source, effort_layer_label,"
    " cells_mapped, cells_unmapped, fishing_hours_mapped, fishing_hours_unmapped"
    " FROM etl_run"
)

_SCHEMA = Path(__file__).with_name("schema.sql")

# Bulk load path: COPY the raw values into a session-temp stage, then one
# INSERT..SELECT that builds each cell's polygon in SQL. COPY streams — a
# full-region run is ~370k rows, where a per-row executemany measurably
# stalled; and the stage keeps geometry construction in SQL (ADR-0010).
_CREATE_STAGE = (
    "CREATE TEMP TABLE _overlap_cell_stage (lat_index integer, lon_index integer,"
    " fishing_hours_trawlers double precision,"
    " fishing_hours_dredge_fishing double precision,"
    " oc_density_mean double precision, oc_density_uncertainty double precision)"
)
_COPY_STAGE = (
    "COPY _overlap_cell_stage (lat_index, lon_index, fishing_hours_trawlers,"
    " fishing_hours_dredge_fishing, oc_density_mean, oc_density_uncertainty) FROM STDIN"
)
_INSERT_FROM_STAGE = (
    "INSERT INTO overlap_cell (run_id, lat_index, lon_index, fishing_hours_trawlers,"
    " fishing_hours_dredge_fishing, oc_density_mean, oc_density_uncertainty, geom)"
    " SELECT %s, lat_index, lon_index, fishing_hours_trawlers,"
    " fishing_hours_dredge_fishing, oc_density_mean, oc_density_uncertainty,"
    " ST_MakeEnvelope(lon_index / 100.0, lat_index / 100.0,"
    " (lon_index + 1) / 100.0, (lat_index + 1) / 100.0, 4326)"
    " FROM _overlap_cell_stage"
)
_DROP_STAGE = "DROP TABLE _overlap_cell_stage"


def _by_gear(trawl_hours: float | None, dredge_hours: float | None) -> dict[str, float]:
    """Per-gear hours from the two gear columns, NULLs (no record) omitted."""
    by_gear = {}
    if trawl_hours is not None:
        by_gear["trawlers"] = trawl_hours
    if dredge_hours is not None:
        by_gear["dredge_fishing"] = dredge_hours
    return by_gear


def apply_schema(conn: psycopg.Connection) -> None:
    """Create the ETL-owned tables if absent. Idempotent by construction."""
    conn.execute(_SCHEMA.read_text(encoding="utf-8"))


def store_overlap(
    conn: psycopg.Connection,
    result: OverlapResult,
    *,
    effort_source: str,
    carbon_source: str,
) -> int:
    """Persist ``result`` as one provenance-carrying run; returns the run id."""
    run_id = conn.execute(
        "INSERT INTO etl_run (effort_source, carbon_source, effort_layer_label,"
        " cells_mapped, cells_unmapped, fishing_hours_mapped, fishing_hours_unmapped)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            effort_source,
            carbon_source,
            EFFORT_LAYER_LABEL,
            len(result.trawled),
            len(result.unmapped_effort),
            result.trawled_fishing_hours,
            result.unmapped_fishing_hours,
        ),
    ).fetchone()[0]

    def gear_columns(by_gear: dict[str, float]) -> tuple[float | None, float | None]:
        # The stage's per-gear columns mirror the ADR-0009 inclusion set; a
        # gear the aggregation never saw stays NULL (no record != zero hours).
        return by_gear.get("trawlers"), by_gear.get("dredge_fishing")

    rows = [
        (
            t.cell.lat_index,
            t.cell.lon_index,
            *gear_columns(t.fishing_hours_by_gear),
            t.carbon.mean,
            t.carbon.uncertainty,
        )
        for t in result.trawled
    ] + [
        (cell.lat_index, cell.lon_index, *gear_columns(by_gear), None, None)
        for cell, by_gear in result.unmapped_effort.items()
    ]
    if rows:
        with conn.cursor() as cur:
            cur.execute(_CREATE_STAGE)
            try:
                with cur.copy(_COPY_STAGE) as copy:
                    for row in rows:
                        copy.write_row(row)
                cur.execute(_INSERT_FROM_STAGE, (run_id,))
            finally:
                cur.execute(_DROP_STAGE)
    return run_id


def list_runs(conn: psycopg.Connection) -> tuple[RunRecord, ...]:
    """Every run's provenance record, newest first (the newest run is what
    the map shows by default). No runs is a valid answer: an empty tuple."""
    rows = conn.execute(_SELECT_RUNS + " ORDER BY id DESC").fetchall()
    return tuple(RunRecord(*row) for row in rows)


def get_run(conn: psycopg.Connection, run_id: int) -> RunRecord:
    """One run's provenance record; unknown ids raise ``KeyError`` naming
    themselves — the loud lookup an API 404 hangs off."""
    row = conn.execute(_SELECT_RUNS + " WHERE id = %s", (run_id,)).fetchone()
    if row is None:
        raise KeyError(f"no etl_run with id {run_id}")
    return RunRecord(*row)


def load_overlap(conn: psycopg.Connection, run_id: int) -> OverlapResult:
    """The stored run's OverlapResult, exactly as it went in.

    Raises ``KeyError`` naming an unknown run id — an empty result must never
    impersonate a real run that found nothing.
    """
    if conn.execute("SELECT 1 FROM etl_run WHERE id = %s", (run_id,)).fetchone() is None:
        raise KeyError(f"no etl_run with id {run_id}")

    rows = conn.execute(
        "SELECT lat_index, lon_index, fishing_hours_trawlers, fishing_hours_dredge_fishing,"
        " oc_density_mean, oc_density_uncertainty"
        " FROM overlap_cell WHERE run_id = %s ORDER BY lat_index, lon_index",
        (run_id,),
    ).fetchall()

    trawled = tuple(
        TrawledCell(
            cell=GridCell(lat_index=lat, lon_index=lon),
            fishing_hours_by_gear=_by_gear(trawl_hours, dredge_hours),
            carbon=CarbonDensity(mean=mean, uncertainty=uncertainty),
        )
        for lat, lon, trawl_hours, dredge_hours, mean, uncertainty in rows
        if mean is not None
    )
    unmapped = {
        GridCell(lat_index=lat, lon_index=lon): _by_gear(trawl_hours, dredge_hours)
        for lat, lon, trawl_hours, dredge_hours, mean, _ in rows
        if mean is None
    }
    return OverlapResult(trawled=trawled, unmapped_effort=unmapped)


def effort_density_moments(conn: psycopg.Connection, run_id: int) -> dict[str, tuple[float, float]]:
    """Per gear class, sum over the run's MAPPED cells of hours x density —
    (sum of h x mean, sum of h x uncertainty), in kg·h/m3.

    This is the exact quantity the pure estimate layer scales by the per-gear
    constants (`disturbed_carbon_from_effort_density_sum`); the equality of
    that shortcut with the per-cell model is property-tested. A gear with no
    recorded hours on mapped cells is absent; a run with no mapped cells is
    an empty mapping. Unknown runs raise, naming themselves.
    """
    if conn.execute("SELECT 1 FROM etl_run WHERE id = %s", (run_id,)).fetchone() is None:
        raise KeyError(f"no etl_run with id {run_id}")
    row = conn.execute(
        "SELECT sum(fishing_hours_trawlers * oc_density_mean),"
        " sum(fishing_hours_trawlers * oc_density_uncertainty),"
        " sum(fishing_hours_dredge_fishing * oc_density_mean),"
        " sum(fishing_hours_dredge_fishing * oc_density_uncertainty)"
        " FROM overlap_cell WHERE run_id = %s AND oc_density_mean IS NOT NULL",
        (run_id,),
    ).fetchone()
    moments = {}
    if row[0] is not None:
        moments["trawlers"] = (row[0], row[1])
    if row[2] is not None:
        moments["dredge_fishing"] = (row[2], row[3])
    return moments


def trawled_cells_intersecting(
    conn: psycopg.Connection,
    run_id: int,
    *,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
) -> tuple[TrawledCell, ...]:
    """The run's mapped cells whose polygons intersect a WGS84 bbox — the seed
    of every future map-tile and region query, answered by the GiST index."""
    rows = conn.execute(
        "SELECT lat_index, lon_index, fishing_hours_trawlers, fishing_hours_dredge_fishing,"
        " oc_density_mean, oc_density_uncertainty"
        " FROM overlap_cell"
        " WHERE run_id = %s AND oc_density_mean IS NOT NULL"
        " AND ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
        " ORDER BY lat_index, lon_index",
        (run_id, lon_min, lat_min, lon_max, lat_max),
    ).fetchall()
    return tuple(
        TrawledCell(
            cell=GridCell(lat_index=lat, lon_index=lon),
            fishing_hours_by_gear=_by_gear(trawl_hours, dredge_hours),
            carbon=CarbonDensity(mean=mean, uncertainty=uncertainty),
        )
        for lat, lon, trawl_hours, dredge_hours, mean, uncertainty in rows
    )
