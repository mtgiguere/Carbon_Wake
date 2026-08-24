"""The overlap query, proven end to end on real published data.

This is build-order step 3's milestone test: a year of real GFW effort rows
(German Bight box, 2012 — see fixtures/real/gfw/README.md) flows through the
real parser, the real gear seam, the real aggregation, and the real Diesing
raster pair, and the join's two sides match ground truth computed at
fixture-creation time with plain dicts and raw rasterio — independently of
every carbon_atlas function exercised here.

Written test-first per TDD_CONTRACT.md (RED until the composition agrees with
the independently pinned numbers).
"""

import math
from pathlib import Path

import pytest

from carbon_atlas.effort.aggregate import aggregate_fishing_hours
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.ingest.diesing import DensityRasterPair
from carbon_atlas.ingest.gfw import parse_fleet_daily
from carbon_atlas.overlap import overlap_effort_with_carbon

_REAL = Path(__file__).parent.parent / "fixtures" / "real"
_EFFORT_CSV = _REAL / "gfw" / "fleet-daily-100-v3-2012.german-bight-box.csv"
_CARBON_MEAN = _REAL / "diesing2021" / "OCdensity_quantrf_mean.win60.tif"
_CARBON_UNC = _REAL / "diesing2021" / "OCdensity_quantrf_tot.unc.win60.tif"


@pytest.mark.integration
def test_a_real_year_of_effort_joins_against_real_carbon_to_ground_truth():
    """Parse -> aggregate -> join, all on committed real samples. The counts,
    the hours on both sides, and the busiest cell's full pairing must equal
    the independently computed ground truth in fixtures/real/gfw/README.md."""
    with _EFFORT_CSV.open(encoding="utf-8") as f:
        effort = aggregate_fishing_hours(parse_fleet_daily(f))

    with DensityRasterPair(_CARBON_MEAN, _CARBON_UNC) as pair:
        result = overlap_effort_with_carbon(effort, pair.sample)

    assert len(result.trawled) == 220
    assert len(result.unmapped_effort) == 97
    assert math.isclose(result.trawled_fishing_hours, 139.7554, rel_tol=1e-9)
    assert math.isclose(result.unmapped_fishing_hours, 168.4296, rel_tol=1e-9)

    # Per-gear ground truth (recomputed independently 2026-08-24): on MAPPED
    # cells every hour is trawlers; all 18.3979 dredge hours sit on unmapped
    # nearshore cells (150.0317 trawler hours join them there). 33 mapped
    # cells carry dredge records (all 0.0 h): 22 alongside trawlers, 11 alone.
    mapped_by_gear: dict[str, float] = {}
    for t in result.trawled:
        for gear, hours in t.fishing_hours_by_gear.items():
            mapped_by_gear[gear] = mapped_by_gear.get(gear, 0.0) + hours
    assert math.isclose(mapped_by_gear["trawlers"], 139.7554, rel_tol=1e-9)
    assert math.isclose(mapped_by_gear["dredge_fishing"], 0.0, abs_tol=1e-12)
    assert sum(1 for t in result.trawled if "dredge_fishing" in t.fishing_hours_by_gear) == 33

    unmapped_by_gear: dict[str, float] = {}
    for by_gear in result.unmapped_effort.values():
        for gear, hours in by_gear.items():
            unmapped_by_gear[gear] = unmapped_by_gear.get(gear, 0.0) + hours
    assert math.isclose(unmapped_by_gear["trawlers"], 150.0317, rel_tol=1e-9)
    assert math.isclose(unmapped_by_gear["dredge_fishing"], 18.3979, rel_tol=1e-9)

    busiest = max(result.trawled, key=lambda t: t.total_fishing_hours)
    assert busiest.cell == GridCell(lat_index=5390, lon_index=764)
    assert set(busiest.fishing_hours_by_gear) == {"trawlers"}
    assert math.isclose(busiest.fishing_hours_by_gear["trawlers"], 15.0057, rel_tol=1e-9)
    assert math.isclose(busiest.carbon.mean, 1.5652642, rel_tol=1e-6)
    assert math.isclose(busiest.carbon.uncertainty, 2.4579988, rel_tol=1e-6)
