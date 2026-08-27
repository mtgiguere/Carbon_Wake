"""Behavioral contract for the estimate panel and preset slider.

The interaction this project exists for, under the visual-honesty policy
(docs/SHOWCASE_SPIKE.md §3): THE RANGE IS THE DEFAULT VIEW, with both ends
attributed; a single preset is an explicit user choice, visibly labeled, with
its citation, its derived/quoted flag, and an atmospheric figure only where
the source quantified one. DOM assertions are appropriate here — the panel is
text, not WebGL (the canvas overlay keeps its pixel guard).

Written test-first per TDD_CONTRACT.md.
"""

from pathlib import Path

import pytest

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
        effort_source="panel test",
        carbon_source="panel test",
        effort_year=2012,
    )


def test_the_range_is_the_default_view_and_a_preset_is_an_explicit_labeled_choice(
    live_server, transactional_db
):
    """Loads the real page over a real seeded run and walks the whole
    honesty contract of the panel."""
    from playwright.sync_api import sync_playwright

    _seed_real_run()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--use-angle=swiftshader"])
        page = browser.new_page(viewport={"width": 1100, "height": 800})
        page.goto(live_server.url + "/?basemap=none")
        page.wait_for_function("window.__atlas && window.__atlas.estimate")

        panel = page.locator("#estimate")

        # 1. The RANGE is the default view, both ends attributed by name, and
        #    the low end visibly flagged as inferred (Hiddink published a
        #    factor, not a number).
        assert panel.locator("#estimate-range").is_visible()
        range_text = panel.locator("#estimate-range").inner_text()
        assert "Hiddink" in range_text
        assert "Sala" in range_text
        assert "inferred" in range_text.lower()

        # 2. Moving the slider is an explicit single-preset choice: the view
        #    switches, labeled with the preset's own label and citation DOI.
        page.locator("#preset-slider").evaluate(
            "el => { el.value = 0; el.dispatchEvent(new Event('input')) }"
        )
        detail = panel.locator("#preset-detail").inner_text()
        assert "Hiddink" in detail
        assert "10.1038/s41586-023-06014-7" in detail
        assert "inferred" in detail.lower()

        # 3. The Sala stop reports atmospheric CO2 as UNKNOWN — the source
        #    called it that; the panel must not invent a figure. It also
        #    shows the EXACT tonne count with separators: compact units alone
        #    once hid the 1000x disagreement behind one letter (3.98 kt vs
        #    3.98 Mt), which the owner read as "the slider changes nothing".
        #    And it states the map-invariance fact instead of leaving the
        #    user to wonder why the map did not move.
        max_index = page.locator("#preset-slider").evaluate("el => el.max")
        page.locator("#preset-slider").evaluate(
            f"el => {{ el.value = {max_index}; el.dispatchEvent(new Event('input')) }}"
        )
        sala = panel.locator("#preset-detail").inner_text()
        assert "Sala" in sala
        assert "10.1038/s41586-021-03371-z" in sala
        assert "unknown" in sala.lower()
        import re

        assert re.search(r"\(\d{1,3}(,\d{3})+ t\)", sala), sala  # exact tonnes, separated
        assert "spatial pattern does not change" in sala

        # 4. And the user can always return to the honest default.
        page.locator("#show-range").click()
        assert panel.locator("#estimate-range").is_visible()

        # 5. A single run means no time axis: the year control stays hidden.
        assert not page.locator("#year-control").is_visible()

        # 6. The caveats travel with the number, one gesture away (the
        #    policy's rule): opening the disclosure reveals the saturation
        #    bound's own assumptions and the coverage line.
        panel.locator("#caveats summary").click()
        caveats = panel.locator("#caveats").inner_text().lower()
        assert "saturation" in caveats
        assert "mapped" in caveats

        browser.close()
