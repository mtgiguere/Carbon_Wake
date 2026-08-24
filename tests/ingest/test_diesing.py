"""Behavioral contract for the Diesing 2021 paired-raster reader.

The dataset publishes OC density as TWO rasters — mean and total uncertainty —
on an identical 500 m LAEA grid. The reader's job is to make the pair behave as
one honest source: a sample is a CarbonDensity (both numbers) or None (outside
the mapped seafloor), and every way the pairing could silently lie — mismatched
grids, a pixel mapped in one raster but not the other, a raster that cannot
even express absence — is a loud refusal instead.

Unit tests here author tiny paired rasters, which proves self-consistency only;
the @integration test at the bottom runs against a committed windowed copy of
the real published rasters (Blind spot A — see fixtures/real/diesing2021/).

Written test-first per TDD_CONTRACT.md.
"""

import math
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform as rio_transform

from carbon_atlas.carbon.density import CarbonDensity
from carbon_atlas.ingest.diesing import DensityRasterPair

_CRS = "EPSG:3035"  # same LAEA family as the real dataset
_NODATA = -3.4e38
# 3x3 rasters of 500 m pixels with a known origin in LAEA coordinates.
_TRANSFORM = from_origin(4321000, 3210000, 500, 500)

_MEAN = np.array(
    [
        [2.0, 4.0, _NODATA],
        [8.0, 16.0, _NODATA],
        [0.0, 32.0, _NODATA],
    ],
    dtype=np.float32,
)
_UNC = np.array(
    [
        [0.5, 1.0, _NODATA],
        [2.0, 4.0, _NODATA],
        [0.0, 8.0, _NODATA],
    ],
    dtype=np.float32,
)


def _write(path, data, *, transform=_TRANSFORM, crs=_CRS, nodata=_NODATA):
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(data, 1)
    return path


@pytest.fixture
def pair_paths(tmp_path):
    return (
        _write(tmp_path / "mean.tif", _MEAN),
        _write(tmp_path / "unc.tif", _UNC),
    )


def _lat_lon_of_pixel_center(row, col):
    """The WGS84 coordinates of a pixel center on the test grid."""
    x, y = _TRANSFORM * (col + 0.5, row + 0.5)
    lons, lats = rio_transform(_CRS, "EPSG:4326", [x], [y])
    return lats[0], lons[0]


def test_a_mapped_pixel_samples_to_its_mean_and_uncertainty_pair(pair_paths):
    """Sampling inside a mapped pixel returns BOTH rasters' values at that
    pixel as one CarbonDensity."""
    lat, lon = _lat_lon_of_pixel_center(1, 1)

    with DensityRasterPair(*pair_paths) as pair:
        density = pair.sample(lat, lon)

    assert density == CarbonDensity(mean=16.0, uncertainty=4.0)


def test_sampled_values_are_plain_python_floats(pair_paths):
    """The numpy float32 must not leak out of the reader: downstream layers
    (and eventually JSON) get plain floats, full stop."""
    lat, lon = _lat_lon_of_pixel_center(0, 0)

    with DensityRasterPair(*pair_paths) as pair:
        density = pair.sample(lat, lon)

    assert type(density.mean) is float
    assert type(density.uncertainty) is float


def test_a_nodata_pixel_is_absence_not_zero(pair_paths):
    """Unmapped seafloor answers None — 'not mapped' is a different claim from
    'zero carbon', and conflating them would paint false certainty on the map."""
    lat, lon = _lat_lon_of_pixel_center(0, 2)

    with DensityRasterPair(*pair_paths) as pair:
        assert pair.sample(lat, lon) is None


def test_a_point_outside_the_raster_is_absence_too(pair_paths):
    """Far outside the raster's extent is the same honest answer: None."""
    with DensityRasterPair(*pair_paths) as pair:
        assert pair.sample(0.0, -40.0) is None


def test_a_pixel_mapped_in_one_raster_but_not_the_other_fails_loudly(tmp_path):
    """Half a pair is a corrupt dataset: a mean without its uncertainty (or
    vice versa) must never become a value OR a silent None."""
    unc_with_hole = _UNC.copy()
    unc_with_hole[1, 1] = _NODATA
    mean_path = _write(tmp_path / "mean.tif", _MEAN)
    unc_path = _write(tmp_path / "unc.tif", unc_with_hole)
    lat, lon = _lat_lon_of_pixel_center(1, 1)

    with DensityRasterPair(mean_path, unc_path) as pair, pytest.raises(ValueError):
        pair.sample(lat, lon)


@pytest.mark.parametrize(
    "variation",
    [
        {"transform": from_origin(4321000, 3210000, 250, 250)},
        {"crs": "EPSG:32631"},
        {"data": np.zeros((4, 3), dtype=np.float32)},
    ],
    ids=["different-pixel-grid", "different-crs", "different-shape"],
)
def test_rasters_on_different_grids_are_refused_at_open(tmp_path, variation):
    """The pairing promise is 'same pixel, same place'. Any grid disagreement
    between the two rasters must refuse at open — sampling across mismatched
    grids would silently pair values from different patches of seafloor."""
    mean_path = _write(tmp_path / "mean.tif", _MEAN)
    data = variation.pop("data", _UNC.copy() if not variation else _UNC)
    unc_path = _write(tmp_path / "unc.tif", data, **variation)

    with pytest.raises(ValueError):
        DensityRasterPair(mean_path, unc_path)


