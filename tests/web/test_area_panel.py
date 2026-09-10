"""Behavioral contract for "draw your own area" (IDEAS.md #1).

The visitor arms the draw tool, drags a box on the map with the mouse — the
real gesture, not a test hook — and the panel switches to THAT box's estimate:
the same cited range, titled as the area's, with the cell count and the
displacement caveat, and a way back to the whole region. The box is drawn on
the map as measured pixels.

Written test-first per TDD_CONTRACT.md.
"""

import io
from pathlib import Path

import pytest
from PIL import Image, ImageChops

pytestmark = [pytest.mark.visual, pytest.mark.integration]

_REAL = Path(__file__).parent.parent / "fixtures" / "real"


def _seed_real_run() -> None:
    from django.db import connection

    from carbon_atlas.db.store import apply_schema, store_overlap
    from carbon_atlas.effort.aggregate import aggregate_fishing_hours
    from carbon_atlas.ingest.diesing import DensityRasterPair
    from carbon_atlas.ingest.gfw import parse_fleet_daily
    from carbon_atlas.overlap import overlap_effort_with_carbon

    with (_REAL / "gfw" / "fleet-daily-100-v3-2012.german-bight-box.csv").open(
        encoding="utf-8"
    ) as f:
        effort = aggregate_fishing_hours(parse_fleet_daily(f))
    with DensityRasterPair(
        _REAL / "diesing2021" / "OCdensity_quantrf_mean.win60.tif",
        _REAL / "diesing2021" / "OCdensity_quantrf_tot.unc.win60.tif",
    ) as pair:
        result = overlap_effort_with_carbon(effort, pair.sample)
    connection.ensure_connection()
    apply_schema(connection.connection)
    store_overlap(
        connection.connection,
        result,
        effort_source="area test",
        carbon_source="c",
        effort_year=2012,
    )


_MAP_REGION = (420, 0, 1100, 800)  # right of the panel: the map itself


def _changed_pixels(png_a: bytes, png_b: bytes) -> int:
    """Pixels that changed on the MAP (the panel is text, judged by DOM)."""
    a = Image.open(io.BytesIO(png_a)).convert("RGB").crop(_MAP_REGION)
    b = Image.open(io.BytesIO(png_b)).convert("RGB").crop(_MAP_REGION)
    return sum(1 for v in ImageChops.difference(a, b).convert("L").tobytes() if v > 16)


def _settle(page, mutation_js: str) -> None:
    page.evaluate(f"{mutation_js}; window.__atlasIdle = false; window.__atlas.map.triggerRepaint()")
    page.wait_for_function("window.__atlasIdle === true")


def test_dragging_a_box_estimates_that_area_and_the_visitor_can_return(
    live_server, transactional_db
):
    from playwright.sync_api import sync_playwright

    _seed_real_run()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--use-angle=swiftshader"])
        page = browser.new_page(viewport={"width": 1100, "height": 800})
        page.goto(live_server.url + "/?basemap=none")
        page.wait_for_function("window.__atlas && window.__atlas.estimate")
        _settle(page, "window.__atlas.map.jumpTo({center: [7.6, 53.79], zoom: 9})")
        region_title = page.locator("#estimate-range strong").inner_text()

        # 1. Arm the tool, then drag on the map canvas — from the panel's
        #    right edge into the sea so the gesture lands on the map itself.
        before = page.screenshot()
        page.locator("#draw-area").click()
        assert "drag" in page.locator("#status").inner_text().lower()
        canvas = page.locator("#map canvas").first
        box = canvas.bounding_box()
        x0, y0 = box["x"] + 600, box["y"] + 250
        x1, y1 = x0 + 220, y0 + 160
        page.mouse.move(x0, y0)
        page.mouse.down()
        page.mouse.move(x0 + 110, y0 + 80, steps=5)
        page.mouse.move(x1, y1, steps=5)
        page.mouse.up()
        page.wait_for_function("window.__atlas.area && window.__atlas.area.estimate")

        # 2. The panel is now the AREA's estimate: titled as such, with the
        #    box's cell count and the displacement caveat, the same range
        #    machinery underneath (both ends attributed), and the payload
        #    says which bbox it covers.
        area_text = page.locator("#estimate-range").inner_text()
        assert "your area" in area_text.lower()
        assert area_text != region_title
        assert "Hiddink" in area_text and "Sala" in area_text
        assert "cells" in area_text.lower()
        area = page.evaluate("window.__atlas.area.estimate.area")
        assert area["cells_mapped"] >= 1
        assert area["bbox"]["lon_min"] < area["bbox"]["lon_max"]
        assert area["bbox"]["lat_min"] < area["bbox"]["lat_max"]
        page.locator("#caveats summary").click()
        assert "displace" in page.locator("#caveats").inner_text().lower()

        # 3. The box itself is visible on the map (measured pixels vs before).
        _settle(page, "window.__atlas.map.triggerRepaint()")
        after = page.screenshot()
        assert _changed_pixels(after, before) > 300

        # 4. Back to the whole region: the region's title returns, the box is
        #    gone, and the area state is cleared.
        page.locator("#clear-area").click()
        page.wait_for_function("window.__atlas.area === null")
        assert page.locator("#estimate-range strong").inner_text() == region_title
        _settle(page, "window.__atlas.map.triggerRepaint()")
        assert _changed_pixels(page.screenshot(), before) < 300

        browser.close()


def test_a_click_without_a_drag_draws_nothing_and_changes_nothing(live_server, transactional_db):
    from playwright.sync_api import sync_playwright

    _seed_real_run()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--use-angle=swiftshader"])
        page = browser.new_page(viewport={"width": 1100, "height": 800})
        page.goto(live_server.url + "/?basemap=none")
        page.wait_for_function("window.__atlas && window.__atlas.estimate")
        title = page.locator("#estimate-range strong").inner_text()

        page.locator("#draw-area").click()
        canvas = page.locator("#map canvas").first
        box = canvas.bounding_box()
        page.mouse.click(box["x"] + 700, box["y"] + 300)
        page.wait_for_timeout(500)

        assert page.evaluate("window.__atlas.area") is None
        assert page.locator("#estimate-range strong").inner_text() == title

        browser.close()
