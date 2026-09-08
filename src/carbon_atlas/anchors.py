"""Everyday-unit anchors — a CO2 mass as a count of something familiar.

Communication research says anchors land; the honesty move (docs/IDEAS.md
#6) is to anchor BOTH ends of the disputed range so the range itself is the
message, never to let one anchored figure stand in for a settled number.
Two rules travel with every anchor:

- the conversion factor is cited to a primary source and ships with the
  assumptions it rests on (docs/SCIENCE_BASIS.md "Everyday anchors");
- the anchor states its own comparability limit — the atlas's headline is
  AQUEOUS first-year CO2, while everyday emission figures are tailpipe
  (atmospheric) figures, so an anchor is for scale only, never an
  equivalence claim.

The arithmetic is one division applied to the mean and the uncertainty
alike — same-path discipline as every quantity in this codebase.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from carbon_atlas.estimates import CO2Quantity


@dataclass(frozen=True)
class EverydayAnchor:
    """A cited unit of everyday CO2: ``kg_co2_per_unit`` kilograms of CO2 per
    one ``unit_label``. ``basis`` is the comparability note that must render
    wherever the anchor does."""

    key: str
    unit_label: str
    kg_co2_per_unit: float
    citation: str
    basis: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.kg_co2_per_unit) or self.kg_co2_per_unit <= 0.0:
            raise ValueError(
                f"kg_co2_per_unit must be finite and positive; got {self.kg_co2_per_unit!r}"
            )


@dataclass(frozen=True)
class AnchorCount:
    """A CO2 quantity expressed in an anchor's units — mean and uncertainty
    together, with the anchor (and so its citation) attached."""

    anchor: EverydayAnchor
    mean_units: float
    uncertainty_units: float


#: US EPA, Green Vehicle Guide, "Greenhouse Gas Emissions from a Typical
#: Passenger Vehicle": "A typical passenger vehicle emits about 4.6 metric
#: tons of carbon dioxide per year", assuming 22.2 miles per gallon and
#: 11,500 miles per year at 8,887 g CO2 per gallon of gasoline. Verified
#: against the primary page (last updated 2026-06-03) on 2026-09-07.
PASSENGER_CAR_YEAR = EverydayAnchor(
    key="passenger_car_year",
    unit_label="typical passenger cars driven for a year",
    kg_co2_per_unit=4600.0,
    citation=(
        "US EPA, Greenhouse Gas Emissions from a Typical Passenger Vehicle: 4.6 metric "
        "tons CO2/yr, assuming 22.2 miles per gallon and 11,500 miles per year "
        "(8,887 g CO2 per gallon of gasoline). "
        "https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle"
    ),
    basis=(
        "For scale only. A car's figure is tailpipe CO2 released to the atmosphere; "
        "the atlas's headline is aqueous first-year CO2 in seawater, of which an "
        "unquantified fraction reaches the atmosphere (see the caveats)."
    ),
)

#: The anchor catalog, in display order.
EVERYDAY_ANCHORS: tuple[EverydayAnchor, ...] = (PASSENGER_CAR_YEAR,)


def anchor_count(quantity: CO2Quantity, anchor: EverydayAnchor) -> AnchorCount:
    """``quantity`` in ``anchor`` units: one division, applied to both
    components, so the relative uncertainty is untouched."""
    return AnchorCount(
        anchor=anchor,
        mean_units=quantity.mean_kg / anchor.kg_co2_per_unit,
        uncertainty_units=quantity.uncertainty_kg / anchor.kg_co2_per_unit,
    )


def anchor_counts(
    quantity: CO2Quantity, anchors: Sequence[EverydayAnchor] = EVERYDAY_ANCHORS
) -> tuple[AnchorCount, ...]:
    """``quantity`` in every catalog anchor's units, catalog order."""
    return tuple(anchor_count(quantity, anchor) for anchor in anchors)
