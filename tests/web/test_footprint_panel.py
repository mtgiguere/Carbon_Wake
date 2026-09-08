"""Behavioral contract for the cumulative-footprint block on the map page.

The one headline that needs no preset, shown the only way this project
allows: as a bracket (floor, Poisson union, ceiling) naming its years and
its denominator, with the method's citation, the published comparator, and
the caveats one gesture away. No computed summary -> no block (never a zero).

Written test-first per TDD_CONTRACT.md.
"""

import re
import zipfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.visual, pytest.mark.integration]

_REAL = Path(__file__).parent.parent / "fixtures" / "real"
_CARBON_MEAN = _REAL / "diesing2021" / "OCdensity_quantrf_mean.win60.tif"
_CARBON_UNC = _REAL / "diesing2021" / "OCdensity_quantrf_tot.unc.win60.tif"


def _seed_years(tmp_path, years, *, summarize: bool) -> None:
    from django.db import connection

    from carbon_atlas.db.store import apply_schema
    from carbon_atlas.etl import run_footprint_summary, run_overlap_etl

    year_zip = tmp_path / "fleet-daily.zip"
    with zipfile.ZipFile(year_zip, "w") as archive:
        archive.writestr(
            "day.csv",
            (_REAL / "gfw" / "fleet-daily-100-v3-2012.german-bight-box.csv").read_text(
                encoding="utf-8"
            ),
        )
    connection.ensure_connection()
    apply_schema(connection.connection)
    for year in years:
        run_overlap_etl(
            effort_zip=year_zip,
            carbon_mean=_CARBON_MEAN,
            carbon_uncertainty=_CARBON_UNC,
            conn=connection.connection,
            effort_source=f"panel test {year}",
            carbon_source="Diesing crop",
            effort_year=year,
        )
    if summarize:
        run_footprint_summary(
            conn=connection.connection, carbon_mean=_CARBON_MEAN, carbon_uncertainty=_CARBON_UNC
        )


def test_the_footprint_block_shows_a_bracket_with_years_denominator_and_provenance(
    live_server, transactional_db, tmp_path
):
    from playwright.sync_api import sync_playwright

    _seed_years(tmp_path, [2012, 2013], summarize=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--use-angle=swiftshader"])
        page = browser.new_page(viewport={"width": 1100, "height": 900})
        page.goto(live_server.url + "/?basemap=none")
        page.wait_for_function("window.__atlas && window.__atlas.footprint")

        block = page.locator("#footprint")
        assert block.is_visible()
        text = block.inner_text()
        lower = text.lower()

        # 1. The claim names what it is, its years, and its denominator.
        assert "trawled at least once" in lower
        assert "2012" in text and "2013" in text
        assert "mapped" in lower and "seabed" in lower

        # 2. Three percentages — floor, Poisson union, ceiling — never one.
        assert len(re.findall(r"\d+(\.\d+)?\s?%", text)) >= 3
        assert "floor" in lower and "ceiling" in lower

        # 3. Provenance one gesture away: the method's citation, the published
        #    comparator for the same sea, and the caveats naming aggregation.
        block.locator("details summary").click()
        opened = block.inner_text().lower()
        assert "amoroso" in opened
        assert "42.2" in opened
        assert "aggregat" in opened
        assert "coverage" in opened

        # 4. Everything stays reachable: with the disclosure open the panel
        #    must not run off the viewport (seen on the real page, 2026-09-08:
        #    the caveats slid under the attribution bar). The panel scrolls
        #    instead, and the attribution bar stays clear of it.
        panel_box = page.locator("#panel").bounding_box()
        attrib_box = page.locator("#attrib").bounding_box()
        assert panel_box["y"] + panel_box["height"] <= attrib_box["y"], (panel_box, attrib_box)

        browser.close()


def test_no_summary_means_no_block_not_a_zero(live_server, transactional_db, tmp_path):
    from playwright.sync_api import sync_playwright

    _seed_years(tmp_path, [2012], summarize=False)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--use-angle=swiftshader"])
        page = browser.new_page(viewport={"width": 1100, "height": 900})
        page.goto(live_server.url + "/?basemap=none")
        page.wait_for_function("window.__atlas && window.__atlas.estimate")
        page.wait_for_function("window.__atlas.footprint !== undefined")

        assert page.locator("#footprint").is_hidden()
        assert page.evaluate("window.__atlas.footprint") is None

        browser.close()
