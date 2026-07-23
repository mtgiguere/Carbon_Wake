"""Behavioral contract for the reactivity science core.

Every test here is written *before* the implementation it exercises and specifies
a behavior the code MUST have — never merely the shape of code already written.
See TDD_CONTRACT.md. No conditional guards, no `is True/False` on numeric values,
no seed-specific assertions.
"""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from carbon_atlas.reactivity.presets import (
    ReactivityPreset,
    co2_from_disturbed_carbon,
    estimate_range,
)


def _named(key: str, fraction: float) -> ReactivityPreset:
    """A valid preset with a caller-chosen key and remineralization fraction."""
    return ReactivityPreset(
        key=key,
        label=key,
        remineralization_fraction=fraction,
        citation="test fixture — not a real published estimate",
    )


def _preset(fraction: float) -> ReactivityPreset:
    """A valid preset with a caller-chosen remineralization fraction.

    Kept as a helper so a test about *one* thing (e.g. a mass boundary) does not
    restate the whole preset and accidentally couple to unrelated fields.
    """
    return _named("fixture", fraction)


# Hypothesis strategies for the physically valid input domain. Bounded mass keeps
# the arithmetic away from float-overflow territory while still spanning many
# orders of magnitude (grams to petagrams).
_fractions = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_masses = st.floats(min_value=0.0, max_value=1e15, allow_nan=False, allow_infinity=False)


def test_full_remineralization_obeys_carbon_to_co2_mass_ratio():
    """The load-bearing chemistry.

    When a mass of seafloor organic carbon is *fully* remineralized, the CO2
    produced equals that mass times the carbon→CO2 molar-mass ratio (44.0 / 12.0).
    So 12 mass-units of organic carbon yield exactly 44 mass-units of CO2.

    This is a fact about the world, not about our code. If the implementation
    disagrees with it, the implementation is wrong.
    """
    preset = ReactivityPreset(
        key="full",
        label="Full remineralization (test fixture)",
        remineralization_fraction=1.0,
        citation="test fixture — not a real published estimate",
    )

    co2 = co2_from_disturbed_carbon(disturbed_carbon_mass=12.0, preset=preset)

    assert math.isclose(co2, 44.0, rel_tol=1e-9)


# --- Boundary validation ----------------------------------------------------
# A remineralization fraction is a proportion: it is meaningful in [0, 1] and
# nonsense outside it. We pin BOTH the accepted boundary values AND the rejected
# just-outside values, in both directions — that is the exact discipline the
# mutation-testing addendum in TDD_CONTRACT.md was written to enforce.


@pytest.mark.parametrize("fraction", [0.0, 0.5, 1.0])
def test_fraction_at_or_within_bounds_is_accepted(fraction):
    """0.0 and 1.0 are valid — a preset may assume nothing outgasses, or all of
    it does. The boundaries are inclusive."""
    assert _preset(fraction).remineralization_fraction == fraction


@pytest.mark.parametrize("fraction", [-0.0001, -1.0, 1.0001, 2.0])
def test_fraction_outside_bounds_is_rejected(fraction):
    """Just past either boundary must raise — not clip, not silently accept.
    Silent clipping is how a false number reaches the map."""
    with pytest.raises(ValueError):
        _preset(fraction)


def test_zero_disturbed_carbon_produces_zero_co2():
    """The lower boundary of mass is valid and meaningful: disturbing nothing
    releases nothing. This must NOT raise."""
    assert co2_from_disturbed_carbon(disturbed_carbon_mass=0.0, preset=_preset(0.5)) == 0.0


def test_negative_disturbed_carbon_is_rejected():
    """Negative disturbed mass is physically meaningless and must raise rather
    than produce a negative 'CO2' figure."""
    with pytest.raises(ValueError):
        co2_from_disturbed_carbon(disturbed_carbon_mass=-1.0, preset=_preset(0.5))


# --- The uncertainty range --------------------------------------------------
# The project's central promise: never show a single figure for a disputed
# quantity. `estimate_range` returns the span across competing presets, and
# carries WHICH preset produced each end so the UI can cite it (Sala high vs. a
# conservative recalculation). These tests pin that promise structurally.


def test_estimate_range_spans_lowest_and_highest_preset():
    """Given several competing presets, the range's low end is the lowest preset's
    estimate and the high end is the highest preset's — and each end names the
    preset that produced it, so the estimate can be cited, not laundered."""
    presets = [_named("high", 0.5), _named("low", 0.01), _named("mid", 0.1)]

    r = estimate_range(disturbed_carbon_mass=1000.0, presets=presets)

    assert r.low == co2_from_disturbed_carbon(1000.0, presets[1])  # the 0.01 preset
    assert r.high == co2_from_disturbed_carbon(1000.0, presets[0])  # the 0.50 preset
    assert r.low_preset.key == "low"
    assert r.high_preset.key == "high"


def test_estimate_range_rejects_empty_presets():
    """A range over zero presets has no meaning. Raise — do not return a degenerate
    (0, 0) that a caller could mistake for a real, confident zero. This is the
    empty-collection edge that TDD_CONTRACT.md Bug #2 was about."""
    with pytest.raises(ValueError):
        estimate_range(disturbed_carbon_mass=1000.0, presets=[])


@given(mass=_masses, fraction=_fractions)
def test_co2_is_never_negative(mass, fraction):
    """Property: for any physically valid input, the CO2 estimate is non-negative."""
    assert co2_from_disturbed_carbon(mass, _preset(fraction)) >= 0.0


@given(mass=_masses, f_a=_fractions, f_b=_fractions)
def test_co2_is_monotonic_in_remineralization_fraction(mass, f_a, f_b):
    """Property: a higher remineralization fraction can only produce more CO2 (or
    equal), never less, for the same disturbed mass. This is exactly what makes a
    'conservative' preset a genuine lower bound rather than just a different number."""
    lo, hi = sorted((f_a, f_b))
    co2_lo = co2_from_disturbed_carbon(mass, _preset(lo))
    co2_hi = co2_from_disturbed_carbon(mass, _preset(hi))
    assert co2_lo <= co2_hi


@given(mass=_masses, fractions=st.lists(_fractions, min_size=1, max_size=6))
def test_every_preset_estimate_lies_within_the_range(mass, fractions):
    """Property: no competing estimate ever falls outside the displayed range.
    If this can be violated, the UI could show a preset value the range excludes —
    the exact false-precision failure the project exists to avoid."""
    presets = [_named(f"p{i}", f) for i, f in enumerate(fractions)]

    r = estimate_range(mass, presets)

    for p in presets:
        est = co2_from_disturbed_carbon(mass, p)
        assert r.low <= est <= r.high
