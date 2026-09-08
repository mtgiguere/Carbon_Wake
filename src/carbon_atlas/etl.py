"""The ETL runners: one year of effort + one carbon dataset -> one stored run;
every stored year -> one stored footprint summary.

These are thin compositions at the top of the pipeline — every rule they obey
is owned and tested one layer down:

- effort streams from the year zip (never fully in memory);
- the region scope is the carbon dataset's own WGS84 envelope, derived from
  the rasters — effort outside it could never overlap this carbon layer and is
  out of the run's scope by definition (the run's ``unmapped_effort`` means
  "inside the region, but the carbon model maps nothing there");
- cells are scoped and sampled at the same representative point (the center),
  so scoping and sampling cannot disagree;
- the stored run carries the caller's source citations and the ADR-0009
  effort-layer label;
- the footprint summary (ADR-0017) is computed over the newest run per year,
  each year priced with its own gear profiles, against the mapped seabed area
  the carbon rasters themselves report.
"""

from pathlib import Path

import psycopg

from carbon_atlas.db.store import (
    apply_schema,
    iter_cell_histories,
    list_runs,
    store_footprint_summary,
    store_overlap,
)
from carbon_atlas.disturbance import gear_profiles_for_year
from carbon_atlas.effort.aggregate import aggregate_fishing_hours
from carbon_atlas.footprint import cumulative_footprint
from carbon_atlas.ingest.diesing import DensityRasterPair
from carbon_atlas.ingest.gfw import iter_fleet_daily_zip
from carbon_atlas.overlap import overlap_effort_with_carbon


def run_overlap_etl(
    *,
    effort_zip: Path,
    carbon_mean: Path,
    carbon_uncertainty: Path,
    conn: psycopg.Connection,
    effort_source: str,
    carbon_source: str,
    effort_year: int,
) -> int:
    """Stream, scope, aggregate, join, store. Returns the stored run's id."""
    with DensityRasterPair(carbon_mean, carbon_uncertainty) as pair:
        region = pair.wgs84_envelope()
        effort = aggregate_fishing_hours(
            record
            for record in iter_fleet_daily_zip(effort_zip)
            if region.contains_cell(record.cell)
        )
        result = overlap_effort_with_carbon(effort, pair.sample)

    apply_schema(conn)
    return store_overlap(
        conn,
        result,
        effort_source=effort_source,
        carbon_source=carbon_source,
        effort_year=effort_year,
    )


def run_footprint_summary(
    *, conn: psycopg.Connection, carbon_mean: Path, carbon_uncertainty: Path
) -> int:
    """The cumulative footprint over the newest run of every stored year,
    stored as one summary. Returns the summary's id.

    An offline step, like the runs themselves: a decade of cells streams
    through the pure layer once here rather than on every request. Raises
    when there are no runs — an empty database has no footprint, not a zero.
    """
    apply_schema(conn)  # the summary table may postdate the database (idempotent)
    runs = list_runs(conn)  # newest first
    if not runs:
        raise ValueError("no ETL runs stored; nothing to summarize")
    newest_by_year = {}
    for run in runs:
        newest_by_year.setdefault(run.effort_year, run)
    run_ids = [newest_by_year[year].id for year in sorted(newest_by_year)]
    profiles_by_year = {year: gear_profiles_for_year(year) for year in newest_by_year}

    footprint = cumulative_footprint(iter_cell_histories(conn, run_ids), profiles_by_year)
    with DensityRasterPair(carbon_mean, carbon_uncertainty) as pair:
        mapped_seabed_area_m2 = pair.mapped_area_m2()
    return store_footprint_summary(
        conn, footprint, run_ids=run_ids, mapped_seabed_area_m2=mapped_seabed_area_m2
    )
