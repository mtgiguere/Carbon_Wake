"""CO2 estimates with uncertainty — the last pure link in the chain.

A region's DisturbedCarbon meets the preset catalog and becomes per-preset
CO2 quantities and an attributed range. All arithmetic flows through the
reactivity core's own functions: the mean and the uncertainty take the SAME
path (both are masses scaled by the same preset multiplier), so the pair can
never diverge, and there is exactly one place the disputed arithmetic lives.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from carbon_atlas.disturbance import DisturbedCarbon
from carbon_atlas.reactivity.presets import ReactivityPreset, estimate_co2, estimate_range


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
