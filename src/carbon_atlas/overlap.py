"""The effort-carbon overlap join — the project's central query, kept pure.

Given aggregated trawling effort per grid cell and a way to sample the carbon
layer at a point, partition the effort into cells on MAPPED carbon (each
carrying its hours and the full mean+uncertainty carbon pair) and cells on
UNMAPPED seafloor. The unmapped side is a first-class result, never a silent
drop: a map that quietly discards what it cannot color is lying by omission.

Pure by injection: the carbon layer arrives as a callable, so this module needs
no rasterio and the join logic lives on the airtight side of the test boundary
(docs/ARCHITECTURE.md §3). The raster-backed sampler is wired in by the caller
(e.g. ``DensityRasterPair.sample``).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.effort.grid import GridCell

#: A point sample of the carbon layer: (lat, lon) -> density, or None where
#: the layer maps nothing.
CarbonSampler = Callable[[float, float], CarbonDensity | None]


@dataclass(frozen=True)
class TrawledCell:
    """One cell where trawling effort sits on mapped seafloor carbon.

    Hours are carried PER GEAR CLASS: the disturbed-carbon model (ADR-0012)
    prices the classes differently, so their identity must survive the join.
    """

    cell: GridCell
    fishing_hours_by_gear: dict[str, float]
    carbon: CarbonDensity

    @property
    def total_fishing_hours(self) -> float:
        """All gears' hours in this cell — derived, never stored separately."""
        return sum(self.fishing_hours_by_gear.values())


@dataclass(frozen=True)
class OverlapResult:
    """The join's two sides: effort on mapped carbon, and effort the carbon
    layer says nothing about. Together they account for every input cell."""

    trawled: tuple[TrawledCell, ...]
    unmapped_effort: dict[GridCell, dict[str, float]]

    @property
    def trawled_fishing_hours(self) -> float:
        """Total fishing hours (all gears) that landed on mapped carbon."""
        return sum(t.total_fishing_hours for t in self.trawled)

    @property
    def unmapped_fishing_hours(self) -> float:
        """Total fishing hours (all gears) outside the mapped carbon area."""
        return sum(sum(by_gear.values()) for by_gear in self.unmapped_effort.values())


def overlap_effort_with_carbon(
    effort: Mapping[GridCell, Mapping[str, float]], sample_carbon: CarbonSampler
) -> OverlapResult:
    """Partition ``effort`` (per-gear hours per cell) by whether the carbon
    layer maps each cell.

    Each cell is sampled at its CENTER (its representative point). Output is
    sorted by cell identity (south-to-north, then west-to-east) so identical
    inputs produce identical artifacts run after run.
    """
    trawled: list[TrawledCell] = []
    unmapped: dict[GridCell, dict[str, float]] = {}
    for cell in sorted(effort, key=lambda c: (c.lat_index, c.lon_index)):
        by_gear = dict(effort[cell])
        carbon = sample_carbon(cell.center_lat, cell.center_lon)
        if carbon is None:
            unmapped[cell] = by_gear
        else:
            trawled.append(TrawledCell(cell=cell, fishing_hours_by_gear=by_gear, carbon=carbon))
    return OverlapResult(trawled=tuple(trawled), unmapped_effort=unmapped)
