"""Store and load overlap results in PostGIS (ADR-0010).

The store is faithful both ways: an OverlapResult round-trips exactly — both
sides, every value, the deterministic cell order — and every run carries its
provenance (sources, the ADR-0009 effort-layer label verbatim, both sides'
totals). Cell geometry is built in SQL from the integer cell indices, so the
database holds real WGS84 polygons a GiST index can do spatial work on.
"""

from pathlib import Path

import psycopg

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.effort.gears import EFFORT_LAYER_LABEL
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.overlap import OverlapResult, TrawledCell

_SCHEMA = Path(__file__).with_name("schema.sql")

# Bulk load path: COPY the raw values into a session-temp stage, then one
# INSERT..SELECT that builds each cell's polygon in SQL. COPY streams — a
# full-region run is ~370k rows, where a per-row executemany measurably
# stalled; and the stage keeps geometry construction in SQL (ADR-0010).
_CREATE_STAGE = (
    "CREATE TEMP TABLE _overlap_cell_stage (lat_index integer, lon_index integer,"
    " fishing_hours double precision, oc_density_mean double precision,"
    " oc_density_uncertainty double precision)"
)
_COPY_STAGE = (
    "COPY _overlap_cell_stage (lat_index, lon_index, fishing_hours,"
    " oc_density_mean, oc_density_uncertainty) FROM STDIN"
)
_INSERT_FROM_STAGE = (
    "INSERT INTO overlap_cell (run_id, lat_index, lon_index, fishing_hours,"
    " oc_density_mean, oc_density_uncertainty, geom)"
    " SELECT %s, lat_index, lon_index, fishing_hours, oc_density_mean,"
    " oc_density_uncertainty,"
    " ST_MakeEnvelope(lon_index / 100.0, lat_index / 100.0,"
    " (lon_index + 1) / 100.0, (lat_index + 1) / 100.0, 4326)"
    " FROM _overlap_cell_stage"
)
_DROP_STAGE = "DROP TABLE _overlap_cell_stage"


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

    rows = [
        (t.cell.lat_index, t.cell.lon_index, t.fishing_hours, t.carbon.mean, t.carbon.uncertainty)
        for t in result.trawled
    ] + [
        (cell.lat_index, cell.lon_index, hours, None, None)
        for cell, hours in result.unmapped_effort.items()
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


def load_overlap(conn: psycopg.Connection, run_id: int) -> OverlapResult:
    """The stored run's OverlapResult, exactly as it went in.

    Raises ``KeyError`` naming an unknown run id — an empty result must never
    impersonate a real run that found nothing.
    """
    if conn.execute("SELECT 1 FROM etl_run WHERE id = %s", (run_id,)).fetchone() is None:
        raise KeyError(f"no etl_run with id {run_id}")

    rows = conn.execute(
        "SELECT lat_index, lon_index, fishing_hours, oc_density_mean, oc_density_uncertainty"
        " FROM overlap_cell WHERE run_id = %s ORDER BY lat_index, lon_index",
        (run_id,),
    ).fetchall()

    trawled = tuple(
        TrawledCell(
            cell=GridCell(lat_index=lat, lon_index=lon),
            fishing_hours=hours,
            carbon=CarbonDensity(mean=mean, uncertainty=uncertainty),
        )
        for lat, lon, hours, mean, uncertainty in rows
        if mean is not None
    )
    unmapped = {
        GridCell(lat_index=lat, lon_index=lon): hours
        for lat, lon, hours, mean, _ in rows
        if mean is None
    }
    return OverlapResult(trawled=trawled, unmapped_effort=unmapped)


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
        "SELECT lat_index, lon_index, fishing_hours, oc_density_mean, oc_density_uncertainty"
        " FROM overlap_cell"
        " WHERE run_id = %s AND oc_density_mean IS NOT NULL"
        " AND ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
        " ORDER BY lat_index, lon_index",
        (run_id, lon_min, lat_min, lon_max, lat_max),
    ).fetchall()
    return tuple(
        TrawledCell(
            cell=GridCell(lat_index=lat, lon_index=lon),
            fishing_hours=hours,
            carbon=CarbonDensity(mean=mean, uncertainty=uncertainty),
        )
        for lat, lon, hours, mean, uncertainty in rows
    )
