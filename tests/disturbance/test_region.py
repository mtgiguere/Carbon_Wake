"""Behavioral contract for combining disturbed-carbon parts.

Uncertainties combine LINEARLY — the conservative choice, since Diesing's
per-pixel total uncertainties include systematic components we cannot assume
independent (SCIENCE_BASIS.md). The former moment-path shortcut was removed
with ADR-0014: a nonlinear saturation bound cannot be expressed as a linear
moment, so regions are now summed per cell (see test_bounded.py and
tests/estimates).

Written test-first per TDD_CONTRACT.md.
"""

from carbon_atlas.disturbance import DisturbedCarbon, combine_disturbed


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
