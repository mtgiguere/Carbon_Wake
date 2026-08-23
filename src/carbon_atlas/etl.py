"""The ETL runner: one year of effort + one carbon dataset -> one stored run.

This is the thin composition at the top of the pipeline — every rule it obeys
is owned and tested one layer down:

- effort streams from the year zip (never fully in memory);
- the region scope is the carbon dataset's own WGS84 envelope, derived from
  the rasters — effort outside it could never overlap this carbon layer and is
  out of the run's scope by definition (the run's ``unmapped_effort`` means
  "inside the region, but the carbon model maps nothing there");
- cells are scoped and sampled at the same representative point (the center),
  so scoping and sampling cannot disagree;
- the stored run carries the caller's source citations and the ADR-0009
  effort-layer label.
"""

from pathlib import Path

import psycopg

from carbon_atlas.db.store import apply_schema, store_overlap
from carbon_atlas.effort.aggregate import aggregate_fishing_hours
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
    return store_overlap(conn, result, effort_source=effort_source, carbon_source=carbon_source)
