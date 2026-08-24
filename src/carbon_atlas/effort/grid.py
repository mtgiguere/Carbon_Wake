"""The 0.01-degree effort grid.

GFW's fleet-daily product bins effort into cells 0.01 degrees on a side (WGS84),
identified by the decimal-degree coordinates of each cell's lower-left corner.
Floats are how the corners arrive, but they are a poor identity — 55.55 * 100 is
5554.999... in binary — so a cell's identity here is its corner in integer
centidegrees, snapped once at the boundary and exact forever after.
"""

from dataclasses import dataclass

#: How far (in centidegrees) a coordinate may sit from an exact 0.01-degree
#: corner and still be that corner. Float noise on a genuine corner is ~1e-12;
#: the nearest wrong-grid value (e.g. a 0.005-degree grid) is 0.5 away. Nine
#: orders of magnitude separate signal from noise, so the threshold provably
#: sits between them (the Blind-spot-C rule).
_SNAP_TOLERANCE = 1e-6


@dataclass(frozen=True)
class GridCell:
    """One 0.01-degree grid cell, identified by its lower-left corner in
    integer centidegrees (latitude 55.55 N -> ``lat_index`` 5555)."""

    lat_index: int
    lon_index: int

    @property
    def center_lat(self) -> float:
        """The cell center's latitude — where point samples represent the cell."""
        return (self.lat_index + 0.5) / 100

    @property
    def center_lon(self) -> float:
        """The cell center's longitude — where point samples represent the cell."""
        return (self.lon_index + 0.5) / 100


@dataclass(frozen=True)
class BoundingBox:
    """A WGS84 lat/lon box — the ETL's region scope (in practice, the carbon
    dataset's envelope). Bounds are inclusive."""

    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    def __post_init__(self) -> None:
        if self.lat_min > self.lat_max or self.lon_min > self.lon_max:
            raise ValueError(
                f"inverted bounding box: lat [{self.lat_min}, {self.lat_max}], "
                f"lon [{self.lon_min}, {self.lon_max}]"
            )

    def contains_cell(self, cell: GridCell) -> bool:
        """Whether ``cell`` is in scope — judged by its CENTER, the same
        representative point the carbon layer is sampled at, so scoping and
        sampling can never disagree about where a cell is."""
        return (
            self.lat_min <= cell.center_lat <= self.lat_max
            and self.lon_min <= cell.center_lon <= self.lon_max
        )


def _snap(value: float, axis: str, min_index: int, max_index: int) -> int:
    """``value`` (decimal degrees) as an exact centidegree index, or ValueError
    if it is not on the grid / not a possible lower-left corner."""
    scaled = value * 100
    index = round(scaled)
    if abs(scaled - index) > _SNAP_TOLERANCE:
        raise ValueError(
            f"{axis}={value!r} is not on the 0.01-degree grid; "
            f"refusing to snap a wrong-grid coordinate onto a cell"
        )
    if not min_index <= index <= max_index:
        raise ValueError(
            f"{axis}={value!r} cannot be a cell's lower-left corner; "
            f"valid range is [{min_index / 100}, {max_index / 100}]"
        )
    return index


def cell_from_lower_left(lat: float, lon: float) -> GridCell:
    """The cell whose lower-left corner is at (``lat``, ``lon``) decimal degrees.

    Raises ``ValueError`` for a coordinate that is not a 0.01-degree corner
    (wrong-grid input must fail loudly, never be silently relocated) or that
    names a cell outside the world (latitude corners span [-90, 90) and
    longitude corners [-180, 180) — a corner AT +90 or +180 would put the cell
    beyond the pole / antimeridian).
    """
    return GridCell(
        lat_index=_snap(lat, "lat", min_index=-9000, max_index=8999),
        lon_index=_snap(lon, "lon", min_index=-18000, max_index=17999),
    )
