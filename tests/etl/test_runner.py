"""Behavioral contract for the full ETL runner — zip to PostGIS in one call.

The runner composes everything below it: stream a year zip, scope effort to
the carbon dataset's own envelope, aggregate, join, store with provenance.
The test archive deliberately mixes the real German Bight fixture with the
real SOUTH ATLANTIC fixture (500 rows near -55S): the run's stored result must
equal the Bight-only ground truth, which proves out-of-region effort is scoped
out by the data-derived envelope rather than surviving as noise.

Written test-first per TDD_CONTRACT.md.
"""

import math
import zipfile
from pathlib import Path

import pytest

from carbon_atlas.db.store import load_overlap
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.etl import run_overlap_etl

pytestmark = pytest.mark.integration

_REAL = Path(__file__).parent.parent / "fixtures" / "real"
_CARBON_MEAN = _REAL / "diesing2021" / "OCdensity_quantrf_mean.win60.tif"
_CARBON_UNC = _REAL / "diesing2021" / "OCdensity_quantrf_tot.unc.win60.tif"


@pytest.fixture
def year_zip(tmp_path):
    """A year archive of two REAL day files: one inside the region (German
    Bight box, 1153 rows), one far outside it (South Atlantic head, 500 rows)."""
    path = tmp_path / "fleet-daily-2012.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name, source in [
            ("day-in-region.csv", _REAL / "gfw" / "fleet-daily-100-v3-2012.german-bight-box.csv"),
            ("day-far-away.csv", _REAL / "gfw" / "fleet-daily-100-v3-2012-02-04.head500.csv"),
        ]:
            archive.writestr(name, source.read_text(encoding="utf-8"))
    return path


def test_the_runner_turns_a_zip_into_a_stored_ground_truth_run(conn, year_zip):
    """One call: the stored run equals the independently pinned Bight ground
    truth (fixtures/real/gfw/README.md) — 220 mapped / 97 unmapped cells,
    139.7554 / 168.4296 h — with the busiest cell's full pairing intact, and
    ZERO trace of the 500 South Atlantic rows that shared the archive."""
    run_id = run_overlap_etl(
        effort_zip=year_zip,
        carbon_mean=_CARBON_MEAN,
        carbon_uncertainty=_CARBON_UNC,
        conn=conn,
        effort_source="GFW fleet-daily v3, 2012 (test archive)",
        carbon_source="Diesing 2021 (committed crop)",
        effort_year=2012,
    )

    result = load_overlap(conn, run_id)

    assert len(result.trawled) == 220
    assert len(result.unmapped_effort) == 97
    assert math.isclose(result.trawled_fishing_hours, 139.7554, rel_tol=1e-9)
    assert math.isclose(result.unmapped_fishing_hours, 168.4296, rel_tol=1e-9)
    assert all(t.cell.lat_index > 0 for t in result.trawled)  # nothing southern survived

    # Gear identity survives storage: all 18.3979 dredge hours in this region
    # sit on unmapped nearshore cells (independent recount, 2026-08-24).
    unmapped_dredge = sum(
        by_gear.get("dredge_fishing", 0.0) for by_gear in result.unmapped_effort.values()
    )
    assert math.isclose(unmapped_dredge, 18.3979, rel_tol=1e-9)

    busiest = max(result.trawled, key=lambda t: t.total_fishing_hours)
    assert busiest.cell == GridCell(lat_index=5390, lon_index=764)
    assert set(busiest.fishing_hours_by_gear) == {"trawlers"}
    assert math.isclose(busiest.fishing_hours_by_gear["trawlers"], 15.0057, rel_tol=1e-9)
    assert math.isclose(busiest.carbon.mean, 1.5652642, rel_tol=1e-6)
    assert math.isclose(busiest.carbon.uncertainty, 2.4579988, rel_tol=1e-6)


def test_the_runner_records_the_callers_provenance(conn, year_zip):
    """The etl_run row carries exactly the sources the caller stated."""
    run_id = run_overlap_etl(
        effort_zip=year_zip,
        carbon_mean=_CARBON_MEAN,
        carbon_uncertainty=_CARBON_UNC,
        conn=conn,
        effort_source="effort-source-text",
        carbon_source="carbon-source-text",
        effort_year=2012,
    )

    row = conn.execute(
        "SELECT effort_source, carbon_source FROM etl_run WHERE id = %s", (run_id,)
    ).fetchone()

    assert row == ("effort-source-text", "carbon-source-text")
