"""HTTP contract for the run-provenance endpoint.

A run's provenance IS the honesty layer at the API: sources, the ADR-0009
effort-layer label verbatim, and BOTH sides' totals — the unmapped effort a
dishonest API would omit. Newest run first; an empty database is an empty
list, not an error.

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.db.store import store_overlap
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.overlap import OverlapResult, TrawledCell

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

_RESULT = OverlapResult(
    trawled=(
        TrawledCell(
            cell=GridCell(lat_index=5390, lon_index=764),
            fishing_hours=15.0057,
            carbon=CarbonDensity(mean=1.5652642, uncertainty=2.4579988),
        ),
    ),
    unmapped_effort={GridCell(lat_index=5366, lon_index=748): 7.25},
)


def test_runs_are_served_newest_first_with_full_provenance(client, raw_conn):
    """Both runs come through with sources, the honest label, and both sides'
    totals — newest first, ready for the map's default view."""
    first = store_overlap(raw_conn, _RESULT, effort_source="e1", carbon_source="c1")
    second = store_overlap(raw_conn, _RESULT, effort_source="e2", carbon_source="c2")

    response = client.get("/api/runs/")

    assert response.status_code == 200
    runs = response.json()["runs"]
    assert [r["id"] for r in runs] == [second, first]
    newest = runs[0]
    assert newest["effort_source"] == "e2"
    assert newest["carbon_source"] == "c2"
    assert "midwater" in newest["effort_layer_label"].lower()
    assert newest["cells_mapped"] == 1
    assert newest["cells_unmapped"] == 1
    assert math.isclose(newest["fishing_hours_mapped"], 15.0057, rel_tol=1e-12)
    assert math.isclose(newest["fishing_hours_unmapped"], 7.25, rel_tol=1e-12)
    assert newest["created_at"]  # present and non-empty (ISO timestamp)


def test_no_runs_is_an_empty_list_not_an_error(client, db):
    """An empty database answers honestly: an empty list, HTTP 200."""
    response = client.get("/api/runs/")

    assert response.status_code == 200
    assert response.json() == {"runs": []}
