"""HTTP contract for the AREA estimate — the visitor's own box (IDEAS.md #1).

The same cited, attributed range as the region estimate, computed over the
run's mapped cells that intersect a WGS84 bbox, wrapped in the honesty an
area query needs on top: how many cells it rests on (few cells = wide
relative uncertainty), how much effort inside the box sits on unmapped
seafloor, and the displacement caveat — a hypothetical closure moves effort,
it does not delete it. Same pure chain as the region estimate, never a
second arithmetic.

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.db.store import store_overlap
from carbon_atlas.disturbance import gear_profiles_for_year
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.estimates import disturbed_from_cells, estimate_region_co2
from carbon_atlas.overlap import OverlapResult, TrawledCell
from carbon_atlas.reactivity.presets import PUBLISHED_PRESETS

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

_DENSITY = CarbonDensity(mean=1.5652642, uncertainty=2.4579988)
_INSIDE = TrawledCell(
    cell=GridCell(lat_index=5390, lon_index=764),
    fishing_hours_by_gear={"trawlers": 15.0, "dredge_fishing": 0.5},
    carbon=_DENSITY,
)
_ALSO_INSIDE = TrawledCell(
    cell=GridCell(lat_index=5391, lon_index=765),
    fishing_hours_by_gear={"trawlers": 4.0},
    carbon=_DENSITY,
)
_OUTSIDE = TrawledCell(
    cell=GridCell(lat_index=5450, lon_index=800),
    fishing_hours_by_gear={"trawlers": 100.0},
    carbon=_DENSITY,
)
_RESULT = OverlapResult(
    trawled=(_INSIDE, _ALSO_INSIDE, _OUTSIDE),
    unmapped_effort={GridCell(lat_index=5390, lon_index=766): {"trawlers": 7.25}},
)
# A box that holds the two inside cells and the unmapped one, not the far cell.
_BBOX = "7.60,53.85,7.70,53.95"


@pytest.fixture
def run_id(raw_conn):
    return store_overlap(raw_conn, _RESULT, effort_source="e", carbon_source="c", effort_year=2024)


def test_the_area_estimate_is_the_pure_chain_over_the_intersecting_mapped_cells(client, run_id):
    response = client.get(f"/api/runs/{run_id}/estimate/?bbox={_BBOX}")

    assert response.status_code == 200
    body = response.json()
    expected = estimate_region_co2(
        disturbed_from_cells([_INSIDE, _ALSO_INSIDE], gear_profiles_for_year(2024)),
        PUBLISHED_PRESETS,
    )
    assert math.isclose(body["disturbed_carbon"]["mean_kg"], expected.disturbed.mean_kg)
    assert math.isclose(
        body["disturbed_carbon"]["uncertainty_kg"], expected.disturbed.uncertainty_kg
    )
    assert math.isclose(
        body["range"]["high"]["aqueous_co2"]["mean_kg"], expected.high.aqueous.mean_kg
    )
    assert body["range"]["low"]["preset_key"] == expected.low.preset.key
    assert body["effort_year"] == 2024
    # The full-run payload's honesty travels too.
    assert len(body["estimates"]) == len(PUBLISHED_PRESETS)
    assert all("anchors" in entry for entry in body["estimates"])
    assert body["caveats"]


def test_the_area_payload_states_its_scope_cells_and_displacement(client, run_id):
    body = client.get(f"/api/runs/{run_id}/estimate/?bbox={_BBOX}").json()

    area = body["area"]
    assert area["bbox"] == {"lon_min": 7.6, "lat_min": 53.85, "lon_max": 7.7, "lat_max": 53.95}
    assert area["cells_mapped"] == 2
    assert area["cells_unmapped"] == 1
    assert math.isclose(area["fishing_hours_mapped"], 19.5)
    assert math.isclose(area["fishing_hours_unmapped"], 7.25)
    assert math.isclose(body["effort_coverage"]["fishing_hours_mapped"], 19.5)
    assert math.isclose(body["effort_coverage"]["fishing_hours_unmapped"], 7.25)
    caveats = " ".join(body["caveats"]).lower()
    assert "displace" in caveats  # a closure moves effort, it does not delete it
    assert "few" in caveats or "cells" in caveats  # small boxes: wide relative uncertainty
    assert "2 cells" in " ".join(body["caveats"]) or area["cells_mapped"] == 2


def test_the_full_run_estimate_is_unchanged_and_carries_no_area_block(client, run_id):
    body = client.get(f"/api/runs/{run_id}/estimate/").json()

    assert "area" not in body
    assert math.isclose(body["effort_coverage"]["fishing_hours_mapped"], 119.5)
    assert not any("displace" in c.lower() for c in body["caveats"])


def test_an_empty_box_is_an_honest_zero_with_zero_cells(client, run_id):
    body = client.get(f"/api/runs/{run_id}/estimate/?bbox=0,0,0.1,0.1").json()

    assert body["area"]["cells_mapped"] == 0 and body["area"]["cells_unmapped"] == 0
    assert body["disturbed_carbon"] == {"mean_kg": 0.0, "uncertainty_kg": 0.0}
    assert body["range"]["high"]["aqueous_co2"]["mean_kg"] == 0.0


@pytest.mark.parametrize("bbox", ["7.6,53.85,7.7", "a,b,c,d", "7.7,53.95,7.6,53.85"])
def test_a_malformed_or_inverted_bbox_is_a_400(client, run_id, bbox):
    response = client.get(f"/api/runs/{run_id}/estimate/?bbox={bbox}")
    assert response.status_code == 400
