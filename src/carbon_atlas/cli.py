"""``python -m carbon_atlas`` - the data-ops commands (RIGOR.md rule 7).

Wiring only: each command opens a connection and calls the tested runners
with the canonical provenance strings. What used to be scratchpad shell and
runbook snippets is now testable, idempotent, and honest about failure
(exit 2 with the reason on stderr).
"""

import argparse
import json
import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from urllib.request import urlopen

import psycopg

from carbon_atlas.dataops import (
    CARBON_SOURCE_TEXT,
    ChecksumError,
    effort_source_text,
    fetch_verified,
    fleet_daily_key,
    parse_zenodo_manifest,
)
from carbon_atlas.db.store import list_runs, list_wind_farm_zones
from carbon_atlas.etl import (
    run_footprint_summary,
    run_overlap_etl,
    run_wind_farm_zones,
    run_zone_contrasts,
)

DEFAULT_DSN = os.environ.get(
    "CARBON_ATLAS_DB_URL", "postgresql://carbon_atlas:carbon_atlas_dev@localhost:5434/carbon_atlas"
)
DEFAULT_DATA_DIR = Path("data/gfw")
DEFAULT_DIESING_DIR = Path("data/diesing2021/Diesing_2021")
ZENODO_RECORD_URL = "https://zenodo.org/api/records/14982712"


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dsn", default=DEFAULT_DSN, help="PostGIS DSN (default: $CARBON_ATLAS_DB_URL)"
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="GFW year zips")
    parser.add_argument(
        "--carbon-mean", type=Path, default=DEFAULT_DIESING_DIR / "OCdensity_quantrf_mean.tif"
    )
    parser.add_argument(
        "--carbon-uncertainty",
        type=Path,
        default=DEFAULT_DIESING_DIR / "OCdensity_quantrf_tot.unc.tif",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m carbon_atlas", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    etl = commands.add_parser("etl-year", help="load one GFW year against the carbon rasters")
    etl.add_argument("year", type=int)
    etl.set_defaults(func=_etl_year)

    fetch = commands.add_parser("fetch-year", help="download one year zip, verified by MD5")
    fetch.add_argument("year", type=int)
    fetch.add_argument("--manifest-file", type=Path, help="saved Zenodo record JSON (else fetched)")
    fetch.set_defaults(func=_fetch_year)

    footprint = commands.add_parser("footprint", help="recompute the cumulative footprint summary")
    footprint.set_defaults(func=_footprint)

    zones = commands.add_parser("zones", help="load EMODnet wind-farm polygons as reference zones")
    zones.add_argument("geojson", type=Path)
    zones.add_argument(
        "--region-margin", type=float, default=0.0, help="degrees beyond the envelope"
    )
    zones.set_defaults(func=_zones)

    contrasts = commands.add_parser(
        "zone-contrasts", help="measure unmeasured runs against the zones"
    )
    contrasts.set_defaults(func=_zone_contrasts)

    backfill = commands.add_parser(
        "backfill", help="fetch (verified), load, and refresh summaries for a span of years"
    )
    backfill.add_argument("first", type=int)
    backfill.add_argument("last", type=int)
    backfill.add_argument(
        "--manifest-file", type=Path, help="saved Zenodo record JSON (else fetched)"
    )
    backfill.set_defaults(func=_backfill)

    for sub in (etl, fetch, footprint, zones, contrasts, backfill):
        _add_common(sub)
    return parser


def _loaded_years(conn: psycopg.Connection) -> dict[int, int]:
    """effort_year -> newest run id."""
    years: dict[int, int] = {}
    for run in list_runs(conn):  # newest first
        years.setdefault(run.effort_year, run.id)
    return years


def _load_year(conn: psycopg.Connection, args: argparse.Namespace, year: int) -> None:
    loaded = _loaded_years(conn)
    if year in loaded:
        print(f"{year}: already loaded (run {loaded[year]})")
        return
    zip_path = args.data_dir / fleet_daily_key(year)
    if not zip_path.is_file():
        raise FileNotFoundError(f"missing year zip {zip_path}")
    run_id = run_overlap_etl(
        effort_zip=zip_path,
        carbon_mean=args.carbon_mean,
        carbon_uncertainty=args.carbon_uncertainty,
        conn=conn,
        effort_source=effort_source_text(year),
        carbon_source=CARBON_SOURCE_TEXT,
        effort_year=year,
    )
    conn.commit()
    print(f"{year}: stored run {run_id}")


def _etl_year(args: argparse.Namespace) -> int:
    with psycopg.connect(args.dsn) as conn:
        _load_year(conn, args, args.year)
    return 0


def _manifest(args: argparse.Namespace) -> dict:
    if args.manifest_file is not None:
        record = json.loads(args.manifest_file.read_text(encoding="utf-8"))
    else:
        # B310: the URL is a module constant over https, never user input.
        with urlopen(ZENODO_RECORD_URL, timeout=120) as response:  # nosec B310
            record = json.load(response)
    return parse_zenodo_manifest(record)


def _fetch(args: argparse.Namespace, manifest: dict, year: int) -> None:
    key = fleet_daily_key(year)
    if key not in manifest:
        raise ValueError(f"{key} is not in the Zenodo record")
    args.data_dir.mkdir(parents=True, exist_ok=True)
    outcome = fetch_verified(manifest[key], args.data_dir / key, opener=urlopen, sleep=time.sleep)
    print(f"{year}: {outcome}")


def _fetch_year(args: argparse.Namespace) -> int:
    _fetch(args, _manifest(args), args.year)
    return 0


def _refresh_footprint(conn: psycopg.Connection, args: argparse.Namespace) -> None:
    summary_id = run_footprint_summary(
        conn=conn, carbon_mean=args.carbon_mean, carbon_uncertainty=args.carbon_uncertainty
    )
    conn.commit()
    print(f"footprint summary {summary_id} stored")


def _footprint(args: argparse.Namespace) -> int:
    with psycopg.connect(args.dsn) as conn:
        _refresh_footprint(conn, args)
    return 0


def _zones(args: argparse.Namespace) -> int:
    with psycopg.connect(args.dsn) as conn:
        count = run_wind_farm_zones(
            conn,
            geojson=args.geojson,
            carbon_mean=args.carbon_mean,
            carbon_uncertainty=args.carbon_uncertainty,
            region_margin_deg=args.region_margin,
        )
        conn.commit()
    print(f"{count} reference zones stored from {args.geojson.name}")
    return 0


def _measure_contrasts(conn: psycopg.Connection) -> None:
    measured = run_zone_contrasts(conn)
    conn.commit()
    print(f"zone contrasts: measured {measured} run(s)")


def _zone_contrasts(args: argparse.Namespace) -> int:
    with psycopg.connect(args.dsn) as conn:
        _measure_contrasts(conn)
    return 0


def _backfill(args: argparse.Namespace) -> int:
    manifest = _manifest(args)
    with psycopg.connect(args.dsn) as conn:
        for year in range(args.first, args.last + 1):
            if year in _loaded_years(conn):
                print(f"{year}: already loaded")
                continue
            _fetch(args, manifest, year)
            _load_year(conn, args, year)
        _refresh_footprint(conn, args)
        if list_wind_farm_zones(conn):
            _measure_contrasts(conn)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, ChecksumError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
