"""Behavioral contract for the offline footprint runner (ADR-0017).

One call: pick the newest run per year, stream every cell's history, price
each year with its own gear profiles, take the mapped seabed area from the
carbon rasters themselves, and store the bracketed result. The stored summary
must equal what the pure layer computes from the same rows — the runner is
wiring, never a second copy of the arithmetic.

Written test-first per TDD_CONTRACT.md.
"""

import math
import zipfile
from pathlib import Path

import pytest

from carbon_atlas.db.store import (
    iter_cell_histories,
    latest_footprint_summary,
    list_runs,
)
from carbon_atlas.disturbance import gear_profiles_for_year
from carbon_atlas.etl import run_footprint_summary, run_overlap_etl
from carbon_atlas.footprint import cumulative_footprint
from carbon_atlas.ingest.diesing import DensityRasterPair

pytestmark = pytest.mark.integration

_REAL = Path(__file__).parent.parent / "fixtures" / "real"
_CARBON_MEAN = _REAL / "diesing2021" / "OCdensity_quantrf_mean.win60.tif"
_CARBON_UNC = _REAL / "diesing2021" / "OCdensity_quantrf_tot.unc.win60.tif"


@pytest.fixture
def year_zip(tmp_path):
    path = tmp_path / "fleet-daily.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "day.csv",
            (_REAL / "gfw" / "fleet-daily-100-v3-2012.german-bight-box.csv").read_text(
                encoding="utf-8"
            ),
        )
    return path


def _run(conn, year_zip, year):
    return run_overlap_etl(
        effort_zip=year_zip,
        carbon_mean=_CARBON_MEAN,
        carbon_uncertainty=_CARBON_UNC,
        conn=conn,
        effort_source=f"test {year}",
        carbon_source="Diesing crop",
        effort_year=year,
    )


def test_the_runner_stores_the_pure_layers_footprint_over_the_newest_run_per_year(conn, year_zip):
    """Three runs — 2012, a superseded 2013, a newer 2013 — become one summary
    over (2012, newest 2013): the same bracket the pure layer computes from
    the same histories, and the denominator the crop's own mapped pixels
    give (1868 x 500 m x 500 m)."""
    id_2012 = _run(conn, year_zip, 2012)
    _run(conn, year_zip, 2013)  # superseded
    id_2013 = _run(conn, year_zip, 2013)

    summary_id = run_footprint_summary(
        conn=conn, carbon_mean=_CARBON_MEAN, carbon_uncertainty=_CARBON_UNC
    )
    record = latest_footprint_summary(conn)

    assert record.id == summary_id
    assert record.run_ids == (id_2012, id_2013)
    assert record.years == (2012, 2013)
    assert len(list_runs(conn)) == 3  # the superseded run is kept, just not used

    expected = cumulative_footprint(
        iter_cell_histories(conn, [id_2012, id_2013]),
        {2012: gear_profiles_for_year(2012), 2013: gear_profiles_for_year(2013)},
    )
    assert record.cells == expected.cells == 220 + 97  # mapped + unmapped Bight cells
    assert record.mapped == expected.mapped
    assert record.all_effort == expected.all_effort
    assert record.per_year_mapped_m2 == expected.per_year_mapped_m2
    with DensityRasterPair(_CARBON_MEAN, _CARBON_UNC) as pair:
        assert record.mapped_seabed_area_m2 == pair.mapped_area_m2()
    assert math.isclose(record.mapped_seabed_area_m2, 1868 * 500 * 500, rel_tol=1e-9)

    # Two identical years: the union exceeds either year alone but the
    # bracket holds — floor (one year) < Poisson union < ceiling (two years).
    assert record.mapped.lower_m2 < record.mapped.poisson_m2 < record.mapped.upper_m2
    assert 0.0 < record.fractions.poisson < 1.0


def test_a_single_year_summary_collapses_to_adr_0014s_footprint(conn, year_zip):
    _run(conn, year_zip, 2012)

    run_footprint_summary(conn=conn, carbon_mean=_CARBON_MEAN, carbon_uncertainty=_CARBON_UNC)
    record = latest_footprint_summary(conn)

    assert record.years == (2012,)
    assert record.mapped.lower_m2 == record.mapped.poisson_m2 == record.mapped.upper_m2
    assert record.per_year_mapped_m2 == {2012: record.mapped.poisson_m2}


def test_no_runs_means_no_summary_not_a_zero(conn):
    with pytest.raises(ValueError, match="no ETL runs"):
        run_footprint_summary(conn=conn, carbon_mean=_CARBON_MEAN, carbon_uncertainty=_CARBON_UNC)
    assert latest_footprint_summary(conn) is None
