"""Blind spot B, exercised for real: does the overlay actually DRAW?

DOM assertions prove a layer loaded; only pixels prove a human can see it
(TDD_CONTRACT.md, Blind spot B). This test renders the real page in headless
Chromium on software WebGL (SwiftShader), over the real German Bight fixture
data, with ?basemap=none so zero third-party network is involved — and
asserts on a pixel DIFF between overlay-off and overlay-on.

Blind spot C compliance: both the noise floor (two overlay-off screenshots of
a static scene) and the signal (off vs on) are MEASURED in this test, and the
assertion requires the signal to clear ten times the measured noise plus a
fixed floor — the threshold provably sits in the gap. The guard was also
RED-demoed: asserting against a second overlay-off screenshot (instead of the
overlay-on one) fails loudly, so the passing run is evidence, not decoration.

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
        connection.connection, result, effort_source="pixel test", carbon_source="pixel test"
    )


def _changed_pixels(png_a: bytes, png_b: bytes) -> int:
    """Pixels whose max per-channel difference exceeds 16/255 — well above
    PNG/encoder jitter, well below any real fill color against the blank
    background."""
    a = Image.open(io.BytesIO(png_a)).convert("RGB")
    b = Image.open(io.BytesIO(png_b)).convert("RGB")
    diff = ImageChops.difference(a, b).convert("L")
    return sum(1 for value in diff.tobytes() if value > 16)


def _settle(page, mutation_js: str) -> None:
    """Apply a map mutation and wait until the map has RENDERED it.

    Waiting on a bare idle flag races: after a mutation, the flag is still
    true from the PREVIOUS idle until the next 'render' event fires, so a
    fast checker sees stale-true and screenshots a pre-render frame. (CI
    caught exactly that: signal=0 because the 'on' screenshot preceded the
    repaint; local runs had passed on timing luck.) Resetting the flag and
    forcing a repaint in the SAME evaluate makes the wait deterministic —
    'idle' then fires only after all tiles are loaded and drawn.
    """
    page.evaluate(f"{mutation_js}; window.__atlasIdle = false; window.__atlas.map.triggerRepaint()")
    page.wait_for_function("window.__atlasIdle === true")


def test_the_overlay_is_visible_as_measured_pixels(live_server, transactional_db):
    """Rendering the real German Bight cells changes thousands of pixels
    relative to the same scene without the overlay, while two overlay-off
    frames of the static scene differ by ~none."""
    from playwright.sync_api import sync_playwright

    _seed_real_run()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--use-angle=swiftshader"])
        page = browser.new_page(viewport={"width": 900, "height": 700})
        page.goto(live_server.url + "/?basemap=none")
        page.wait_for_function("window.__atlas && window.__atlas.hasOverlay === true")
        # Dive to the fixture's German Bight footprint so the cells fill the
        # frame — the overlay must be judged where the data is.
        _settle(page, "window.__atlas.map.jumpTo({center: [7.6, 53.79], zoom: 9})")

        _settle(page, "window.__atlas.setOverlayVisible(false)")
        off_1 = page.screenshot()
        off_2 = page.screenshot()

        _settle(page, "window.__atlas.setOverlayVisible(true)")
        on = page.screenshot()
        browser.close()

    noise = _changed_pixels(off_1, off_2)
    signal = _changed_pixels(on, off_1)

    # Both sides measured (Blind spot C): the scene is static with the
    # overlay off, so noise is ~0; 317 real cells at z9 paint thousands of
    # pixels. The threshold must sit provably between them.
    assert signal > 10 * noise + 2000, f"signal={signal}, noise={noise}"