def test_rasters_that_cannot_express_absence_are_refused_at_open(tmp_path):
    """A raster with no declared nodata cannot distinguish 'not mapped' from a
    measured value, so every sample from it would be an honesty gamble. Refuse."""
    mean_path = _write(tmp_path / "mean.tif", _MEAN, nodata=None)
    unc_path = _write(tmp_path / "unc.tif", _UNC)

    with pytest.raises(ValueError):
        DensityRasterPair(mean_path, unc_path)


def test_the_pair_closes_its_files_on_exit(pair_paths):
    """Context-manager exit releases both file handles; sampling after close is
    an error, not undefined behavior on a dead handle."""
    with DensityRasterPair(*pair_paths) as pair:
        pass

    with pytest.raises(Exception):  # broad on purpose: the closed-handle error type is rasterio's
        pair.sample(*_lat_lon_of_pixel_center(1, 1))


def test_the_pair_exposes_its_wgs84_envelope(pair_paths):
    """The rasters' extent as a WGS84 BoundingBox — the ETL's region scope
    derives from the carbon data itself, never from a hand-typed constant.
    Every pixel center must fall inside it (the envelope may be slightly
    generous where the projection curves; it must never be tight enough to
    exclude real pixels)."""
    with DensityRasterPair(*pair_paths) as pair:
        box = pair.wgs84_envelope()

        for row in range(3):
            for col in range(3):
                lat, lon = _lat_lon_of_pixel_center(row, col)
                assert box.lat_min <= lat <= box.lat_max
                assert box.lon_min <= lon <= box.lon_max


# --- Reality (Blind spot A) --------------------------------------------------


_REAL_DIR = Path(__file__).parent.parent / "fixtures" / "real" / "diesing2021"
_REAL_MEAN = _REAL_DIR / "OCdensity_quantrf_mean.win60.tif"
_REAL_UNC = _REAL_DIR / "OCdensity_quantrf_tot.unc.win60.tif"


@pytest.mark.integration
def test_real_published_rasters_sample_to_known_ground_truth():
    """A committed windowed copy of the real published rasters (German Bight
    coast: sea AND land pixels) samples to values pinned independently with
    rasterio at fixture-creation time — proving the reader's CRS handling,
    nodata convention, and pairing hold against what PANGAEA actually serves.
    Ground truth: fixtures/real/diesing2021/README.md."""
    with DensityRasterPair(_REAL_MEAN, _REAL_UNC) as pair:
        sea = pair.sample(53.901543, 7.599223)
        land = pair.sample(53.665470, 7.483920)
        far_outside = pair.sample(54.5, 3.0)

    assert math.isclose(sea.mean, 1.5459666, rel_tol=1e-6)
    assert math.isclose(sea.uncertainty, 2.3630075, rel_tol=1e-6)
    assert land is None
    assert far_outside is None


@pytest.mark.integration
def test_real_rasters_have_no_inconsistently_paired_pixel():
    """Exhaustive sweep of every pixel center in the real crop: each one is
    either a full CarbonDensity or a clean None — the corrupt-pair refusal
    never fires on the dataset as actually published, and the mapped/unmapped
    split matches the counts pinned at fixture-creation time (1868 / 1732)."""
    with rasterio.open(_REAL_MEAN) as src:
        transform, crs = src.transform, src.crs
    cols_rows = [(col + 0.5, row + 0.5) for row in range(60) for col in range(60)]
    xs, ys = zip(*[transform * cr for cr in cols_rows])
    lons, lats = rio_transform(crs, "EPSG:4326", list(xs), list(ys))

    with DensityRasterPair(_REAL_MEAN, _REAL_UNC) as pair:
        samples = [pair.sample(lat, lon) for lat, lon in zip(lats, lons)]

    mapped = [s for s in samples if s is not None]
    assert len(mapped) == 1868
    assert len(samples) - len(mapped) == 1732
    assert all(s.mean >= 0.0 and s.uncertainty >= 0.0 for s in mapped)


@pytest.mark.integration
def test_real_crop_envelope_contains_its_area_and_not_the_wider_sea():
    """The real crop's WGS84 envelope contains the pinned in-crop points (sea
    and land) and excludes Dogger Bank, ~250 km away — so scoping by envelope
    keeps the region honest in both directions."""
    with DensityRasterPair(_REAL_MEAN, _REAL_UNC) as pair:
        box = pair.wgs84_envelope()

    assert box.lat_min <= 53.901543 <= box.lat_max  # pinned sea pixel
    assert box.lon_min <= 7.599223 <= box.lon_max
    assert box.lat_min <= 53.665470 <= box.lat_max  # pinned land pixel
    assert box.lon_min <= 7.483920 <= box.lon_max
    assert not (box.lat_min <= 54.5 <= box.lat_max and box.lon_min <= 3.0 <= box.lon_max)
