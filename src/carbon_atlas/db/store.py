"""Store and load overlap results in PostGIS (ADR-0010).

The store is faithful both ways: an OverlapResult round-trips exactly — both
sides, every value, the deterministic cell order — and every run carries its
provenance (sources, the ADR-0009 effort-layer label verbatim, both sides'
totals). Cell geometry is built in SQL from the integer cell indices, so the
database holds real WGS84 polygons a GiST index can do spatial work on.
"""

import json
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from itertools import groupby
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.effort.gears import EFFORT_LAYER_LABEL
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.footprint import (
    CellEffortHistory,
    CumulativeFootprint,
    FootprintBracket,
    FootprintFractions,
)
from carbon_atlas.overlap import OverlapResult, TrawledCell


@dataclass(frozen=True)
class RunRecord:
    """One ETL run's provenance row, as stored."""

    id: int
    created_at: datetime
    effort_source: str
    carbon_source: str
    effort_year: int
    effort_layer_label: str
    cells_mapped: int
    cells_unmapped: int
    fishing_hours_mapped: float
    fishing_hours_unmapped: float


_SELECT_RUNS = (
    "SELECT id, created_at, effort_source, carbon_source, effort_year, effort_layer_label,"
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
    effort_year: int,
) -> int:
    """Persist ``result`` as one provenance-carrying run; returns the run id.

    ``effort_year`` is load-bearing provenance: the estimate layer resolves
    that year's gear profiles with it (ADR-0012c).
    """
    run_id = conn.execute(
        "INSERT INTO etl_run (effort_source, carbon_source, effort_year, effort_layer_label,"
        " cells_mapped, cells_unmapped, fishing_hours_mapped, fishing_hours_unmapped)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            effort_source,
            carbon_source,
            effort_year,
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


_TILE_MVT_CELLS = (
    "SELECT ST_AsMVT(tile_rows, 'cells', 4096, 'geom') FROM ("
    " SELECT ST_AsMVTGeom(ST_Transform(geom, 3857), ST_TileEnvelope(%(z)s, %(x)s, %(y)s),"
    "                     4096, 64, true) AS geom,"
    "        lat_index, lon_index, fishing_hours,"
    "        fishing_hours_trawlers, fishing_hours_dredge_fishing,"
    "        oc_density_mean, oc_density_uncertainty,"
    "        ST_Area(geom::geography) / 1e6 AS area_km2,"
    "        (oc_density_mean IS NOT NULL) AS mapped"
    " FROM overlap_cell"
    " WHERE run_id = %(run_id)s"
    "   AND geom && ST_Transform(ST_TileEnvelope(%(z)s, %(x)s, %(y)s), 4326)"
    ") tile_rows WHERE geom IS NOT NULL"
)

# Below z8 a 0.01-degree cell is subpixel; raw cells antialias into
# invisibility (the contract's 0.4px road-layer story). Aggregate to
# 0.1-degree bins per mapped-class, with true seabed area aboard so the style
# colors by hours per km2 at every zoom. The carbon pair does not survive
# aggregation: a bin-average would be a new, unpublished number.
_TILE_MVT_BINS = (
    "SELECT ST_AsMVT(tile_rows, 'cells', 4096, 'geom') FROM ("
    " SELECT ST_AsMVTGeom("
    "          ST_Transform(ST_SetSRID(ST_MakeEnvelope("
    "            bin_lon_index / 10.0, bin_lat_index / 10.0,"
    "            (bin_lon_index + 1) / 10.0, (bin_lat_index + 1) / 10.0), 4326), 3857),"
    "          ST_TileEnvelope(%(z)s, %(x)s, %(y)s), 4096, 64, true) AS geom,"
    "        bin_lat_index, bin_lon_index, mapped, fishing_hours,"
    "        fishing_hours_trawlers, fishing_hours_dredge_fishing, cells, area_km2"
    " FROM ("
    "   SELECT floor(lat_index / 10.0)::int AS bin_lat_index,"
    "          floor(lon_index / 10.0)::int AS bin_lon_index,"
    "          (oc_density_mean IS NOT NULL) AS mapped,"
    "          sum(fishing_hours) AS fishing_hours,"
    "          sum(fishing_hours_trawlers) AS fishing_hours_trawlers,"
    "          sum(fishing_hours_dredge_fishing) AS fishing_hours_dredge_fishing,"
    "          count(*) AS cells,"
    "          sum(ST_Area(geom::geography)) / 1e6 AS area_km2"
    "   FROM overlap_cell"
    "   WHERE run_id = %(run_id)s"
    "     AND geom && ST_Transform(ST_TileEnvelope(%(z)s, %(x)s, %(y)s), 4326)"
    "   GROUP BY 1, 2, 3"
    " ) binned"
    ") tile_rows WHERE geom IS NOT NULL"
)

#: Below this zoom, tiles aggregate to 0.1-degree bins.
CELL_TILE_MIN_ZOOM = 8


def cells_tile_mvt(conn: psycopg.Connection, run_id: int, *, z: int, x: int, y: int) -> bytes:
    """One slippy tile of the run's cells as Mapbox Vector Tile bytes.

    PostGIS builds the tile (ST_AsMVT over the GiST-indexed geometry) — a
    rendering-format encoder, not science. The 'cells' layer carries BOTH
    sides of the join: per-gear hours (a gear with no record contributes no
    key — absence stays distinct from zero, ADR-0013), the carbon pair on
    mapped cells only, and a `mapped` flag so the style can honor the
    "unmapped is not zero" rule visually (ADR-0015). An empty tile is empty
    bytes; an unknown run raises, naming itself.
    """
    if conn.execute("SELECT 1 FROM etl_run WHERE id = %s", (run_id,)).fetchone() is None:
        raise KeyError(f"no etl_run with id {run_id}")
    query = _TILE_MVT_CELLS if z >= CELL_TILE_MIN_ZOOM else _TILE_MVT_BINS
    row = conn.execute(query, {"run_id": run_id, "z": z, "x": x, "y": y}).fetchone()
    return bytes(row[0]) if row[0] is not None else b""


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


# ---------------------------------------------------------------------------
# The cross-year view and the footprint summary (ADR-0017)
# ---------------------------------------------------------------------------

_SELECT_HISTORIES = (
    "SELECT c.lat_index, c.lon_index, r.effort_year, c.fishing_hours_trawlers,"
    " c.fishing_hours_dredge_fishing, c.oc_density_mean IS NOT NULL"
    " FROM overlap_cell c JOIN etl_run r ON r.id = c.run_id"
    " WHERE c.run_id = ANY(%s)"
    " ORDER BY c.lat_index, c.lon_index, r.effort_year"
)


def iter_cell_histories(
    conn: psycopg.Connection, run_ids: Sequence[int]
) -> Iterator[CellEffortHistory]:
    """Every cell touched by any of ``run_ids``, its per-gear hours keyed by
    each run's effort year — streamed in cell order through a server-side
    cursor, because a decade of runs is millions of rows.

    Refuses an empty request, an unknown run (KeyError naming it), and two
    runs sharing a year (a cell cannot have two histories for one year;
    choosing silently would hide the ambiguity). A cell mapped in one run
    and unmapped in another means the runs used different carbon layers —
    refused too.
    """
    ids = list(run_ids)
    if not ids:
        raise ValueError("at least one run id is required")
    year_by_run = dict(
        conn.execute("SELECT id, effort_year FROM etl_run WHERE id = ANY(%s)", (ids,)).fetchall()
    )
    missing = sorted(set(ids) - set(year_by_run))
    if missing:
        raise KeyError(f"no etl_run with id(s) {', '.join(map(str, missing))}")
    shared = sorted(year for year, count in Counter(year_by_run.values()).items() if count > 1)
    if shared:
        raise ValueError(f"more than one run for effort year(s) {shared}; pass one run per year")

    # WITH HOLD: the cursor must work on an autocommit connection (the ETL's)
    # as well as inside Django's transaction; it is consumed and closed here.
    with conn.cursor(name="carbon_atlas_cell_histories", withhold=True) as cursor:
        cursor.itersize = 50_000
        cursor.execute(_SELECT_HISTORIES, (ids,))
        for (lat, lon), group in groupby(cursor, key=lambda row: (row[0], row[1])):
            rows = list(group)
            mapped_flags = {row[5] for row in rows}
            if len(mapped_flags) != 1:
                raise ValueError(
                    f"cell ({lat}, {lon}) is mapped in some runs and unmapped in others; "
                    f"the runs do not share a carbon layer"
                )
            yield CellEffortHistory(
                cell=GridCell(lat_index=lat, lon_index=lon),
                mapped=mapped_flags.pop(),
                hours_by_year={row[2]: _by_gear(row[3], row[4]) for row in rows},
            )


@dataclass(frozen=True)
class FootprintSummaryRecord:
    """One stored footprint computation, as the API serves it."""

    id: int
    computed_at: datetime
    run_ids: tuple[int, ...]
    years: tuple[int, ...]
    cells: int
    mapped_seabed_area_m2: float
    mapped: FootprintBracket
    all_effort: FootprintBracket
    per_year_mapped_m2: dict[int, float]

    @property
    def fractions(self) -> FootprintFractions:
        """The mapped bracket over the mapped seabed — through the pure
        layer's own division, so there is one place it happens."""
        return CumulativeFootprint(
            years=self.years,
            cells=self.cells,
            mapped=self.mapped,
            all_effort=self.all_effort,
            per_year_mapped_m2=self.per_year_mapped_m2,
        ).mapped_fraction(mapped_seabed_area_m2=self.mapped_seabed_area_m2)


_SELECT_SUMMARY = (
    "SELECT id, computed_at, run_ids, years, cells, mapped_seabed_area_m2,"
    " mapped_lower_m2, mapped_poisson_m2, mapped_upper_m2,"
    " all_lower_m2, all_poisson_m2, all_upper_m2, per_year_mapped_m2"
    " FROM footprint_summary"
)


def store_footprint_summary(
    conn: psycopg.Connection,
    footprint: CumulativeFootprint,
    *,
    run_ids: Sequence[int],
    mapped_seabed_area_m2: float,
) -> int:
    """Persist one footprint computation with the runs it was built from and
    the denominator it should be read against. Returns the summary id."""
    row = conn.execute(
        "INSERT INTO footprint_summary (run_ids, years, cells, mapped_seabed_area_m2,"
        " mapped_lower_m2, mapped_poisson_m2, mapped_upper_m2,"
        " all_lower_m2, all_poisson_m2, all_upper_m2, per_year_mapped_m2)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            list(run_ids),
            list(footprint.years),
            footprint.cells,
            mapped_seabed_area_m2,
            footprint.mapped.lower_m2,
            footprint.mapped.poisson_m2,
            footprint.mapped.upper_m2,
            footprint.all_effort.lower_m2,
            footprint.all_effort.poisson_m2,
            footprint.all_effort.upper_m2,
            Jsonb({str(year): area for year, area in footprint.per_year_mapped_m2.items()}),
        ),
    ).fetchone()
    return row[0]


def latest_footprint_summary(conn: psycopg.Connection) -> FootprintSummaryRecord | None:
    """The newest stored footprint, or None when none has been computed —
    the honest empty state, never a zero."""
    row = conn.execute(_SELECT_SUMMARY + " ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    # Django's connection registers a text loader for jsonb (JSONField decodes
    # itself); a plain psycopg connection decodes to a dict. Accept both.
    per_year = row[12] if isinstance(row[12], dict) else json.loads(row[12])
    return FootprintSummaryRecord(
        id=row[0],
        computed_at=row[1],
        run_ids=tuple(row[2]),
        years=tuple(row[3]),
        cells=row[4],
        mapped_seabed_area_m2=row[5],
        mapped=FootprintBracket(lower_m2=row[6], poisson_m2=row[7], upper_m2=row[8]),
        all_effort=FootprintBracket(lower_m2=row[9], poisson_m2=row[10], upper_m2=row[11]),
        per_year_mapped_m2={int(year): area for year, area in per_year.items()},
    )
