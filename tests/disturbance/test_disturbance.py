"""Behavioral contract for the disturbed-carbon model (pure core).

The model is Sala 2021's swept-volume chain instantiated per cell:
fishing hours x towing speed x gear width -> swept area; x penetration depth
-> disturbed volume; x OC density -> disturbed carbon mass. Every parameter
travels in a GearProfile that carries its provenance, and the mass inherits
the carbon density's uncertainty — never a bare number (see
docs/SCIENCE_BASIS.md "The disturbed-carbon model" and ADR-0012).

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.disturbance import (
    GearProfile,
    disturbed_carbon_kg,
    swept_area_m2,
)


def _profile(
    *, width_m: float = 63.0, speed_knots: float = 3.0, depth_m: float = 0.0244
) -> GearProfile:
    return GearProfile(
        key="fixture",
        gear_width_m=width_m,
        towing_speed_knots=speed_knots,
        penetration_depth_m=depth_m,
        provenance="test fixture — not a real published parameter set",
    )


def test_one_hour_at_one_knot_with_one_km_of_gear_sweeps_exactly_one_nautical_mile_strip():
    """The load-bearing unit conversion: a knot is exactly 1852 m/h by
    definition, so 1 h x 1 kn x 1000 m of gear = 1,852,000 m^2. A wrong
    knots-to-meters factor would silently scale every estimate on the map."""
    area = swept_area_m2(fishing_hours=1.0, profile=_profile(width_m=1000.0, speed_knots=1.0))

    assert math.isclose(area, 1_852_000.0, rel_tol=1e-12)


def test_swept_area_for_a_realistic_trawl_hour():
    """3.1 knots with a 63 m door spread for one hour: 3.1 x 1852 x 63 m^2 —
    the arithmetic pinned once with explicit numbers, not re-derived."""
    area = swept_area_m2(fishing_hours=1.0, profile=_profile(width_m=63.0, speed_knots=3.1))

    assert math.isclose(area, 3.1 * 1852.0 * 63.0, rel_tol=1e-12)


def test_disturbed_mass_is_volume_times_density_with_uncertainty_carried():
    """Swept area x penetration depth prices the disturbed volume at the
    cell's OC density — and the per-pixel uncertainty scales with it, exactly
    (scalar multiplication), never dropped."""
    profile = _profile(width_m=1000.0, speed_knots=1.0, depth_m=0.0244)
    density = CarbonDensity(mean=2.0, uncertainty=0.5)

    mass = disturbed_carbon_kg(fishing_hours=1.0, profile=profile, density=density)

    expected_volume = 1_852_000.0 * 0.0244
    assert math.isclose(mass.mean_kg, expected_volume * 2.0, rel_tol=1e-12)
    assert math.isclose(mass.uncertainty_kg, expected_volume * 0.5, rel_tol=1e-12)


def test_zero_fishing_hours_disturbs_exactly_nothing():
    """The lower boundary is valid and meaningful: no effort, no disturbance,
    and no uncertainty about it."""
    mass = disturbed_carbon_kg(
        fishing_hours=0.0, profile=_profile(), density=CarbonDensity(mean=5.0, uncertainty=1.0)
    )

    assert mass.mean_kg == 0.0
    assert mass.uncertainty_kg == 0.0


@pytest.mark.parametrize("hours", [-0.1, float("nan"), float("inf")])
def test_invalid_fishing_hours_are_rejected(hours):
    """Negative, NaN, or infinite hours are corrupt input — raise, never
    absorb into a mass that reaches a CO2 figure."""
    with pytest.raises(ValueError):
        swept_area_m2(fishing_hours=hours, profile=_profile())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"width_m": 0.0},
        {"width_m": -1.0},
        {"width_m": float("nan")},
        {"speed_knots": 0.0},
        {"speed_knots": -2.0},
        {"depth_m": 0.0},
        {"depth_m": 1.5},
        {"depth_m": float("inf")},
    ],
    ids=str,
)
def test_physically_impossible_gear_profiles_cannot_be_constructed(kwargs):
    """A gear that is 0 m wide, tows at 0 knots, doesn't touch the seabed, or
    penetrates deeper than a metre (an order of magnitude past hydraulic
    dredges) is a parameter error, not a gear. Reject at construction."""
    with pytest.raises(ValueError):
        _profile(**kwargs)


_hours = st.floats(min_value=0.0, max_value=1e5, allow_nan=False, allow_infinity=False)


@given(hours=_hours)
def test_disturbed_mass_is_linear_in_effort(hours):
    """Property: doubling the hours exactly doubles the disturbed mass and
    its uncertainty — the model has no hidden thresholds or saturation."""
    profile = _profile()
    density = CarbonDensity(mean=3.0, uncertainty=0.7)

    single = disturbed_carbon_kg(fishing_hours=hours, profile=profile, density=density)
    double = disturbed_carbon_kg(fishing_hours=2 * hours, profile=profile, density=density)

    assert math.isclose(double.mean_kg, 2 * single.mean_kg, rel_tol=1e-9, abs_tol=1e-12)
    assert math.isclose(
        double.uncertainty_kg, 2 * single.uncertainty_kg, rel_tol=1e-9, abs_tol=1e-12
    )


@given(
    hours=_hours,
    mean=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    unc=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_disturbed_mass_is_never_negative_and_never_loses_its_uncertainty(hours, mean, unc):
    """Property: over the whole physical input domain the mass and its
    uncertainty are non-negative, and a nonzero density uncertainty with
    nonzero effort yields a nonzero mass uncertainty — it cannot vanish."""
    mass = disturbed_carbon_kg(
        fishing_hours=hours,
        profile=_profile(),
        density=CarbonDensity(mean=mean, uncertainty=unc),
    )

    assert mass.mean_kg >= 0.0
    assert mass.uncertainty_kg >= 0.0
    if hours > 0.0 and unc > 0.0:
        assert mass.uncertainty_kg > 0.0
