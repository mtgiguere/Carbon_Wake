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
from collections.abc import Iterable
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


#: One profile per included GFW gear class (the ADR-0009 seam). Every figure
#: is citable; the exact computation of the derived widths is in ADR-0012.
DEFAULT_GEAR_PROFILES: dict[str, GearProfile] = {
    "trawlers": GearProfile(
        key="trawlers",
        gear_width_m=77.28,
        towing_speed_knots=3.0,
        penetration_depth_m=0.0244,
        provenance=(
            "Treated as otter trawls — Sala 2021's own default for unclassified "
            "vessels; per ADR-0009 the GFW class also contains midwater trawlers, "
            "so figures derived from it overstate bottom contact where midwater "
            "effort is common and must carry the honest label. Width 77.28 m: "
            "effort-weighted mean over GFW fishing-vessels-v3 (year 2012, 5,654 "
            "vessels) of Sala 2021's Eigaard et al. 2016 relationship "
            "W = 10.6608 x KW^0.2921 (ADR-0012). Speed 3.0 kn: midpoint of Sala "
            "2021's 2-4 kn otter-trawl plausibility range (from Eigaard 2016). "
            "Penetration 2.44 cm: Hiddink et al. 2017 via Sala 2021 / Atwood 2024."
        ),
    ),
    "dredge_fishing": GearProfile(
        key="dredge_fishing",
        gear_width_m=26.02,
        towing_speed_knots=2.25,
        penetration_depth_m=0.0547,
        provenance=(
            "Treated as towed (non-hydraulic) dredges, per ADR-0009. Width "
            "26.02 m: effort-weighted mean over GFW fishing-vessels-v3 (year "
            "2012, 105 vessels) of Sala 2021's Eigaard et al. 2016 relationship "
            "W = 0.3142 x LOA^1.2454 (ADR-0012). Speed 2.25 kn: midpoint of Sala "
            "2021's 2-2.5 kn dredge plausibility range (from Eigaard 2016). "
            "Penetration 5.47 cm: Hiddink et al. 2017 via Sala 2021 / Atwood 2024."
        ),
    ),
}


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


def bounded_disturbed_carbon_kg(
    *,
    fishing_hours: float,
    profile: GearProfile,
    density: CarbonDensity,
    cell_area_m2: float,
) -> DisturbedCarbon:
    """Disturbed carbon in ONE cell under the saturation bound (ADR-0014).

    The linear model counts the same sediment repeatedly wherever the swept
    area exceeds the cell (real hotspots reach swept-area ratios in the
    hundreds). The bound uses the trawling-footprint literature's Poisson
    estimator — passes over any point are randomly distributed within the
    cell (Amoroso et al. 2018) — whose closed form for the fraction swept at
    least once is 1 - exp(-SAR). Disturbed volume is that footprint times the
    penetration depth; the density's uncertainty scales by the same volume.

    Random placement overstates freshly swept area relative to real
    (aggregated) trawling, so the bound stays conservative-high — disclosed,
    like everything else, in ESTIMATE_CAVEATS.
    """
    if not math.isfinite(cell_area_m2) or cell_area_m2 <= 0.0:
        raise ValueError(f"cell_area_m2 must be finite and positive; got {cell_area_m2!r}")
    swept_area_ratio = swept_area_m2(fishing_hours, profile) / cell_area_m2
    footprint_m2 = cell_area_m2 * -math.expm1(-swept_area_ratio)
    volume_m3 = footprint_m2 * profile.penetration_depth_m
    return DisturbedCarbon(
        mean_kg=volume_m3 * density.mean,
        uncertainty_kg=volume_m3 * density.uncertainty,
    )


def disturbed_carbon_from_effort_density_sum(
    *,
    hours_density_mean_sum: float,
    hours_density_uncertainty_sum: float,
    profile: GearProfile,
) -> DisturbedCarbon:
    """Region-scale disturbed carbon from one per-gear moment.

    Because the per-cell factors (speed x width x penetration) are constant
    per gear, sum_cells(h x rho) can be computed where the cells live (SQL)
    and the constants applied here — and the result equals the per-cell path
    exactly (pinned by property test). Inputs are kg·h/m3 sums over a run's
    mapped cells; corrupt (negative/non-finite) moments are refused.
    """
    for name, value in (
        ("hours_density_mean_sum", hours_density_mean_sum),
        ("hours_density_uncertainty_sum", hours_density_uncertainty_sum),
    ):
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be finite and non-negative; got {value!r}")
    volume_rate_m3_per_hour_density = (
        profile.towing_speed_knots
        * METERS_PER_NAUTICAL_MILE
        * profile.gear_width_m
        * profile.penetration_depth_m
    )
    return DisturbedCarbon(
        mean_kg=volume_rate_m3_per_hour_density * hours_density_mean_sum,
        uncertainty_kg=volume_rate_m3_per_hour_density * hours_density_uncertainty_sum,
    )


def combine_disturbed(parts: Iterable[DisturbedCarbon]) -> DisturbedCarbon:
    """The total across gear classes: means AND uncertainties add linearly.

    Linear is the conservative (fully correlated) treatment — Diesing's total
    uncertainties include systematic components we cannot assume independent,
    and within a cell the gear classes share the same density anyway.
    Quadrature would claim an independence we do not have (SCIENCE_BASIS.md).
    No parts is the honest zero: 0 ± 0.
    """
    mean_kg = uncertainty_kg = 0.0
    for part in parts:
        mean_kg += part.mean_kg
        uncertainty_kg += part.uncertainty_kg
    return DisturbedCarbon(mean_kg=mean_kg, uncertainty_kg=uncertainty_kg)


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
