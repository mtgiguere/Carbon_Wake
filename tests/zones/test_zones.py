"""Behavioral contract for wind-farm reference zones (pure core).

Offshore wind farms are the atlas's first reference zones: places where
bottom trawling is excluded by law in some countries and merely discouraged
in others. The pure layer turns EMODnet's published polygons into zones the
store can hold (status, country, commissioning year — which may honestly be
unknown) and turns measured hours and areas into an inside-versus-surroundings
contrast, with the caveats that must travel with it.

Written test-first per TDD_CONTRACT.md.
"""

import json
import math
from pathlib import Path

import pytest

from carbon_atlas.effort.grid import BoundingBox
from carbon_atlas.zones import (
    EMODNET_WINDFARMS_SOURCE,
    ZONE_CAVEATS,
    WindFarmZone,
    ZoneContrast,
    parse_emodnet_windfarms,
    zone_contrast,
)

_REAL = Path(__file__).parent.parent / "fixtures" / "real" / "emodnet"
_NORTH_SEA = BoundingBox(lat_min=49.3, lat_max=62.4, lon_min=-10.4, lon_max=13.6)


def _feature(name, status, year, coords, country="Germany", extra=None):
    props = {
        "name": name,
        "country": country,
        "status": status,
        "year": year,
        "power_mw": 100.0,
        "n_turbines": 10,
        "area_sqkm": 5.0,
    }
    props.update(extra or {})
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [coords]},
        "properties": props,
    }


_SQUARE = [[7.0, 54.0], [7.1, 54.0], [7.1, 54.1], [7.0, 54.1], [7.0, 54.0]]


def test_producing_and_under_construction_farms_become_zones_with_their_facts():
    collection = {
        "type": "FeatureCollection",
        "features": [
            _feature("A", "Production", 2017, _SQUARE),
            _feature("B", "Construction", None, _SQUARE, country="Netherlands"),
        ],
    }

    zones = parse_emodnet_windfarms(collection, region=_NORTH_SEA)

    assert [z.name for z in zones] == ["A", "B"]
    a, b = zones
    assert a == WindFarmZone(
        name="A",
        country="Germany",
        status="Production",
        commissioned_year=2017,
        power_mw=100.0,
        turbines=10,
        area_km2=5.0,
        geometry={"type": "Polygon", "coordinates": [_SQUARE]},
    )
    assert b.status == "Construction"
    assert b.commissioned_year is None  # honestly unknown, never guessed


def test_planned_approved_dismantled_and_test_sites_are_not_reference_zones():
    """A farm that does not exist (yet, or any more) excludes nothing."""
    collection = {
        "type": "FeatureCollection",
        "features": [
            _feature(status, "x", 2020, _SQUARE)
            for status in ("Planned", "Approved", "Dismantled", "Test site")
        ]
        + [_feature("keep", "Production", 2020, _SQUARE)],
    }

    zones = parse_emodnet_windfarms(collection, region=_NORTH_SEA)

    assert [z.name for z in zones] == ["keep"]


def test_farms_outside_the_region_are_dropped_and_touching_ones_kept():
    baltic = [[20.0, 60.0], [20.1, 60.0], [20.1, 60.1], [20.0, 60.1], [20.0, 60.0]]
    edge = [[13.5, 55.0], [13.7, 55.0], [13.7, 55.1], [13.5, 55.1], [13.5, 55.0]]  # straddles
    collection = {
        "type": "FeatureCollection",
        "features": [
            _feature("baltic", "Production", 2015, baltic, country="Finland"),
            _feature("edge", "Production", 2015, edge, country="Sweden"),
        ],
    }

    zones = parse_emodnet_windfarms(collection, region=_NORTH_SEA)

    assert [z.name for z in zones] == ["edge"]


def test_a_feature_without_geometry_or_status_is_refused_loudly():
    no_geom = _feature("ghost", "Production", 2015, _SQUARE)
    no_geom["geometry"] = None
    with pytest.raises(ValueError, match="ghost"):
        parse_emodnet_windfarms({"features": [no_geom]}, region=_NORTH_SEA)

    no_status = _feature("blank", None, 2015, _SQUARE)
    with pytest.raises(ValueError, match="blank"):
        parse_emodnet_windfarms({"features": [no_status]}, region=_NORTH_SEA)


