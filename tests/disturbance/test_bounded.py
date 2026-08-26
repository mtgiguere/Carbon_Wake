"""Behavioral contract for the BOUNDED disturbed-carbon model (ADR-0014).

The v1 linear model counted the same sediment repeatedly in heavily trawled
cells (the 2026-08-24 retrospective's headline flaw). The bounded form uses
the trawling-footprint literature's Poisson estimator (Amoroso et al. 2018:
passes over any point are randomly distributed within a cell), whose closed
form for the fraction of the cell swept at least once is 1 - exp(-SAR).
Disturbed volume = cell_area x (1 - exp(-SAR)) x penetration_depth — capped
by physics, equal to the linear model in the low-effort limit, and always
between zero and the cell's penetrated volume.

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.disturbance import (
    GearProfile,
    bounded_disturbed_carbon_kg,
    disturbed_carbon_kg,
    swept_area_m2,
)
from carbon_atlas.effort.grid import GridCell

_PROFILE = GearProfile(
    key="fixture",
    gear_width_m=77.28,
    towing_speed_knots=3.0,
    penetration_depth_m=0.0244,
    provenance="test fixture — not a real published parameter set",
)
_DENSITY = CarbonDensity(mean=2.0, uncertainty=0.5)
_CELL_AREA = 1.0e6  # a round 1 km^2 cell keeps the arithmetic legible


def test_the_2012_hotspot_cell_saturates_at_its_penetrated_volume():
    """The retrospective's own example: 427.6 h in the real Dutch-delta cell
    (SAR ~= 250) must disturb essentially the cell's WHOLE penetrated volume
    once — not ~250 times it. The bounded mass equals area x depth x density
    to within float precision, and sits ~250x below the linear model."""
    cell_area = GridCell(lat_index=5390, lon_index=764).area_m2

    bounded = bounded_disturbed_carbon_kg(
        fishing_hours=427.6, profile=_PROFILE, density=_DENSITY, cell_area_m2=cell_area
    )

    ceiling = cell_area * _PROFILE.penetration_depth_m * _DENSITY.mean
    linear = disturbed_carbon_kg(427.6, _PROFILE, _DENSITY)
    assert math.isclose(bounded.mean_kg, ceiling, rel_tol=1e-9)
    assert linear.mean_kg / bounded.mean_kg > 200.0


def test_at_sar_one_the_footprint_is_one_minus_e_to_the_minus_one():
    """The pinned midpoint: hours chosen so swept area equals cell area
    (SAR = 1) disturb exactly (1 - 1/e) of the penetrated volume."""
    hours_for_sar_one = _CELL_AREA / swept_area_m2(1.0, _PROFILE)

    bounded = bounded_disturbed_carbon_kg(
        fishing_hours=hours_for_sar_one,
        profile=_PROFILE,
        density=_DENSITY,
        cell_area_m2=_CELL_AREA,
    )

    expected = (1.0 - math.exp(-1.0)) * _CELL_AREA * _PROFILE.penetration_depth_m * _DENSITY.mean
    assert math.isclose(bounded.mean_kg, expected, rel_tol=1e-12)


def test_light_trawling_matches_the_linear_model():
    """The low-effort limit: at SAR ~ 0.001 the bound changes nothing —
    within 0.1% of the linear model, so lightly trawled cells (most of the
    North Sea) keep their previous, already-defensible values."""
    hours = 0.001 * _CELL_AREA / swept_area_m2(1.0, _PROFILE)

    bounded = bounded_disturbed_carbon_kg(
        fishing_hours=hours, profile=_PROFILE, density=_DENSITY, cell_area_m2=_CELL_AREA
    )
    linear = disturbed_carbon_kg(hours, _PROFILE, _DENSITY)

    assert math.isclose(bounded.mean_kg, linear.mean_kg, rel_tol=1e-3)


def test_zero_hours_disturb_exactly_nothing():
    bounded = bounded_disturbed_carbon_kg(
        fishing_hours=0.0, profile=_PROFILE, density=_DENSITY, cell_area_m2=_CELL_AREA
    )

    assert bounded.mean_kg == 0.0
    assert bounded.uncertainty_kg == 0.0


@pytest.mark.parametrize("cell_area_m2", [0.0, -1.0, float("nan"), float("inf")])
def test_a_corrupt_cell_area_is_rejected(cell_area_m2):
    """A non-positive or non-finite cell area is corrupt input, not a cell."""
    with pytest.raises(ValueError):
        bounded_disturbed_carbon_kg(
            fishing_hours=1.0, profile=_PROFILE, density=_DENSITY, cell_area_m2=cell_area_m2
        )


_hours = st.floats(min_value=0.0, max_value=1e5, allow_nan=False, allow_infinity=False)
_areas = st.floats(min_value=1e4, max_value=2e6, allow_nan=False, allow_infinity=False)


@given(hours=_hours, cell_area_m2=_areas)
def test_bounded_never_exceeds_linear_or_the_physical_ceiling(hours, cell_area_m2):
    """Property: for every effort level and cell size, the bounded mass is
    (a) never above the linear model and (b) never above the cell's
    penetrated volume times density — the two envelopes that define it."""
    bounded = bounded_disturbed_carbon_kg(
        fishing_hours=hours, profile=_PROFILE, density=_DENSITY, cell_area_m2=cell_area_m2
    )

    linear = disturbed_carbon_kg(hours, _PROFILE, _DENSITY)
    ceiling = cell_area_m2 * _PROFILE.penetration_depth_m * _DENSITY.mean
    # The 1e-290 kg absolute slack exists ONLY for subnormal-float inputs
    # (Hypothesis found hours=5e-324, where denormal rounding makes the two
    # code paths differ at magnitudes of 1e-319 kg). Any real violation of
    # the envelopes would exceed it by hundreds of orders of magnitude.
    assert bounded.mean_kg <= linear.mean_kg * (1 + 1e-12) + 1e-290
    assert bounded.mean_kg <= ceiling * (1 + 1e-12) + 1e-290


@given(hours_a=_hours, hours_b=_hours)
def test_more_effort_never_disturbs_less(hours_a, hours_b):
    """Property: the bound is monotone — extra hours can only disturb more
    (or equally), never less."""
    lo, hi = sorted((hours_a, hours_b))

    mass_lo = bounded_disturbed_carbon_kg(
        fishing_hours=lo, profile=_PROFILE, density=_DENSITY, cell_area_m2=_CELL_AREA
    )
    mass_hi = bounded_disturbed_carbon_kg(
        fishing_hours=hi, profile=_PROFILE, density=_DENSITY, cell_area_m2=_CELL_AREA
    )

    assert mass_lo.mean_kg <= mass_hi.mean_kg


@given(hours=_hours)
def test_uncertainty_scales_by_the_same_footprint_as_the_mean(hours):
    """Property: the uncertainty is the density uncertainty times exactly the
    same disturbed volume as the mean — the pair can never drift apart."""
    bounded = bounded_disturbed_carbon_kg(
        fishing_hours=hours, profile=_PROFILE, density=_DENSITY, cell_area_m2=_CELL_AREA
    )

    assert math.isclose(
        bounded.uncertainty_kg * _DENSITY.mean,
        bounded.mean_kg * _DENSITY.uncertainty,
        rel_tol=1e-12,
        abs_tol=1e-300,
    )
