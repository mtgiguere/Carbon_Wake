"""HTTP contract for the cumulative-footprint endpoint (ADR-0017).

The one headline that needs no preset is still never a bare number: the
payload carries the bracket (floor, Poisson union, ceiling) as areas AND as
fractions of a stated denominator, the years and runs it was built from, the
method's citation with the published comparator, and the caveats naming both
directions of bias. No computed summary -> 404 with a message, never a zero.

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.db.store import store_footprint_summary, store_overlap
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.footprint import CumulativeFootprint, FootprintBracket
from carbon_atlas.overlap import OverlapResult, TrawledCell

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

_RESULT = OverlapResult(
    trawled=(
        TrawledCell(
            cell=GridCell(lat_index=5390, lon_index=764),
            fishing_hours_by_gear={"trawlers": 15.0},
            carbon=CarbonDensity(mean=1.5652642, uncertainty=2.4579988),
        ),
    ),
    unmapped_effort={},
)
_SUMMARY = CumulativeFootprint(
    years=(2012, 2024),
    cells=1,
    mapped=FootprintBracket(lower_m2=1.0e10, poisson_m2=1.5e10, upper_m2=2.0e10),
    all_effort=FootprintBracket(lower_m2=1.2e10, poisson_m2=1.8e10, upper_m2=2.4e10),
    per_year_mapped_m2={2012: 1.0e10, 2024: 8.0e9},
)


@pytest.fixture
def seeded(raw_conn):
    a = store_overlap(raw_conn, _RESULT, effort_source="e", carbon_source="c", effort_year=2012)
    b = store_overlap(raw_conn, _RESULT, effort_source="e", carbon_source="c", effort_year=2024)
    return store_footprint_summary(
        raw_conn, _SUMMARY, run_ids=[a, b], mapped_seabed_area_m2=5.0e10
    ), (a, b)


def test_the_footprint_is_served_as_a_bracket_with_fractions_and_provenance(client, seeded):
    summary_id, run_ids = seeded

    response = client.get("/api/footprint/")

    assert response.status_code == 200
    body = response.json()
    assert body["summary_id"] == summary_id
    assert body["years"] == [2012, 2024]
    assert body["run_ids"] == list(run_ids)
    assert body["cells"] == 1
    assert body["mapped_seabed_area_m2"] == 5.0e10

    mapped = body["mapped_seabed"]
    assert mapped["lower_m2"] == 1.0e10
    assert mapped["poisson_m2"] == 1.5e10
    assert mapped["upper_m2"] == 2.0e10
    assert math.isclose(mapped["fraction"]["lower"], 0.2)
    assert math.isclose(mapped["fraction"]["poisson"], 0.3)
    assert math.isclose(mapped["fraction"]["upper"], 0.4)

    assert body["all_effort"] == {"lower_m2": 1.2e10, "poisson_m2": 1.8e10, "upper_m2": 2.4e10}
    assert body["per_year_mapped_m2"] == {"2012": 1.0e10, "2024": 8.0e9}
    assert math.isclose(body["per_year_mapped_fraction"]["2012"], 0.2)
    assert math.isclose(body["per_year_mapped_fraction"]["2024"], 0.16)
    assert "computed_at" in body


def test_the_method_is_cited_and_the_caveats_name_both_biases(client, seeded):
    body = client.get("/api/footprint/").json()

    method = body["method"]
    assert method["headline"] == "poisson_union"
    assert "Amoroso" in method["citation"]
    assert "10.1073/pnas.1802379115" in method["citation"]
    # The published comparator for the same region travels with the number:
    # Amoroso 2018 Table 1, North Sea, random-placement footprint 42.2 %/yr.
    assert "42.2" in method["published_comparator"]
    assert "North Sea" in method["published_comparator"]

    caveats = " ".join(body["caveats"]).lower()
    assert "aggregat" in caveats
    assert "coverage" in caveats
    assert "midwater" in caveats
    assert "mapped" in caveats


def test_no_summary_is_a_404_with_a_message_not_a_zero(client, db):
    response = client.get("/api/footprint/")

    assert response.status_code == 404
    assert "footprint" in response.json()["detail"].lower()
