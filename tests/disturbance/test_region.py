"""Behavioral contract for region-scale disturbed carbon.

A region's disturbed mass is a sum over cells, but the per-cell factors
(speed x width x penetration) are constant per gear — so the store can hand
back one per-gear moment, sum(hours x density), and the pure layer applies
the constants. The contract that keeps that shortcut honest: the moment path
must equal the per-cell path EXACTLY. Uncertainties combine LINEARLY — the
conservative choice, since Diesing's per-pixel total uncertainties include
systematic components we cannot assume independent (SCIENCE_BASIS.md).

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.disturbance import (
    DisturbedCarbon,
    GearProfile,
    combine_disturbed,
    disturbed_carbon_from_effort_density_sum,
    disturbed_carbon_kg,
)

_PROFILE = GearProfile(
    key="fixture",
    gear_width_m=63.0,
    towing_speed_knots=3.0,
    penetration_depth_m=0.0244,
    provenance="test fixture — not a real published parameter set",
)


@given(
    hours=st.floats(min_value=0.0, max_value=1e5, allow_nan=False, allow_infinity=False),
    mean=st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    unc=st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_the_moment_path_equals_the_per_cell_path_exactly(hours, mean, unc):
    """Property: for one cell, feeding sum(h x density) through the moment
    shortcut gives the SAME DisturbedCarbon as the per-cell computation —
    the SQL-summable fast path can never drift from the tested model."""
    per_cell = disturbed_carbon_kg(
        fishing_hours=hours, profile=_PROFILE, density=CarbonDensity(mean=mean, uncertainty=unc)
    )
    via_moment = disturbed_carbon_from_effort_density_sum(
        hours_density_mean_sum=hours * mean,
        hours_density_uncertainty_sum=hours * unc,
        profile=_PROFILE,
    )

    assert math.isclose(via_moment.mean_kg, per_cell.mean_kg, rel_tol=1e-12, abs_tol=1e-300)
    assert math.isclose(
        via_moment.uncertainty_kg, per_cell.uncertainty_kg, rel_tol=1e-12, abs_tol=1e-300
    )


def test_moments_of_many_cells_sum_before_the_constant_factors():
    """Two cells' worth of hours-times-density arrives as ONE moment; the
    result equals the sum of the two per-cell computations."""
    a = disturbed_carbon_kg(2.0, _PROFILE, CarbonDensity(mean=3.0, uncertainty=1.0))
    b = disturbed_carbon_kg(5.0, _PROFILE, CarbonDensity(mean=1.5, uncertainty=0.25))

    combined = disturbed_carbon_from_effort_density_sum(
        hours_density_mean_sum=2.0 * 3.0 + 5.0 * 1.5,
        hours_density_uncertainty_sum=2.0 * 1.0 + 5.0 * 0.25,
        profile=_PROFILE,
    )

    assert math.isclose(combined.mean_kg, a.mean_kg + b.mean_kg, rel_tol=1e-12)
    assert math.isclose(combined.uncertainty_kg, a.uncertainty_kg + b.uncertainty_kg, rel_tol=1e-12)


@pytest.mark.parametrize(("mean_sum", "unc_sum"), [(-0.1, 1.0), (1.0, -0.1), (float("nan"), 1.0)])
def test_corrupt_moments_are_rejected(mean_sum, unc_sum):
    """A negative or NaN moment is corrupt input, not a region."""
    with pytest.raises(ValueError):
        disturbed_carbon_from_effort_density_sum(
            hours_density_mean_sum=mean_sum,
            hours_density_uncertainty_sum=unc_sum,
            profile=_PROFILE,
        )


def test_gears_combine_by_linear_addition_of_both_components():
    """Across gear classes the masses AND the uncertainties add linearly —
    the conservative (fully correlated) treatment, chosen because Diesing's
    total uncertainties include systematic components we cannot assume
    independent. Quadrature would claim knowledge we do not have."""
    trawl = DisturbedCarbon(mean_kg=100.0, uncertainty_kg=30.0)
    dredge = DisturbedCarbon(mean_kg=20.0, uncertainty_kg=8.0)

    combined = combine_disturbed([trawl, dredge])

    assert combined == DisturbedCarbon(mean_kg=120.0, uncertainty_kg=38.0)


def test_combining_nothing_is_the_honest_zero():
    """No parts means nothing disturbed: 0 ± 0, not an error — a region with
    no included effort is a valid (and reportable) answer."""
    assert combine_disturbed([]) == DisturbedCarbon(mean_kg=0.0, uncertainty_kg=0.0)