def test_missing_optional_facts_stay_none_and_an_unnamed_farm_is_named_so():
    feature = _feature(None, "Production", None, _SQUARE)
    feature["properties"].update({"power_mw": None, "n_turbines": None, "area_sqkm": None})

    (zone,) = parse_emodnet_windfarms({"features": [feature]}, region=_NORTH_SEA)

    assert zone.name == "(unnamed)"
    assert zone.power_mw is None and zone.turbines is None and zone.area_km2 is None


def test_the_source_names_emodnet_the_layer_and_the_license():
    assert "EMODnet" in EMODNET_WINDFARMS_SOURCE
    assert "windfarmspoly" in EMODNET_WINDFARMS_SOURCE
    assert "CC-BY 4.0" in EMODNET_WINDFARMS_SOURCE


@pytest.mark.integration
def test_the_real_german_bight_sample_parses_to_the_published_facts():
    """Verbatim EMODnet features (fixtures/real/emodnet/README.md): four
    producing German farms, two with an honestly missing commissioning year,
    and one Planned site that must not become a zone."""
    collection = json.loads(
        (_REAL / "windfarms_polygons.german-bight.geojson").read_text(encoding="utf-8")
    )

    zones = parse_emodnet_windfarms(collection, region=_NORTH_SEA)

    by_name = {z.name: z for z in zones}
    assert set(by_name) == {"Gode Wind 3", "Nordergründe", "Gode Wind 01", "Gode Wind 02"}
    assert by_name["Nordergründe"].commissioned_year == 2017
    assert by_name["Gode Wind 3"].commissioned_year == 2024
    assert by_name["Gode Wind 01"].commissioned_year is None
    assert all(z.country == "Germany" and z.status == "Production" for z in zones)
    assert by_name["Gode Wind 01"].geometry["type"] in {"Polygon", "MultiPolygon"}
    assert math.isclose(by_name["Nordergründe"].area_km2, 3.42193592317)


# ---------------------------------------------------------------------------
# The inside-versus-surroundings contrast
# ---------------------------------------------------------------------------


def test_the_contrast_is_two_densities_and_their_ratio():
    contrast = zone_contrast(farm_km2=100.0, inside_hours=50.0, ring_km2=400.0, ring_hours=600.0)

    assert contrast == ZoneContrast(
        farm_km2=100.0,
        inside_hours=50.0,
        ring_km2=400.0,
        ring_hours=600.0,
        inside_density=0.5,
        ring_density=1.5,
        ratio=1.0 / 3.0,
    )


def test_a_quiet_ring_gives_no_ratio_rather_than_infinity():
    contrast = zone_contrast(farm_km2=10.0, inside_hours=1.0, ring_km2=40.0, ring_hours=0.0)

    assert contrast.inside_density == 0.1
    assert contrast.ring_density == 0.0
    assert contrast.ratio is None


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(farm_km2=0.0, inside_hours=0.0, ring_km2=1.0, ring_hours=0.0),
        dict(farm_km2=1.0, inside_hours=-1.0, ring_km2=1.0, ring_hours=0.0),
        dict(farm_km2=1.0, inside_hours=0.0, ring_km2=float("nan"), ring_hours=0.0),
    ],
)
def test_meaningless_areas_or_hours_are_refused(kwargs):
    with pytest.raises(ValueError):
        zone_contrast(**kwargs)


def test_the_caveats_say_what_the_contrast_is_not():
    text = " ".join(ZONE_CAVEATS).lower()
    assert "matched" in text  # the ring is a comparison, not a matched control
    assert "united kingdom" in text or "uk" in text  # fishing is often permitted there
    assert "unknown" in text  # farms without a commissioning year are excluded
    assert "midwater" in text
    assert "coverage" in text


def test_a_point_or_line_geometry_is_refused_naming_its_type():
    """A wind farm is an area; EMODnet's point layer (windfarms) must not be
    mistaken for the polygon layer and drawn as if it had an extent."""
    point = _feature("dot", "Production", 2015, _SQUARE)
    point["geometry"] = {"type": "Point", "coordinates": [7.0, 54.0]}
    with pytest.raises(ValueError, match="Point"):
        parse_emodnet_windfarms({"features": [point]}, region=_NORTH_SEA)
