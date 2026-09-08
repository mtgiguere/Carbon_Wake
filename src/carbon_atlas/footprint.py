"""The cumulative trawling footprint — a coverage claim, bracketed, pure.

"What fraction of the seabed has been trawled at least once since 2012?" is
the one headline the atlas can offer that needs no reactivity preset: it is
about where gear touched the bottom, physics both camps of the CO2 dispute
accept. It extends ADR-0014's within-year Poisson footprint across years —
but never as a single number. Per cell:

- **floor**   = the largest single-year footprint. That seabed was swept in
  that year whatever the other years did; no cross-year assumption needed.
- **ceiling** = the annual footprints summed, capped at the cell. Years cannot
  overlap less than not at all.
- **Poisson union** = 1 - exp(-sum of the years' SARs): the footprint if tow
  placement were independent and random across years too. Real fleets revisit
  the same grounds year after year (aggregation), so the truth tends to sit
  BELOW this — while AIS under-coverage in early years and the midwater share
  of the GFW trawler class push the measured effort the other way. The bracket
  travels with the headline; the caveats say which way each bias points.

Each year's SAR is priced with THAT year's gear profiles (ADR-0016). Cells on
mapped carbon give a fraction (the denominator is the carbon-mapped seabed,
supplied by the caller from the raster itself); all effort cells give an area
only — no honest denominator exists for effort the carbon map does not cover.
"""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from carbon_atlas.disturbance import GearProfile, poisson_footprint_fraction, swept_area_ratio
from carbon_atlas.effort.grid import GridCell

#: The honesty that must travel with every served footprint figure.
FOOTPRINT_CAVEATS: tuple[str, ...] = (
    "A coverage claim, not a CO2 claim: the fraction of seabed swept at least "
    "once by the GFW trawler + dredge classes, independent of any reactivity "
    "preset.",
    "The headline is the Poisson union — tow placement assumed independent and "
    "random within AND across years (Amoroso et al. 2018's within-year "
    "assumption, extended). Real trawling is aggregated (fleets revisit the "
    "same tows year after year), so the true footprint tends to sit BELOW the "
    "union; the floor (largest single-year footprint) needs no cross-year "
    "assumption at all.",
    "AIS coverage grew through the period (thin before 2017): early years "
    "under-detect effort, pushing every figure LOW; the GFW 'trawlers' class "
    "includes midwater trawlers (ADR-0009), pushing swept bottom area HIGH. The "
    "two do not cancel in any knowable way.",
    "The fraction's denominator is the carbon-mapped seabed (Diesing 2021's "
    "mapped pixels); effort on unmapped seafloor is reported as an area only, "
    "because no honest denominator exists for it.",
    "A 0.01-degree cell whose center falls on mapped carbon counts as fully "
    "mapped; the cell grid and the 500 m raster grid do not coincide exactly.",
)

#: How the headline is computed and what the literature says for the same
#: region — served with every footprint figure. Provenance: SCIENCE_BASIS.md
#: "The cumulative footprint" (Amoroso 2018 Table 1 read from PMC6205437).
FOOTPRINT_METHOD: dict[str, str] = {
    "headline": "poisson_union",
    "description": (
        "Per 0.01-degree cell: swept-area ratio per year (hours x speed x width / "
        "cell area, that year's fleet widths), footprint fraction 1 - exp(-SAR); "
        "the union across years is 1 - exp(-sum of SARs); floor = largest "
        "single-year footprint; ceiling = annual footprints summed, capped at the "
        "cell. Areas sum over cells; the fraction divides by the carbon-mapped "
        "seabed area."
    ),
    "citation": (
        "Amoroso, R.O., et al. (2018). Bottom trawl fishing footprints on the "
        "world's continental shelves. PNAS 115(43), E10275-E10282. "
        "DOI: 10.1073/pnas.1802379115."
    ),
    "published_comparator": (
        "Amoroso et al. 2018, Table 1, North Sea (ICES 4a-4c), VMS-based effort "
        "2010-2012, depths 0-1000 m: regional SAR 1.191 per year; 42.2 % of the "
        "region trawled per year under the random-placement assumption (their "
        "approach B, the same estimator as this headline), 89.3 % under the "
        "grid-cell assumption, 51.7 % under the uniform assumption. Compare with "
        "this atlas's per-year mapped footprints, not with the multi-year union."
    ),
}


