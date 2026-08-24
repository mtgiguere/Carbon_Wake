"""The disturbed-carbon model — Sala 2021's swept-volume chain, pure.

fishing hours x towing speed x gear width -> swept area; x penetration depth
-> disturbed volume; x OC density -> disturbed carbon mass. The provenance of
every parameter travels with it in a GearProfile, and the mass inherits the
carbon density's per-pixel uncertainty exactly (scalar multiplication) — the
never-a-bare-number rule extended to the quantity the presets consume.

Full provenance and the deviations from Sala's global model:
docs/SCIENCE_BASIS.md ("The disturbed-carbon model") and ADR-0012.
"""

import math
from dataclasses import dataclass

from carbon_atlas.carbon.density import CarbonDensity

#: Meters per nautical mile — a knot is exactly this many meters per hour, by
#: definition. Fixed conversion, not a modelling choice.
METERS_PER_NAUTICAL_MILE = 1852.0

#: No towed gear penetrates anywhere near a meter of sediment (hydraulic
#: dredges, the deepest, average 0.1611 m — Hiddink 2017). A profile past
#: this is a unit mistake (centimeters typed as meters), not a gear.
_MAX_PENETRATION_DEPTH_M = 1.0


@dataclass(frozen=True)
class GearProfile:
    """One gear class's swept-volume parameters, with their provenance.

    ``provenance`` records where every number comes from (citation, and the
    derivation when a figure is computed rather than quoted) — a profile is
    not usable science without it.
    """

    key: str
    gear_width_m: float
    towing_speed_knots: float
    penetration_depth_m: float
    provenance: str

    def __post_init__(self) -> None:
        for name, value in (
            ("gear_width_m", self.gear_width_m),
            ("towing_speed_knots", self.towing_speed_knots),
            ("penetration_depth_m", self.penetration_depth_m),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive; got {value!r}")
        if self.penetration_depth_m > _MAX_PENETRATION_DEPTH_M:
            raise ValueError(
                f"penetration_depth_m={self.penetration_depth_m!r} exceeds "
                f"{_MAX_PENETRATION_DEPTH_M} m — no towed gear does that; "
                f"likely centimeters passed as meters"
            )


@dataclass(frozen=True)
class DisturbedCarbon:
    """Disturbed organic-carbon mass (kg): mean + uncertainty, inseparable —
    the same discipline as :class:`CarbonDensity`, one derivation later."""

    mean_kg: float
    uncertainty_kg: float

    def __post_init__(self) -> None:
        for name, value in (("mean_kg", self.mean_kg), ("uncertainty_kg", self.uncertainty_kg)):
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative; got {value!r}")


def swept_area_m2(fishing_hours: float, profile: GearProfile) -> float:
    """Seabed area (m^2) swept by ``fishing_hours`` of towing under ``profile``.

    Sala 2021's SAR numerator for one cell: distance (speed x time) times gear
    width. Raises for negative or non-finite hours — corrupt effort must never
    reach a CO2 figure.
    """
    if not math.isfinite(fishing_hours) or fishing_hours < 0.0:
        raise ValueError(f"fishing_hours must be finite and non-negative; got {fishing_hours!r}")
    distance_m = fishing_hours * profile.towing_speed_knots * METERS_PER_NAUTICAL_MILE
    return distance_m * profile.gear_width_m


def disturbed_carbon_kg(
    fishing_hours: float, profile: GearProfile, density: CarbonDensity
) -> DisturbedCarbon:
    """The organic-carbon mass disturbed by ``fishing_hours`` of towing under
    ``profile`` on sediment of ``density``.

    Swept area x penetration depth prices the disturbed volume at the cell's
    OC density; the density's per-pixel uncertainty scales with the same
    factor — exactly, since the operation is scalar multiplication.
    """
    volume_m3 = swept_area_m2(fishing_hours, profile) * profile.penetration_depth_m
    return DisturbedCarbon(
        mean_kg=volume_m3 * density.mean,
        uncertainty_kg=volume_m3 * density.uncertainty,
    )
