"""Behavioral contract for the cumulative trawling footprint (pure core).

"What fraction of the seabed has been trawled at least once since 2012?" is a
COVERAGE claim — physics both camps of the CO2 dispute accept — so it needs
no preset. It reuses ADR-0014's Poisson footprint (1 - exp(-SAR)) and extends
it across years, but never as one number: per cell, the largest single-year
footprint is a FLOOR (that seabed was certainly swept), the sum of annual
footprints capped at the cell is a CEILING (years cannot overlap less than
not at all), and the Poisson union across years (independent random placement
year to year) sits between them. The three travel together.

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
    poisson_footprint_fraction,
    swept_area_ratio,
)
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.footprint import (
    FOOTPRINT_CAVEATS,
    CellEffortHistory,
    FootprintBracket,
    cumulative_footprint,
)

_PROFILE = GearProfile(
    key="trawlers",
    gear_width_m=64.0,
    towing_speed_knots=3.0,
    penetration_depth_m=0.0244,
    provenance="test fixture - not a real published parameter set",
)
_WIDER = GearProfile(
    key="trawlers",
    gear_width_m=128.0,  # a different year's fleet: twice the width
    towing_speed_knots=3.0,
    penetration_depth_m=0.0244,
    provenance="test fixture - not a real published parameter set",
)
_PROFILES = {2012: {"trawlers": _PROFILE}, 2013: {"trawlers": _WIDER}}
_CELL = GridCell(lat_index=5390, lon_index=764)  # the real Dutch-delta hotspot cell
_AREA = _CELL.area_m2


def _hours_for_sar(sar: float, profile: GearProfile, area_m2: float) -> float:
    """Hours that produce exactly ``sar`` under ``profile`` in ``area_m2``."""
    return sar * area_m2 / (profile.towing_speed_knots * 1852.0 * profile.gear_width_m)


# ---------------------------------------------------------------------------
# The two primitives live in ONE place (disturbance) and the bounded carbon
# model is built from them - no second copy of the footprint math.
# ---------------------------------------------------------------------------


def test_swept_area_ratio_is_swept_area_over_cell_area():
    hours = _hours_for_sar(2.5, _PROFILE, _AREA)
    assert math.isclose(swept_area_ratio(hours, _PROFILE, _AREA), 2.5, rel_tol=1e-12)


@pytest.mark.parametrize("bad_area", [0.0, -1.0, float("nan"), float("inf")])
def test_a_meaningless_cell_area_is_refused(bad_area):
    with pytest.raises(ValueError):
        swept_area_ratio(1.0, _PROFILE, bad_area)


def test_poisson_footprint_fraction_is_one_minus_exp_minus_sar():
    assert poisson_footprint_fraction(0.0) == 0.0
    assert math.isclose(poisson_footprint_fraction(1.0), 1.0 - math.exp(-1.0), rel_tol=1e-12)
    assert math.isclose(poisson_footprint_fraction(250.0), 1.0, rel_tol=1e-12)
    with pytest.raises(ValueError):
        poisson_footprint_fraction(-0.1)


def test_the_bounded_carbon_model_is_built_from_the_same_footprint():
    """ADR-0014's disturbed mass is footprint x depth x density - where the
    footprint is exactly these primitives, so a change to the footprint math
    can never leave the CO2 chain and the coverage headline disagreeing."""
    hours = _hours_for_sar(0.7, _PROFILE, _AREA)
    density = CarbonDensity(mean=2.0, uncertainty=0.5)

    bounded = bounded_disturbed_carbon_kg(
        fishing_hours=hours, profile=_PROFILE, density=density, cell_area_m2=_AREA
    )

    footprint_m2 = _AREA * poisson_footprint_fraction(swept_area_ratio(hours, _PROFILE, _AREA))
    assert math.isclose(bounded.mean_kg, footprint_m2 * 0.0244 * 2.0, rel_tol=1e-12)


# ---------------------------------------------------------------------------
# The cumulative footprint
# ---------------------------------------------------------------------------


def _history(hours_by_year: dict[int, float], mapped: bool = True) -> CellEffortHistory:
    return CellEffortHistory(
        cell=_CELL,
        mapped=mapped,
        hours_by_year={year: {"trawlers": hours} for year, hours in hours_by_year.items()},
    )


def test_a_single_year_collapses_the_bracket_onto_adr_0014s_footprint():
    """One year: floor, Poisson union, and ceiling are all the same number -
    the within-year bound the CO2 chain already uses."""
    hours = _hours_for_sar(1.0, _PROFILE, _AREA)

    result = cumulative_footprint([_history({2012: hours})], _PROFILES)

    expected = _AREA * (1.0 - math.exp(-1.0))
    assert result.years == (2012,)
    assert result.cells == 1
    for value in (result.mapped.lower_m2, result.mapped.poisson_m2, result.mapped.upper_m2):
        assert math.isclose(value, expected, rel_tol=1e-12)
    assert math.isclose(result.per_year_mapped_m2[2012], expected, rel_tol=1e-12)


def test_two_years_in_one_cell_give_floor_union_and_ceiling():
    """SAR 0.25 in 2012 and SAR 0.75 in 2013 (the 2013 fleet is priced with
    ITS width). Floor = the larger single-year footprint; Poisson union =
    1 - exp(-(0.25 + 0.75)); ceiling = the two footprints summed (0.22 + 0.53
    of the cell — below it, so uncapped)."""
    history = _history(
        {2012: _hours_for_sar(0.25, _PROFILE, _AREA), 2013: _hours_for_sar(0.75, _WIDER, _AREA)}
    )

    result = cumulative_footprint([history], _PROFILES)

    f_2012 = 1.0 - math.exp(-0.25)
    f_2013 = 1.0 - math.exp(-0.75)
    assert result.years == (2012, 2013)
    assert math.isclose(result.mapped.lower_m2, _AREA * f_2013, rel_tol=1e-12)
    assert math.isclose(result.mapped.poisson_m2, _AREA * (1.0 - math.exp(-1.0)), rel_tol=1e-12)
    assert math.isclose(result.mapped.upper_m2, _AREA * (f_2012 + f_2013), rel_tol=1e-12)
    assert math.isclose(result.per_year_mapped_m2[2012], _AREA * f_2012, rel_tol=1e-12)
    assert math.isclose(result.per_year_mapped_m2[2013], _AREA * f_2013, rel_tol=1e-12)


def test_the_ceiling_never_exceeds_the_cell():
    """Two heavy years: annual footprints sum past the cell; the ceiling is
    the cell itself, and the union stays at or below it."""
    history = _history(
        {2012: _hours_for_sar(3.0, _PROFILE, _AREA), 2013: _hours_for_sar(3.0, _WIDER, _AREA)}
    )

    result = cumulative_footprint([history], _PROFILES)

    assert math.isclose(result.mapped.upper_m2, _AREA, rel_tol=1e-12)
    assert result.mapped.poisson_m2 <= result.mapped.upper_m2


def test_unmapped_cells_count_toward_all_effort_but_not_toward_mapped_seabed():
    """The mapped-seabed bracket answers 'fraction of the carbon-mapped
    seabed'; the all-effort bracket is an AREA (no honest denominator exists
    for it). An unmapped cell is in the second, not the first."""
    hours = _hours_for_sar(1.0, _PROFILE, _AREA)
    mapped = _history({2012: hours}, mapped=True)
    unmapped = CellEffortHistory(
        cell=GridCell(lat_index=5366, lon_index=748),
        mapped=False,
        hours_by_year={2012: {"trawlers": hours}},
    )

    result = cumulative_footprint([mapped, unmapped], _PROFILES)

    assert result.cells == 2
    assert result.all_effort.poisson_m2 > result.mapped.poisson_m2
    assert math.isclose(result.mapped.poisson_m2, _AREA * (1.0 - math.exp(-1.0)), rel_tol=1e-12)


def test_no_cells_is_the_honest_zero():
    result = cumulative_footprint([], _PROFILES)
    assert result.cells == 0
    assert result.years == ()
    assert result.mapped == FootprintBracket(lower_m2=0.0, poisson_m2=0.0, upper_m2=0.0)
    assert result.all_effort == FootprintBracket(lower_m2=0.0, poisson_m2=0.0, upper_m2=0.0)


def test_a_year_without_profiles_fails_loudly_naming_it():
    with pytest.raises(KeyError, match="no gear profiles for year 2031"):
        cumulative_footprint([_history({2031: 1.0})], _PROFILES)


def test_a_gear_without_a_profile_fails_loudly_naming_it():
    history = CellEffortHistory(
        cell=_CELL, mapped=True, hours_by_year={2012: {"beam_trawl_from_the_future": 1.0}}
    )
    with pytest.raises(
        KeyError, match="no gear profile for 'beam_trawl_from_the_future' in year 2012"
    ):
        cumulative_footprint([history], _PROFILES)


def test_fractions_divide_by_the_supplied_mapped_seabed_area_and_refuse_nonsense():
    hours = _hours_for_sar(1.0, _PROFILE, _AREA)
    result = cumulative_footprint([_history({2012: hours})], _PROFILES)

    fractions = result.mapped_fraction(mapped_seabed_area_m2=4.0 * _AREA)

    expected = (1.0 - math.exp(-1.0)) / 4.0
    assert math.isclose(fractions.poisson, expected, rel_tol=1e-12)
    assert math.isclose(fractions.lower, expected, rel_tol=1e-12)
    assert math.isclose(fractions.upper, expected, rel_tol=1e-12)
    assert set(fractions.per_year) == {2012}
    assert math.isclose(fractions.per_year[2012], expected, rel_tol=1e-12)
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            result.mapped_fraction(mapped_seabed_area_m2=bad)


@given(
    sars=st.lists(
        st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=6,
    )
)
def test_property_floor_le_union_le_ceiling_le_cell(sars):
    """For any run of years in a cell: lower <= poisson <= upper <= area."""
    profiles = {2012 + i: {"trawlers": _PROFILE} for i in range(len(sars))}
    history = _history(
        {2012 + i: _hours_for_sar(sar, _PROFILE, _AREA) for i, sar in enumerate(sars)}
    )

    result = cumulative_footprint([history], profiles)

    b = result.mapped
    assert 0.0 <= b.lower_m2 <= b.poisson_m2 * (1 + 1e-12) + 1e-9
    assert b.poisson_m2 <= b.upper_m2 * (1 + 1e-12) + 1e-9
    assert b.upper_m2 <= _AREA * (1 + 1e-12)


def test_a_cell_with_no_years_of_effort_counts_as_a_cell_and_sweeps_nothing():
    """The store never produces one, but the type allows it: an empty history
    is a cell with zero footprint in every bracket member, not an error."""
    result = cumulative_footprint(
        [CellEffortHistory(cell=_CELL, mapped=True, hours_by_year={})], _PROFILES
    )

    assert result.cells == 1
    assert result.years == ()
    assert result.mapped == FootprintBracket(lower_m2=0.0, poisson_m2=0.0, upper_m2=0.0)


def test_the_caveats_name_both_directions_of_bias():
    """The headline is bracketed, not bounded from below: aggregation (real
    fleets revisit the same tows, year after year) pushes the true footprint
    BELOW the Poisson union; AIS under-coverage in early years and midwater
    contamination push the measured effort the other way. Both must be said."""
    text = " ".join(FOOTPRINT_CAVEATS).lower()
    assert "aggregat" in text
    assert "coverage" in text
    assert "midwater" in text
    assert "random" in text
    assert "mapped" in text
