"""Contract for the map page's HTML and assets.

DOM/HTML assertions are NOT visual verification (Blind spot B) — the pixel
test in test_map_pixels.py is what earns the word "visible". These tests pin
what HTML can honestly pin: the page exists, the honesty text is IN it
(the ADR-0009 label verbatim, the full attribution stack), and every asset it
references actually resolves through staticfiles.

Written test-first per TDD_CONTRACT.md.
"""

import pytest
from django.contrib.staticfiles import finders

from carbon_atlas.effort.gears import EFFORT_LAYER_LABEL


@pytest.fixture
def page(client):
    response = client.get("/")
    assert response.status_code == 200
    return response.content.decode("utf-8")


def test_the_page_carries_the_honest_label_verbatim(page):
    """ADR-0009's requirement reaches the frontend: the effort layer's label
    appears in the page exactly as the constant defines it."""
    assert EFFORT_LAYER_LABEL in page


def test_the_page_carries_the_full_attribution_stack(page):
    """GFW (CC BY-NC), Diesing (CC-BY), and OpenStreetMap (ODbL basemap) are
    all attributed on the page itself — ADR-0008's recorded obligation."""
    assert "Global Fishing Watch" in page
    assert "Diesing" in page
    assert "OpenStreetMap" in page


def test_every_referenced_asset_resolves_through_staticfiles(page):
    """The vendored MapLibre files and our atlas.js are both referenced by
    the page and actually findable — a broken reference would render a blank
    map that a DOM test could not distinguish from a working one."""
    for path in (
        "vendor/maplibre/maplibre-gl.js",
        "vendor/maplibre/maplibre-gl.css",
        "atlas.js",
    ):
        assert f"/static/{path}" in page
        assert finders.find(path), f"staticfiles cannot locate {path}"
