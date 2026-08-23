"""Effort records and their aggregation onto the grid.

One :class:`EffortRecord` is one GFW fleet-day row's worth of effort: a cell, a
gear class, and the apparent fishing hours detected there. Aggregation answers
the overlap query's question — included-gear fishing hours per cell — and
nothing else; date/flag breakdowns belong to whoever slices the records before
handing them here.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass

from carbon_atlas.effort.gears import is_included_gear
from carbon_atlas.effort.grid import GridCell


@dataclass(frozen=True)
class EffortRecord:
    """Apparent fishing hours for one gear class in one grid cell.

    ``fishing_hours`` must be a finite non-negative number: a negative or NaN
    value absorbed into a sum silently corrupts every total downstream, so it
    is impossible to construct rather than merely unlikely to be aggregated.
    """

    cell: GridCell
    geartype: str
    fishing_hours: float

    def __post_init__(self) -> None:
        if math.isnan(self.fishing_hours) or self.fishing_hours < 0.0:
            raise ValueError(
                f"fishing_hours must be a non-negative number; got {self.fishing_hours!r}"
            )


def aggregate_fishing_hours(records: Iterable[EffortRecord]) -> dict[GridCell, float]:
    """Included-gear fishing hours summed per cell.

    A cell fished only by excluded gear is absent from the result — absent
    means "no included effort observed", which is not the same claim as a
    present 0.0 (a vessel looked-at and found not fishing).
    """
    totals: dict[GridCell, float] = {}
    for record in records:
        if is_included_gear(record.geartype):
            totals[record.cell] = totals.get(record.cell, 0.0) + record.fishing_hours
    return totals
