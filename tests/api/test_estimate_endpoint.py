"""HTTP contract for the region CO2-estimate endpoint — the headline number,
served the only way this project allows: as a cited range with uncertainty.

The response must be self-describing: the disturbed-carbon pair it rests on,
one entry per published preset (citation, derivation flag, and CO2 with
uncertainty on both bases), the attributed range ends, the gear profiles with
their provenance, the effort-coverage disclosure (mapped vs unmapped hours),
and the model caveats. The arithmetic itself is pinned in the pure suites;
these tests pin the WIRING and the honesty of the payload.

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.db.store import store_overlap
from carbon_atlas.disturbance import (
    DEFAULT_GEAR_PROFILES,
    combine_disturbed,
    disturbed_carbon_from_effort_density_sum,
)
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.overlap import OverlapResult, TrawledCell

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

_DENSITY = CarbonDensity(mean=1.5652642, uncertainty=2.4579988)
_RESULT = OverlapResult(
    trawled=(
        TrawledCell(
            cell=GridCell(lat_index=5390, lon_index=764),
            fishing_hours_by_gear={"trawlers": 15.0057, "dredge_fishing": 0.5},
            carbon=_DENSITY,
        ),
    ),
    unmapped_effort={GridCell(lat_index=5366, lon_index=748): {"dredge_fishing": 7.25}},
)

# What the wired endpoint must reproduce, computed through the SAME pure
# functions the pure suites pin — these tests verify wiring, not arithmetic.
_EXPECTED_DISTURBED = combine_disturbed(
    [
        disturbed_carbon_from_effort_density_sum(
            hours_density_mean_sum=15.0057 * _DENSITY.mean,
            hours_density_uncertainty_sum=15.0057 * _DENSITY.uncertainty,
            profile=DEFAULT_GEAR_PROFILES["trawlers"],
        ),
        disturbed_carbon_from_effort_density_sum(
            hours_density_mean_sum=0.5 * _DENSITY.mean,
            hours_density_uncertainty_sum=0.5 * _DENSITY.uncertainty,
            profile=DEFAULT_GEAR_PROFILES["dredge_fishing"],
        ),
    ]
)


@pytest.fixture
def run_id(raw_conn):
    return store_overlap(raw_conn, _RESULT, effort_source="e", carbon_source="c")


@pytest.fixture
def payload(client, run_id):
    response = client.get(f"/api/runs/{run_id}/estimate/")
    assert response.status_code == 200
    return response.json()


def test_the_disturbed_carbon_matches_the_pure_chain(payload):
    """The endpoint's disturbed mass equals the pure moment-path computation
    over the seeded cells — per-gear profiles applied, linearly combined."""
    disturbed = payload["disturbed_carbon"]

    assert math.isclose(disturbed["mean_kg"], _EXPECTED_DISTURBED.mean_kg, rel_tol=1e-9)
    assert math.isclose(
        disturbed["uncertainty_kg"], _EXPECTED_DISTURBED.uncertainty_kg, rel_tol=1e-9
    )


def test_one_estimate_per_published_preset_each_cited(payload):
    """Every published preset appears with its citation, derivation flag, and
    CO2-with-uncertainty; Sala's unquantified atmospheric basis stays null."""
    by_key = {e["preset"]["key"]: e for e in payload["estimates"]}

    assert set(by_key) == {
        "sala_2021",
        "atwood_2024_low",
        "atwood_2024_high",
        "hiddink_2023_low",
        "hiddink_2023_high",
    }
    sala = by_key["sala_2021"]
    assert "10.1038/s41586-021-03371-z" in sala["preset"]["citation"]
    assert sala["atmospheric_co2"] is None
    expected_aqueous = _EXPECTED_DISTURBED.mean_kg * 0.297 * (44.0 / 12.0)
    assert math.isclose(sala["aqueous_co2"]["mean_kg"], expected_aqueous, rel_tol=1e-9)
    assert sala["aqueous_co2"]["uncertainty_kg"] > 0.0
    assert "inferred" in by_key["hiddink_2023_low"]["preset"]["derivation"].lower()
    atwood = by_key["atwood_2024_low"]
    assert math.isclose(
        atwood["atmospheric_co2"]["mean_kg"], atwood["aqueous_co2"]["mean_kg"] * 0.55, rel_tol=1e-9
    )


def test_the_range_is_attributed_and_spans_the_dispute(payload):
    """The span's ends name their presets; high/low ratio is the published
    1000x dispute."""
    assert payload["range"]["low"]["preset_key"] == "hiddink_2023_low"
    ratio = (
        payload["range"]["high"]["aqueous_co2"]["mean_kg"]
        / payload["range"]["low"]["aqueous_co2"]["mean_kg"]
    )
    assert math.isclose(ratio, 1000.0, rel_tol=1e-9)


def test_the_payload_discloses_coverage_profiles_and_caveats(payload):
    """The honesty layer travels with the number: the effort-layer label
    (midwater disclosure), mapped vs unmapped hours, each gear profile's
    provenance, and non-empty model caveats naming the mapped-only scope."""
    assert "midwater" in payload["effort_layer_label"].lower()
    coverage = payload["effort_coverage"]
    assert coverage["cells_mapped"] == 1
    assert coverage["cells_unmapped"] == 1
    assert math.isclose(coverage["fishing_hours_mapped"], 15.5057, rel_tol=1e-9)
    assert math.isclose(coverage["fishing_hours_unmapped"], 7.25, rel_tol=1e-9)

    profiles = {p["key"]: p for p in payload["gear_profiles"]}
    assert set(profiles) == {"trawlers", "dredge_fishing"}
    for profile in profiles.values():
        assert "Eigaard" in profile["provenance"]

    caveats = " ".join(payload["caveats"]).lower()
    assert "mapped" in caveats
    assert "aqueous" in caveats
    assert "uncertaint" in caveats


def test_a_run_with_no_mapped_effort_estimates_an_honest_zero(client, raw_conn):
    """All-unmapped effort: disturbed 0 ± 0 and zero CO2 under every preset —
    a valid, reportable answer whose coverage block shows WHY it is zero."""
    run_id = store_overlap(
        raw_conn,
        OverlapResult(
            trawled=(),
            unmapped_effort={GridCell(lat_index=100, lon_index=100): {"trawlers": 9.0}},
        ),
        effort_source="e",
        carbon_source="c",
    )

    response = client.get(f"/api/runs/{run_id}/estimate/")

    assert response.status_code == 200
    body = response.json()
    assert body["disturbed_carbon"] == {"mean_kg": 0.0, "uncertainty_kg": 0.0}
    assert all(e["aqueous_co2"]["mean_kg"] == 0.0 for e in body["estimates"])
    assert math.isclose(body["effort_coverage"]["fishing_hours_unmapped"], 9.0, rel_tol=1e-12)


def test_an_unknown_run_is_a_404_naming_the_id(client, db):
    response = client.get("/api/runs/31337/estimate/")

    assert response.status_code == 404
    assert "31337" in response.json()["detail"]
