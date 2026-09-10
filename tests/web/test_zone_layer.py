"""Behavioral contract for the wind-farm reference-zone layer and its panel
line (ADR-0018).

Blind spot B: the outlines must be VISIBLE as measured pixels, not merely
loaded — the same off/on diff discipline as the effort overlay, judged where
a real farm is. The panel line reads the run's measured contrast per country
and says plainly when a farm could not be measured or a ring saw no effort.
No zones loaded -> no toggle, no line.

Written test-first per TDD_CONTRACT.md.
"""

import io
import zipfile
from pathlib import Path

import pytest
from PIL import Image, ImageChops

pytestmark = [pytest.mark.visual, pytest.mark.integration]

_REAL = Path(__file__).parent.parent / "fixtures" / "real"
_CARBON_MEAN = _REAL / "diesing2021" / "OCdensity_quantrf_mean.win60.tif"
_CARBON_UNC = _REAL / "diesing2021" / "OCdensity_quantrf_tot.unc.win60.tif"
_WINDFARMS = _REAL / "emodnet" / "windfarms_polygons.german-bight.geojson"


def _seed(tmp_path, *, zones: bool) -> None:
    from django.db import connection

    from carbon_atlas.db.store import apply_schema
    from carbon_atlas.etl import run_overlap_etl, run_wind_farm_zones, run_zone_contrasts

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
    run_overlap_etl(
        effort_zip=year_zip,
        carbon_mean=_CARBON_MEAN,
        carbon_uncertainty=_CARBON_UNC,
        conn=connection.connection,
        effort_source="zone layer test",
        carbon_source="Diesing crop",
        effort_year=2024,
    )
    if zones:
        run_wind_farm_zones(
            connection.connection,
            geojson=_WINDFARMS,
            carbon_mean=_CARBON_MEAN,
            carbon_uncertainty=_CARBON_UNC,
            region_margin_deg=1.0,
        )
        run_zone_contrasts(connection.connection)


def _changed_pixels(png_a: bytes, png_b: bytes) -> int:
    a = Image.open(io.BytesIO(png_a)).convert("RGB")
    b = Image.open(io.BytesIO(png_b)).convert("RGB")
    diff = ImageChops.difference(a, b).convert("L")
    return sum(1 for value in diff.tobytes() if value > 16)


def _settle(page, mutation_js: str) -> None:
    page.evaluate(f"{mutation_js}; window.__atlasIdle = false; window.__atlas.map.triggerRepaint()")
    page.wait_for_function("window.__atlasIdle === true")


def test_wind_farm_outlines_are_visible_pixels_and_the_contrast_line_reads_honestly(
    live_server, transactional_db, tmp_path
):
    from playwright.sync_api import sync_playwright

    _seed(tmp_path, zones=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--use-angle=swiftshader"])
        page = browser.new_page(viewport={"width": 900, "height": 700})
        page.goto(live_server.url + "/?basemap=none")
        page.wait_for_function(
            "window.__atlas && window.__atlas.hasOverlay === true && window.__atlas.zones"
            " && window.__atlas.zoneContrast !== undefined"
        )

        # 1. The toggle is present and on by default; the layer is labeled
        #    with its source and license on the page.
        toggle = page.locator("#zones-toggle")
        assert toggle.is_visible() and toggle.is_checked()
        legend = page.locator("#zones-legend").inner_text().lower()
        assert "wind farm" in legend and "emodnet" in legend and "cc-by" in legend

        # 2. Pixels: over Nordergründe (the 3.4 km2 producing farm in the
        #    sample) the outline changes the frame; with zones off and the
        #    effort overlay off the scene is static.
        _settle(page, "window.__atlas.setOverlayVisible(false)")
        _settle(page, "window.__atlas.map.jumpTo({center: [8.166, 53.834], zoom: 12})")
        _settle(page, "window.__atlas.setZonesVisible(false)")
        off_1 = page.screenshot()
        off_2 = page.screenshot()
        _settle(page, "window.__atlas.setZonesVisible(true)")
        on = page.screenshot()
        noise = _changed_pixels(off_1, off_2)
        signal = _changed_pixels(on, off_1)
        assert signal > 10 * noise + 300, f"signal={signal}, noise={noise}"

        # 3. The panel line: 2024 run measured against farms commissioned by
        #    2023 — Germany: 1 farm measured, 2 with an unknown year; the
        #    Bight effort is 30 km away from it, so the ring saw nothing and
        #    the line must say so rather than print a ratio.
        line = page.locator("#zone-contrast")
        assert line.is_visible()
        text = line.inner_text()
        lower = text.lower()
        assert "germany" in lower
        assert "1 farm" in lower
        assert "2" in text and "unknown" in lower
        assert "no effort in the surrounding ring" in lower or "ring saw no effort" in lower
        assert "2023" in text  # the cutoff year is stated
        # The caveats are one gesture away and name the UK exception.
        line.locator("details summary").click()
        assert "united kingdom" in line.inner_text().lower()

        browser.close()


def test_without_zones_there_is_no_toggle_and_no_line(live_server, transactional_db, tmp_path):
    from playwright.sync_api import sync_playwright

    _seed(tmp_path, zones=False)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--use-angle=swiftshader"])
        page = browser.new_page(viewport={"width": 900, "height": 700})
        page.goto(live_server.url + "/?basemap=none")
        page.wait_for_function(
            "window.__atlas && window.__atlas.estimate && window.__atlas.zones"
            " && window.__atlas.zoneContrast !== undefined"
        )

        assert page.evaluate("window.__atlas.zones.count") == 0
        assert page.locator("#zones-control").is_hidden()
        assert page.locator("#zone-contrast").is_hidden()
        assert page.evaluate("window.__atlas.zoneContrast") is None

        browser.close()
