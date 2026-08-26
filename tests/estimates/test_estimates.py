"""Behavioral contract for CO2 estimates with uncertainty (pure core).

The last pure link in the chain: a region's DisturbedCarbon meets the preset
catalog and becomes per-preset CO2 quantities and an attributed range. All
arithmetic flows through the reactivity core's own functions — the mean AND
the uncertainty take the same path, so they cannot diverge — and the honesty
invariants hold with uncertainty attached: an unquantified atmospheric
fraction stays None, a derived preset stays flagged, and the range's ends
carry the presets that produced them.

Written test-first per TDD_CONTRACT.md.
"""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from carbon_atlas.disturbance import DisturbedCarbon
from carbon_atlas.estimates import estimate_region_co2
from carbon_atlas.reactivity.presets import (
    PUBLISHED_PRESETS,
    co2_from_disturbed_carbon,
    get_preset,
)

_DISTURBED = DisturbedCarbon(mean_kg=1000.0, uncertainty_kg=100.0)


@pytest.fixture(scope="module")
def region():
    return estimate_region_co2(_DISTURBED, PUBLISHED_PRESETS)


def test_sala_aqueous_co2_carries_the_scaled_uncertainty(region):
    """1000 kg ± 100 disturbed under Sala 2021: aqueous CO2 is
    1000 x 0.297 x 44/12 = 1089 kg, and the uncertainty scales by the SAME
    multiplier: 108.9 kg. Atmospheric stays None — Sala calls it unknown."""
    sala = next(p for p in region.per_preset if p.preset.key == "sala_2021")

    assert math.isclose(sala.aqueous.mean_kg, 1089.0, rel_tol=1e-9)
    assert math.isclose(sala.aqueous.uncertainty_kg, 108.9, rel_tol=1e-9)
    assert sala.atmospheric is None


def test_atwood_atmospheric_co2_scales_both_components(region):
    """Atwood 2024 (55% outgassing): atmospheric mean and uncertainty are the
    aqueous pair times 0.55 — the uncertainty is never left behind."""
    atwood = next(p for p in region.per_preset if p.preset.key == "atwood_2024_low")

    assert math.isclose(atwood.atmospheric.mean_kg, 1089.0 * 0.55, rel_tol=1e-9)
    assert math.isclose(atwood.atmospheric.uncertainty_kg, 108.9 * 0.55, rel_tol=1e-9)


def test_the_range_spans_hiddink_low_to_the_sala_flux_with_attribution(region):
    """The published dispute, with uncertainty attached: the low end is
    Hiddink's strongest correction (1000x below Sala), the high end the Sala
    flux — and each end names its preset, so the map can cite, not launder."""
    assert region.low.preset.key == "hiddink_2023_low"
    assert math.isclose(region.low.aqueous.mean_kg, 1.089, rel_tol=1e-9)
    assert region.high.preset.remineralization_fraction == 0.297
    assert math.isclose(region.high.aqueous.mean_kg, 1089.0, rel_tol=1e-9)
    assert math.isclose(
        region.high.aqueous.mean_kg / region.low.aqueous.mean_kg, 1000.0, rel_tol=1e-9
    )


def test_every_preset_appears_once_in_catalog_order(region):
    """Faithful transport: one entry per published preset, in catalog order,
    and the estimate keeps the original disturbed-carbon pair it was built
    from — provenance all the way up."""
    assert tuple(p.preset for p in region.per_preset) == PUBLISHED_PRESETS
    assert region.disturbed == _DISTURBED


def test_zero_disturbance_is_a_valid_all_zero_estimate():
    """A region where nothing was disturbed estimates 0 ± 0 CO2 under every
    preset — a reportable honest zero, not an error."""
    region = estimate_region_co2(
        DisturbedCarbon(mean_kg=0.0, uncertainty_kg=0.0), PUBLISHED_PRESETS
    )

    for entry in region.per_preset:
        assert entry.aqueous.mean_kg == 0.0
        assert entry.aqueous.uncertainty_kg == 0.0


