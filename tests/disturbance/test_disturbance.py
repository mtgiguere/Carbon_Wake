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
    DEFAULT_GEAR_PROFILES,
    DisturbedCarbon,
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


@pytest.mark.parametrize(
    ("mean_kg", "uncertainty_kg"),
    [(-0.1, 1.0), (1.0, -0.1), (float("nan"), 1.0), (1.0, float("inf"))],
)
def test_a_corrupt_disturbed_mass_cannot_be_constructed(mean_kg, uncertainty_kg):
    """Same discipline as CarbonDensity, one derivation later: a negative or
    non-finite mass (or uncertainty) is impossible to build, so nothing
    downstream ever has to check."""
    with pytest.raises(ValueError):
        DisturbedCarbon(mean_kg=mean_kg, uncertainty_kg=uncertainty_kg)


# --- The default profiles (ADR-0012) ------------------------------------------
# One profile per included GFW gear class (the ADR-0009 seam), every number
# citable: penetration depths quoted from Hiddink 2017 via Sala/Atwood; widths
# computed with Sala's own Eigaard relationships, effort-weighted over GFW's
# 2012 vessel table; speeds the midpoints of Sala's per-gear plausibility
# filters. Exact figures and computation: ADR-0012 / SCIENCE_BASIS.md.


def test_there_is_a_default_profile_for_each_included_gear_class():
    """The profile keys are exactly the ADR-0009 inclusion set — a gear the
    effort layer includes but the model cannot price would be a silent hole."""
    assert set(DEFAULT_GEAR_PROFILES) == {"trawlers", "dredge_fishing"}


def test_the_trawlers_profile_pins_the_derived_parameters():
    """Otter-trawl treatment (Sala's own default for unclassified vessels):
    Hiddink's 2.44 cm penetration, 3.0 kn (midpoint of Sala's 2-4 kn otter
    filter), and the 77.28 m effort-weighted width computed from GFW's 2012
    vessel table with Sala's W = 10.6608 x KW^0.2921."""
    profile = DEFAULT_GEAR_PROFILES["trawlers"]

    assert profile.penetration_depth_m == 0.0244
    assert profile.towing_speed_knots == 3.0
    assert math.isclose(profile.gear_width_m, 77.28, rel_tol=1e-9)


def test_the_dredge_profile_pins_the_derived_parameters():
    """Towed-dredge treatment: Hiddink's 5.47 cm penetration, 2.25 kn
    (midpoint of Sala's 2-2.5 kn dredge filter), and the 26.02 m
    effort-weighted width from Sala's W = 0.3142 x LOA^1.2454."""
    profile = DEFAULT_GEAR_PROFILES["dredge_fishing"]

    assert profile.penetration_depth_m == 0.0547
    assert profile.towing_speed_knots == 2.25
    assert math.isclose(profile.gear_width_m, 26.02, rel_tol=1e-9)


def test_every_default_profile_carries_its_provenance():
    """A parameter without its source is not usable science: each profile
    names its sources, and the trawlers profile discloses the midwater
    caveat (ADR-0009) — the honest label follows the number everywhere."""
    for profile in DEFAULT_GEAR_PROFILES.values():
        provenance = profile.provenance.lower()
        assert "sala" in provenance
        assert "eigaard" in provenance
        assert "hiddink" in provenance
    assert "midwater" in DEFAULT_GEAR_PROFILES["trawlers"].provenance.lower()


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
def test_disturbed_mass_scales_the_uncertainty_by_exactly_the_disturbed_volume(hours, mean, unc):
    """Property: over the whole physical input domain the mass and its
    uncertainty are non-negative, and the uncertainty is EXACTLY the density
    uncertainty times the disturbed volume — the same factor as the mean, so
    the pair can never drift apart. (Hypothesis found that a naive 'nonzero
    in, nonzero out' claim is false in IEEE floats: ~5e-184 x ~5e-184
    underflows to 0.0 — so the pinned claim is the algebraic identity.)"""
    profile = _profile()
    mass = disturbed_carbon_kg(
        fishing_hours=hours,
        profile=profile,
        density=CarbonDensity(mean=mean, uncertainty=unc),
    )

    volume = swept_area_m2(hours, profile) * profile.penetration_depth_m
    assert mass.mean_kg >= 0.0
    assert mass.uncertainty_kg >= 0.0
    assert mass.mean_kg == volume * mean
    assert mass.uncertainty_kg == volume * unc
