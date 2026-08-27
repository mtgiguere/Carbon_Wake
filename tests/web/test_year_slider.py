"""Behavioral contract for the year selector.

With multiple runs loaded, the atlas becomes a time series: the newest year
is the default, and choosing another year swaps EVERYTHING coherently — the
tiles, the status line, and the estimate panel (which titles itself with the
run's own year and prices with that year's fleet, ADR-0016). One run = no
year control; the time axis appears only when it exists.

Written test-first per TDD_CONTRACT.md.
"""

from pathlib import Path

import pytest

pytestmark = [pytest.mark.visual, pytest.mark.integration]

_REAL = Path(__file__).parent.parent / "fixtures" / "real"


def _seed_two_years() -> None:
    from django.db import connection

    from carbon_atlas.carbon.density import CarbonDensity
    from carbon_atlas.db.store import apply_schema, store_overlap
    from carbon_atlas.effort.aggregate import aggregate_fishing_hours
    from carbon_atlas.effort.grid import GridCell
    from carbon_atlas.ingest.diesing import DensityRasterPair
    from carbon_atlas.ingest.gfw import parse_fleet_daily
    from carbon_atlas.overlap import OverlapResult, TrawledCell, overlap_effort_with_carbon

    with (_REAL / "gfw" / "fleet-daily-100-v3-2012.german-bight-box.csv").open(
        encoding="utf-8"
    ) as f:
        effort = aggregate_fishing_hours(parse_fleet_daily(f))
    with DensityRasterPair(
        _REAL / "diesing2021" / "OCdensity_quantrf_mean.win60.tif",
        _REAL / "diesing2021" / "OCdensity_quantrf_tot.unc.win60.tif",
    ) as pair:
        bight = overlap_effort_with_carbon(effort, pair.sample)

    tiny_2024 = OverlapResult(
        trawled=(
            TrawledCell(
                cell=GridCell(lat_index=5390, lon_index=764),
                fishing_hours_by_gear={"trawlers": 42.0},
                carbon=CarbonDensity(mean=1.5652642, uncertainty=2.4579988),
            ),
        ),
        unmapped_effort={},
    )

    connection.ensure_connection()
    apply_schema(connection.connection)
    store_overlap(
        connection.connection, bight, effort_source="y2012", carbon_source="c", effort_year=2012
    )
    store_overlap(
        connection.connection, tiny_2024, effort_source="y2024", carbon_source="c", effort_year=2024
    )


def test_years_swap_coherently_and_the_newest_is_the_default(live_server, transactional_db):
    from playwright.sync_api import sync_playwright

    _seed_two_years()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--use-angle=swiftshader"])
        page = browser.new_page(viewport={"width": 1100, "height": 800})
        page.goto(live_server.url + "/?basemap=none")
        page.wait_for_function("window.__atlas && window.__atlas.estimate")

        # Newest year (2024) is the default everywhere.
        assert page.locator("#year-control").is_visible()
        assert "2024" in page.locator("#year-label").inner_text()
        assert "1 cell" in page.locator("#status").inner_text().replace("1 cells", "1 cell")
        assert "2024" in page.locator("#estimate-range").inner_text()

        # Choosing 2012 swaps tiles, status, and estimate together.
        page.locator("#year-slider").evaluate(
            "el => { el.value = 0; el.dispatchEvent(new Event('input')) }"
        )
        page.wait_for_function("window.__atlas.currentRun.effort_year === 2012")
        assert "2012" in page.locator("#year-label").inner_text()
        assert "220" in page.locator("#status").inner_text()
        page.wait_for_function(
            "window.__atlas.estimate && window.__atlas.estimate.effort_year === 2012"
        )
        assert "2012" in page.locator("#estimate-range").inner_text()

        browser.close()
