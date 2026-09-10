"""Reference zones — offshore wind farms — and the inside-versus-surroundings
contrast, pure.

Wind farms are de facto trawl exclosures in some countries (Belgium, the
Netherlands, Germany, Denmark close them to bottom fishing) and merely
constrained areas in others (many UK farms permit fishing). That makes them
the atlas's first *reference zones*: places where the effort layer can be
checked against something the fleet is known to avoid — and, later, natural
controls for inside/outside comparisons (docs/VALIDATION_SPIKE.md).

The honesty rule that governs this module (docs/IDEAS.md #3): verify the
exclusion in OUR effort data before narrating it, per country, and never
present a 5 km ring as a matched control. The measured contrast is served
with these caveats attached (ADR-0018).

Pure by construction: the parser consumes a GeoJSON mapping (EMODnet's WFS
output), the contrast consumes hours and areas the store measured.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass

from carbon_atlas.effort.grid import BoundingBox

#: Where the polygons come from, verbatim on every surface that shows them.
EMODNET_WINDFARMS_SOURCE = (
    "EMODnet Human Activities — Wind Farms (Polygons), CETMAR for EMODnet; WFS layer "
    "emodnet:windfarmspoly at https://ows.emodnet-humanactivities.eu/wfs (EPSG:4326); "
    "license CC-BY 4.0 (metadata record 8201070b-4b0b-4d54-8910-abcea5dce57f)."
)

#: The statuses that denote a farm physically present on the seabed. Planned,
#: Approved, Dismantled, and Test site farms exclude nothing.
REFERENCE_STATUSES: frozenset[str] = frozenset({"Production", "Construction"})

#: What the contrast is, and is not — served with every contrast figure.
ZONE_CAVEATS: tuple[str, ...] = (
    "The 5 km ring around each farm is a comparison area, not a matched control: "
    "farms sit on sites chosen for wind and depth, and their surroundings differ "
    "in fishability for reasons unrelated to the farm.",
    "Exclusion is a matter of national rules: Belgium, the Netherlands, Germany, "
    "and Denmark close producing farms to bottom fishing; many United Kingdom "
    "farms permit it. Read the contrast per country, never as one number.",
    "Only farms with a known commissioning year before the effort year are "
    "measured; farms whose commissioning year is unknown (EMODnet records none) "
    "are shown on the map but excluded from the contrast, and their count is "
    "reported.",
    "Effort is the GFW trawler + dredge classes as published (ADR-0009): "
    "midwater trawlers inside a farm are counted as effort even though they "
    "never touch the seabed; AIS coverage grew through the period, so early "
    "years under-detect effort inside and outside alike.",
    "Farm polygons are EMODnet's published outlines (annual update); safety "
    "zones and cable corridors around them are not represented.",
)


@dataclass(frozen=True)
class WindFarmZone:
    """One farm as a reference zone: the published facts, the geometry as
    GeoJSON, and a commissioning year that is None when EMODnet records
    none — unknown is never guessed."""

    name: str
    country: str
    status: str
    commissioned_year: int | None
    power_mw: float | None
    turbines: int | None
    area_km2: float | None
    geometry: Mapping


def _coordinates(geometry: Mapping) -> list[list[float]]:
    kind = geometry.get("type")
    if kind == "Polygon":
        return [point for ring in geometry["coordinates"] for point in ring]
    if kind == "MultiPolygon":
        return [point for polygon in geometry["coordinates"] for ring in polygon for point in ring]
    raise ValueError(f"unsupported geometry type {kind!r}; expected Polygon or MultiPolygon")


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def parse_emodnet_windfarms(
    collection: Mapping, *, region: BoundingBox
) -> tuple[WindFarmZone, ...]:
    """EMODnet's ``windfarmspoly`` FeatureCollection as reference zones:
    Production and Construction farms with at least one vertex inside
    ``region``, in the collection's order.

    A feature without geometry or without a status is refused, naming the
    farm — a zone that cannot be placed or whose existence is unknown must
    not be drawn as if it excluded anything.
    """
    zones: list[WindFarmZone] = []
    for feature in collection["features"]:
        properties = feature.get("properties") or {}
        name = properties.get("name") or "(unnamed)"
        status = properties.get("status")
        if status is None:
            raise ValueError(f"wind farm {name!r} has no status")
        geometry = feature.get("geometry")
        if geometry is None:
            raise ValueError(f"wind farm {name!r} has no geometry")
        if status not in REFERENCE_STATUSES:
            continue
        if not any(
            region.lon_min <= lon <= region.lon_max and region.lat_min <= lat <= region.lat_max
            for lon, lat in _coordinates(geometry)
        ):
            continue
        zones.append(
            WindFarmZone(
                name=name,
                country=properties.get("country"),
                status=status,
                commissioned_year=_optional_int(properties.get("year")),
                power_mw=_optional_float(properties.get("power_mw")),
                turbines=_optional_int(properties.get("n_turbines")),
                area_km2=_optional_float(properties.get("area_sqkm")),
                geometry=geometry,
            )
        )
    return tuple(zones)


@dataclass(frozen=True)
class ZoneContrast:
    """Trawl-hour density inside a set of farms versus in the ring around
    them, with the raw hours and areas it was made from. ``ratio`` is None
    when the ring saw no effort — no number, rather than infinity."""

    farm_km2: float
    inside_hours: float
    ring_km2: float
    ring_hours: float
    inside_density: float
    ring_density: float
    ratio: float | None


def zone_contrast(
    *, farm_km2: float, inside_hours: float, ring_km2: float, ring_hours: float
) -> ZoneContrast:
    """Densities (hours per km^2 of the FULL zone area, zero-effort parts
    included) and their ratio. Areas must be positive; hours non-negative."""
    for label, value in (("farm_km2", farm_km2), ("ring_km2", ring_km2)):
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"{label} must be finite and positive; got {value!r}")
    for label, value in (("inside_hours", inside_hours), ("ring_hours", ring_hours)):
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"{label} must be finite and non-negative; got {value!r}")
    inside_density = inside_hours / farm_km2
    ring_density = ring_hours / ring_km2
    return ZoneContrast(
        farm_km2=farm_km2,
        inside_hours=inside_hours,
        ring_km2=ring_km2,
        ring_hours=ring_hours,
        inside_density=inside_density,
        ring_density=ring_density,
        ratio=None if ring_density == 0.0 else inside_density / ring_density,
    )