def test_a_regions_disturbed_carbon_is_the_bounded_per_cell_sum():
    """disturbed_from_cells applies the BOUNDED model per cell per gear (each
    gear priced by its own profile against the cell's true area) and combines
    linearly — equal to the hand-built sum over the same cells."""
    from carbon_atlas.carbon.density import CarbonDensity
    from carbon_atlas.disturbance import (
        DEFAULT_GEAR_PROFILES,
        bounded_disturbed_carbon_kg,
        combine_disturbed,
    )
    from carbon_atlas.effort.grid import GridCell
    from carbon_atlas.estimates import disturbed_from_cells
    from carbon_atlas.overlap import TrawledCell

    hotspot = TrawledCell(
        cell=GridCell(lat_index=5390, lon_index=764),
        fishing_hours_by_gear={"trawlers": 427.6, "dredge_fishing": 2.0},
        carbon=CarbonDensity(mean=1.5652642, uncertainty=2.4579988),
    )
    light = TrawledCell(
        cell=GridCell(lat_index=5391, lon_index=760),
        fishing_hours_by_gear={"trawlers": 0.25},
        carbon=CarbonDensity(mean=4.2, uncertainty=1.1),
    )

    total = disturbed_from_cells([hotspot, light], DEFAULT_GEAR_PROFILES)

    expected = combine_disturbed(
        bounded_disturbed_carbon_kg(
            fishing_hours=hours,
            profile=DEFAULT_GEAR_PROFILES[gear],
            density=cell.carbon,
            cell_area_m2=cell.cell.area_m2,
        )
        for cell in (hotspot, light)
        for gear, hours in cell.fishing_hours_by_gear.items()
    )
    assert math.isclose(total.mean_kg, expected.mean_kg, rel_tol=1e-12)
    assert math.isclose(total.uncertainty_kg, expected.uncertainty_kg, rel_tol=1e-12)


def test_no_cells_disturb_nothing():
    """The empty region is the honest zero."""
    from carbon_atlas.disturbance import DEFAULT_GEAR_PROFILES
    from carbon_atlas.estimates import disturbed_from_cells

    total = disturbed_from_cells([], DEFAULT_GEAR_PROFILES)

    assert (total.mean_kg, total.uncertainty_kg) == (0.0, 0.0)


def test_a_gear_without_a_profile_fails_loudly():
    """A cell recording a gear the profile set cannot price must raise naming
    the gear — silently skipping it would drop real effort from the estimate."""
    from carbon_atlas.carbon.density import CarbonDensity
    from carbon_atlas.effort.grid import GridCell
    from carbon_atlas.estimates import disturbed_from_cells
    from carbon_atlas.overlap import TrawledCell

    cell = TrawledCell(
        cell=GridCell(lat_index=100, lon_index=100),
        fishing_hours_by_gear={"beam_trawlers": 1.0},
        carbon=CarbonDensity(mean=1.0, uncertainty=0.1),
    )

    with pytest.raises(KeyError, match="beam_trawlers"):
        disturbed_from_cells([cell], {})


def test_the_caveats_disclose_the_saturation_bounds_own_assumptions():
    """The 2026-08-24 saturation flaw is FIXED by the bounded model
    (ADR-0014), and the caveat changes with it: the served disclosure now
    names the bound's assumption (random/Poisson tow placement, which
    overstates freshly swept area versus real aggregated trawling) and that
    year-to-year depletion is still unmodeled. The old KNOWN-FLAW wording
    must be gone — a fixed flaw advertised as unfixed is also dishonest."""
    from carbon_atlas.estimates import ESTIMATE_CAVEATS

    text = " ".join(ESTIMATE_CAVEATS).lower()

    assert "saturation" in text
    assert "random" in text
    assert "aggregated" in text
    assert "amoroso" in text
    assert "known flaw" not in text


@pytest.mark.parametrize(
    ("mean_kg", "uncertainty_kg"),
    [(-0.1, 1.0), (1.0, -0.1), (float("nan"), 1.0), (1.0, float("inf"))],
)
def test_a_corrupt_co2_quantity_cannot_be_constructed(mean_kg, uncertainty_kg):
    """Same discipline as every quantity here: a negative or non-finite CO2
    mass (or uncertainty) is impossible to build."""
    from carbon_atlas.estimates import CO2Quantity

    with pytest.raises(ValueError):
        CO2Quantity(mean_kg=mean_kg, uncertainty_kg=uncertainty_kg)


def test_no_presets_is_refused():
    """A range over zero presets has no meaning — same rule as the core."""
    with pytest.raises(ValueError):
        estimate_region_co2(_DISTURBED, ())


@given(
    mean=st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False),
    unc=st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False),
)
def test_means_and_uncertainties_take_the_reactivity_cores_own_path(mean, unc):
    """Property: for every preset, the aqueous mean and uncertainty are
    exactly what the reactivity core computes for the mass and its
    uncertainty respectively — one source of arithmetic, zero drift."""
    region = estimate_region_co2(
        DisturbedCarbon(mean_kg=mean, uncertainty_kg=unc), PUBLISHED_PRESETS
    )

    for entry in region.per_preset:
        preset = get_preset(entry.preset.key)
        assert entry.aqueous.mean_kg == co2_from_disturbed_carbon(mean, preset)
        assert entry.aqueous.uncertainty_kg == co2_from_disturbed_carbon(unc, preset)
