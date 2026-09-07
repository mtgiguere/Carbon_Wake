"""Behavioral contract for everyday-unit anchors (pure core).

An anchor turns a CO2 mass into a count of something a reader already has a
feel for ("typical passenger cars driven for a year"). The honesty rules
(docs/IDEAS.md #6, SCIENCE_BASIS.md "Everyday anchors"): the conversion
factor is cited to a primary source; the anchor states its own comparability
limit (tailpipe emissions are atmospheric, our headline is aqueous first-year
CO2); and the mean and the uncertainty take the same path, so an anchored
count is a quantity with its uncertainty attached, never a bare number.

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from carbon_atlas.anchors import (
    EVERYDAY_ANCHORS,
    PASSENGER_CAR_YEAR,
    EverydayAnchor,
    anchor_count,
    anchor_counts,
)
from carbon_atlas.estimates import CO2Quantity


def test_the_passenger_car_anchor_is_the_epa_figure_with_its_citation_and_basis():
    """4.6 metric tons CO2 per typical passenger vehicle per year (US EPA,
    Green Vehicle Guide; verified against the primary page 2026-09-07). The
    factor ships with its source and with the assumptions it rests on, and
    the anchor names the comparability limit itself: a tailpipe emits to the
    ATMOSPHERE, while the atlas's headline is AQUEOUS first-year CO2."""
    assert PASSENGER_CAR_YEAR.key == "passenger_car_year"
    assert PASSENGER_CAR_YEAR.kg_co2_per_unit == 4600.0
    assert "epa.gov" in PASSENGER_CAR_YEAR.citation
    assert "22.2" in PASSENGER_CAR_YEAR.citation  # miles per gallon assumed
    assert "11,500" in PASSENGER_CAR_YEAR.citation  # miles per year assumed
    basis = PASSENGER_CAR_YEAR.basis.lower()
    assert "aqueous" in basis
    assert "atmospher" in basis
    assert "scale" in basis  # for scale only — never an equivalence claim


def test_the_catalog_holds_each_anchor_once():
    assert PASSENGER_CAR_YEAR in EVERYDAY_ANCHORS
    assert len({a.key for a in EVERYDAY_ANCHORS}) == len(EVERYDAY_ANCHORS)


def test_a_count_divides_the_mass_by_the_factor_and_keeps_the_anchor():
    """3.98 Mt of CO2 is about 865,000 car-years at 4.6 t each; the count
    carries the anchor that produced it (citation reachable from the number)."""
    counted = anchor_count(CO2Quantity(mean_kg=3.98e9, uncertainty_kg=2.2e9), PASSENGER_CAR_YEAR)

    assert counted.anchor is PASSENGER_CAR_YEAR
    assert math.isclose(counted.mean_units, 3.98e9 / 4600.0)
    assert math.isclose(counted.uncertainty_units, 2.2e9 / 4600.0)


@given(
    mean=st.floats(min_value=0.0, max_value=1e15, allow_nan=False, allow_infinity=False),
    unc=st.floats(min_value=0.0, max_value=1e15, allow_nan=False, allow_infinity=False),
)
def test_mean_and_uncertainty_take_the_same_path(mean, unc):
    """Property: both components are the SAME division — the relative
    uncertainty of the anchored count equals that of the CO2 mass, so the
    anchor can never tighten or loosen a band."""
    counted = anchor_count(CO2Quantity(mean_kg=mean, uncertainty_kg=unc), PASSENGER_CAR_YEAR)

    assert counted.mean_units == mean / PASSENGER_CAR_YEAR.kg_co2_per_unit
    assert counted.uncertainty_units == unc / PASSENGER_CAR_YEAR.kg_co2_per_unit


def test_a_thousandfold_dispute_stays_a_thousandfold_dispute():
    """Anchoring BOTH ends of the range is the point: the disagreement must
    survive the unit change exactly."""
    low = anchor_count(CO2Quantity(mean_kg=3.982e6, uncertainty_kg=0.0), PASSENGER_CAR_YEAR)
    high = anchor_count(CO2Quantity(mean_kg=3.982e9, uncertainty_kg=0.0), PASSENGER_CAR_YEAR)

    assert math.isclose(high.mean_units / low.mean_units, 1000.0, rel_tol=1e-9)


def test_zero_co2_is_zero_of_everything():
    counted = anchor_count(CO2Quantity(mean_kg=0.0, uncertainty_kg=0.0), PASSENGER_CAR_YEAR)
    assert counted.mean_units == 0.0
    assert counted.uncertainty_units == 0.0


def test_anchor_counts_covers_the_whole_catalog_in_order():
    counted = anchor_counts(CO2Quantity(mean_kg=4600.0, uncertainty_kg=0.0))

    assert tuple(c.anchor for c in counted) == EVERYDAY_ANCHORS
    assert counted[0].mean_units == 1.0


@pytest.mark.parametrize("factor", [0.0, -4600.0, float("nan"), float("inf")])
def test_an_anchor_with_a_meaningless_factor_cannot_exist(factor):
    """Dividing by zero, a negative mass, or a non-number is not a scale —
    refuse at construction, never produce an infinite or negative count."""
    with pytest.raises(ValueError):
        EverydayAnchor(
            key="broken",
            unit_label="broken things",
            kg_co2_per_unit=factor,
            citation="none",
            basis="none",
        )
