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


def test_runserver_works_out_of_the_box():
    """With no environment configured, `manage.py runserver` must serve on
    localhost — Django refuses to run with DEBUG=False and empty
    ALLOWED_HOSTS, and the project owner hit exactly that. (Tests alone can't
    catch it: the test harness appends 'testserver' itself.) Deployment
    overrides via CARBON_ATLAS_ALLOWED_HOSTS."""
    from django.conf import settings

    assert "localhost" in settings.ALLOWED_HOSTS
    assert "127.0.0.1" in settings.ALLOWED_HOSTS


def test_static_assets_are_actually_served_over_http(client):
    """finders.find proves an asset EXISTS; only an HTTP 200 through the real
    middleware stack proves it is SERVED. The gap between the two is exactly
    what shipped: with DEBUG=False, bare runserver serves no static at all —
    maplibre-gl.js 404'd and the owner got a white page stuck at 'loading…'.
    WhiteNoise closes it in every mode."""
    for path in (
        "/static/vendor/maplibre/maplibre-gl.js",
        "/static/vendor/maplibre/maplibre-gl.css",
        "/static/atlas.js",
    ):
        response = client.get(path)
        assert response.status_code == 200, f"{path} -> {response.status_code}"
        response.close()  # WhiteNoise streams the file; leaving it open leaks the handle


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
