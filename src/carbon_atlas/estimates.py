"""CO2 estimates with uncertainty — the last pure link in the chain.

A region's DisturbedCarbon meets the preset catalog and becomes per-preset
CO2 quantities and an attributed range. All arithmetic flows through the
reactivity core's own functions: the mean and the uncertainty take the SAME
path (both are masses scaled by the same preset multiplier), so the pair can
never diverge, and there is exactly one place the disputed arithmetic lives.
"""

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from carbon_atlas.disturbance import (
    DisturbedCarbon,
    GearProfile,
    bounded_disturbed_carbon_kg,
    combine_disturbed,
)
from carbon_atlas.overlap import TrawledCell
from carbon_atlas.reactivity.presets import ReactivityPreset, estimate_co2, estimate_range

#: The model caveats that must travel with every served estimate — the
#: honest-labeling rule applied to the number itself. Full provenance:
#: SCIENCE_BASIS.md "The disturbed-carbon model" and ADR-0012.
ESTIMATE_CAVEATS: tuple[str, ...] = (
    "Covers effort on MAPPED seafloor carbon only; effort on unmapped seafloor "
    "is excluded from the estimate and reported in effort_coverage.",
    "Aqueous first-year CO2 basis: preset fractions are first-year "
    "remineralization efficiencies of disturbed carbon (resettlement included); "
    "atmospheric figures exist only where the cited source quantified outgassing.",
    "Uncertainty reflects the carbon layer's per-pixel uncertainty only; gear "
    "width, towing speed, and penetration depth carry real spread that is NOT "
    "quantified here.",
    "Gear widths are fleet-averages (effort-weighted, from GFW's vessel table), "
    "not per-vessel; the GFW 'trawlers' class includes midwater trawlers "
    "(ADR-0009), so swept bottom area is overstated where midwater effort is "
    "common.",
    "KNOWN FLAW (identified 2026-08-24, fix scheduled): the model has no "
    "saturation — disturbed carbon is linear in effort, so heavily trawled "
    "cells (swept-area ratios in the hundreds in real hotspots) count the same "
    "sediment many times over and totals are OVERSTATED, possibly by a large "
    "factor. Treat current figures as pipeline-proof, not publication-grade. "
    "See SCIENCE_BASIS.md 'Known limitations'.",
)


@dataclass(frozen=True)
class CO2Quantity:
    """A CO2 mass (kg): mean + uncertainty, inseparable — same discipline as
    every quantity in this codebase."""

    mean_kg: float
    uncertainty_kg: float

    def __post_init__(self) -> None:
        for name, value in (("mean_kg", self.mean_kg), ("uncertainty_kg", self.uncertainty_kg)):
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative; got {value!r}")


@dataclass(frozen=True)
class PresetCO2:
    """One preset's CO2 for a disturbed-carbon quantity, on both bases.

    ``atmospheric`` is None when the preset does not quantify outgassing —
    the gap is reported with the uncertainty machinery intact, never filled.
    """

    preset: ReactivityPreset
    aqueous: CO2Quantity
    atmospheric: CO2Quantity | None


@dataclass(frozen=True)
class RegionEstimate:
    """A region's full estimate: the disturbed carbon it is built from, one
    entry per preset (catalog order), and the attributed range ends."""

    disturbed: DisturbedCarbon
    per_preset: tuple[PresetCO2, ...]
    low: PresetCO2
    high: PresetCO2


def disturbed_from_cells(
    trawled: Iterable[TrawledCell], profiles: Mapping[str, GearProfile]
) -> DisturbedCarbon:
    """A region's disturbed carbon: the BOUNDED model (ADR-0014) applied per
    cell per gear — each gear priced by its own profile against the cell's
    true area — combined linearly (the correlated convention).

    A gear the profile set cannot price raises, naming the gear: silently
    skipping it would drop real effort from the estimate.
    """
    return combine_disturbed(
        bounded_disturbed_carbon_kg(
            fishing_hours=hours,
            profile=profiles[gear],
            density=cell.carbon,
            cell_area_m2=cell.cell.area_m2,
        )
        for cell in trawled
        for gear, hours in cell.fishing_hours_by_gear.items()
    )


def _preset_co2(disturbed: DisturbedCarbon, preset: ReactivityPreset) -> PresetCO2:
    mean = estimate_co2(disturbed.mean_kg, preset)
    uncertainty = estimate_co2(disturbed.uncertainty_kg, preset)
    return PresetCO2(
        preset=preset,
        aqueous=CO2Quantity(mean_kg=mean.aqueous, uncertainty_kg=uncertainty.aqueous),
        atmospheric=(
            None
            if mean.atmospheric is None
            else CO2Quantity(mean_kg=mean.atmospheric, uncertainty_kg=uncertainty.atmospheric)
        ),
    )


def estimate_region_co2(
    disturbed: DisturbedCarbon, presets: Sequence[ReactivityPreset]
) -> RegionEstimate:
    """The per-preset CO2 quantities and attributed range for ``disturbed``.

    The range ends are chosen by the reactivity core's own ``estimate_range``
    (one source of range semantics), then carried here with their
    uncertainties attached. Raises for an empty preset sequence — a range
    over nothing has no meaning.
    """
    per_preset = tuple(_preset_co2(disturbed, preset) for preset in presets)
    attributed = estimate_range(disturbed.mean_kg, presets)
    by_key = {entry.preset.key: entry for entry in per_preset}
    return RegionEstimate(
        disturbed=disturbed,
        per_preset=per_preset,
        low=by_key[attributed.low_preset.key],
        high=by_key[attributed.high_preset.key],
    )