@dataclass(frozen=True)
class CellEffortHistory:
    """One cell's effort across years: year -> gear class -> fishing hours,
    plus whether the carbon layer maps the cell."""

    cell: GridCell
    mapped: bool
    hours_by_year: Mapping[int, Mapping[str, float]]


@dataclass(frozen=True)
class FootprintBracket:
    """Floor, Poisson union, ceiling — areas (m^2), always in that order."""

    lower_m2: float
    poisson_m2: float
    upper_m2: float


@dataclass(frozen=True)
class FootprintFractions:
    """The bracket — and each year's own footprint — as fractions of a stated
    denominator."""

    lower: float
    poisson: float
    upper: float
    per_year: Mapping[int, float]


@dataclass(frozen=True)
class CumulativeFootprint:
    """The union across years, over mapped cells (fraction-able) and over all
    effort cells (area only), with each year's own footprint alongside."""

    years: tuple[int, ...]
    cells: int
    mapped: FootprintBracket
    all_effort: FootprintBracket
    per_year_mapped_m2: Mapping[int, float]

    def mapped_fraction(self, *, mapped_seabed_area_m2: float) -> FootprintFractions:
        """The mapped-seabed bracket over the carbon-mapped seabed area."""
        if not math.isfinite(mapped_seabed_area_m2) or mapped_seabed_area_m2 <= 0.0:
            raise ValueError(
                f"mapped_seabed_area_m2 must be finite and positive; got {mapped_seabed_area_m2!r}"
            )
        return FootprintFractions(
            lower=self.mapped.lower_m2 / mapped_seabed_area_m2,
            poisson=self.mapped.poisson_m2 / mapped_seabed_area_m2,
            upper=self.mapped.upper_m2 / mapped_seabed_area_m2,
            per_year={
                year: area / mapped_seabed_area_m2
                for year, area in sorted(self.per_year_mapped_m2.items())
            },
        )


class _Accumulator:
    def __init__(self) -> None:
        self.lower = self.poisson = self.upper = 0.0

    def add(self, cell_area_m2: float, sar_by_year: Mapping[int, float]) -> None:
        if not sar_by_year:
            return
        fractions = [poisson_footprint_fraction(sar) for sar in sar_by_year.values()]
        self.lower += cell_area_m2 * max(fractions)
        self.poisson += cell_area_m2 * poisson_footprint_fraction(sum(sar_by_year.values()))
        self.upper += cell_area_m2 * min(1.0, sum(fractions))

    def bracket(self) -> FootprintBracket:
        return FootprintBracket(lower_m2=self.lower, poisson_m2=self.poisson, upper_m2=self.upper)


def cumulative_footprint(
    histories: Iterable[CellEffortHistory],
    profiles_by_year: Mapping[int, Mapping[str, GearProfile]],
) -> CumulativeFootprint:
    """The bracketed footprint of ``histories`` under ``profiles_by_year``.

    Per cell and year, SAR sums over gear classes (each priced with that
    year's profile); the year's footprint fraction is the Poisson fraction of
    that SAR. A year or gear without a profile raises, naming it — silently
    skipping effort would understate coverage.
    """
    years: set[int] = set()
    cells = 0
    mapped_acc, all_acc = _Accumulator(), _Accumulator()
    per_year_mapped: dict[int, float] = {}

    for history in histories:
        cells += 1
        area = history.cell.area_m2
        sar_by_year: dict[int, float] = {}
        for year, hours_by_gear in history.hours_by_year.items():
            if year not in profiles_by_year:
                raise KeyError(f"no gear profiles for year {year}")
            profiles = profiles_by_year[year]
            sar = 0.0
            for gear, hours in hours_by_gear.items():
                if gear not in profiles:
                    raise KeyError(f"no gear profile for {gear!r} in year {year}")
                sar += swept_area_ratio(hours, profiles[gear], area)
            sar_by_year[year] = sar
            years.add(year)
        all_acc.add(area, sar_by_year)
        if history.mapped:
            mapped_acc.add(area, sar_by_year)
            for year, sar in sar_by_year.items():
                per_year_mapped[year] = per_year_mapped.get(
                    year, 0.0
                ) + area * poisson_footprint_fraction(sar)

    return CumulativeFootprint(
        years=tuple(sorted(years)),
        cells=cells,
        mapped=mapped_acc.bracket(),
        all_effort=all_acc.bracket(),
        per_year_mapped_m2=per_year_mapped,
    )
