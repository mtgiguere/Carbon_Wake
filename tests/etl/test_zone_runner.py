"""Behavioral contract for the reference-zone runners (ADR-0018).

Two offline steps: load EMODnet's polygons as zones scoped to the carbon
rasters' own region (the same scope rule every run obeys), and measure every
stored run against the zones — farms commissioned before the run's effort
year — storing the per-country result. Wiring only; the arithmetic is the
store's SQL and the pure layer's.

Written test-first per TDD_CONTRACT.md.
"""

import zipfile
from pathlib import Path

import pytest

from carbon_atlas.db.store import list_runs, list_wind_farm_zones, load_zone_contrast
from carbon_atlas.etl import run_overlap_etl, run_wind_farm_zones, run_zone_contrasts
from carbon_atlas.zones import EMODNET_WINDFARMS_SOURCE

pytestmark = pytest.mark.integration

_REAL = Path(__file__).parent.parent / "fixtures" / "real"
_CARBON_MEAN = _REAL / "diesing2021" / "OCdensity_quantrf_mean.win60.tif"
_CARBON_UNC = _REAL / "diesing2021" / "OCdensity_quantrf_tot.unc.win60.tif"
_WINDFARMS = _REAL / "emodnet" / "windfarms_polygons.german-bight.geojson"


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


def test_zones_load_scoped_to_the_carbon_rasters_region_with_the_emodnet_source(conn):
    """The committed crop covers a 30 km box on the German Bight coast; of the
    four producing farms in the sample, none lies inside it — so scoping by
    the rasters' envelope keeps zero, exactly as the effort scope would.
    Widening the region to the real North Sea envelope keeps all four."""
    count = run_wind_farm_zones(
        conn, geojson=_WINDFARMS, carbon_mean=_CARBON_MEAN, carbon_uncertainty=_CARBON_UNC
    )
    assert count == 0
    assert list_wind_farm_zones(conn) == ()

    count = run_wind_farm_zones(
        conn,
        geojson=_WINDFARMS,
        carbon_mean=_CARBON_MEAN,
        carbon_uncertainty=_CARBON_UNC,
        region_margin_deg=1.0,
    )
    zones = list_wind_farm_zones(conn)
    assert count == len(zones) == 4
    assert all(z.source.startswith(EMODNET_WINDFARMS_SOURCE) for z in zones)
    assert "fetched" in zones[0].source  # the snapshot date travels with the rows


def test_every_run_is_measured_against_farms_commissioned_before_its_year(conn, year_zip):
    run_wind_farm_zones(
        conn,
        geojson=_WINDFARMS,
        carbon_mean=_CARBON_MEAN,
        carbon_uncertainty=_CARBON_UNC,
        region_margin_deg=1.0,
    )
    id_2012 = run_overlap_etl(
        effort_zip=year_zip,
        carbon_mean=_CARBON_MEAN,
        carbon_uncertainty=_CARBON_UNC,
        conn=conn,
        effort_source="e",
        carbon_source="c",
        effort_year=2012,
    )
    id_2024 = run_overlap_etl(
        effort_zip=year_zip,
        carbon_mean=_CARBON_MEAN,
        carbon_uncertainty=_CARBON_UNC,
        conn=conn,
        effort_source="e",
        carbon_source="c",
        effort_year=2024,
    )

    measured = run_zone_contrasts(conn)

    assert measured == 2
    r2012 = load_zone_contrast(conn, id_2012)
    r2024 = load_zone_contrast(conn, id_2024)
    assert r2012.cutoff_year == 2011 and r2024.cutoff_year == 2023
    germany_2012 = {m.country: m for m in r2012.rows}["Germany"]
    germany_2024 = {m.country: m for m in r2024.rows}["Germany"]
    # Nordergründe (2017) and Gode Wind 3 (2024) postdate 2011; the two
    # year-unknown farms are counted, never measured.
    assert germany_2012.farms == 0 and germany_2012.farms_without_year == 2
    assert germany_2024.farms == 1 and germany_2024.farms_without_year == 2

    # Idempotent: runs already measured are not re-measured.
    assert run_zone_contrasts(conn) == 0
    assert len(list_runs(conn)) == 2
