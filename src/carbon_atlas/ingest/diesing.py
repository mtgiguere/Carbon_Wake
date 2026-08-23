"""Reader for Diesing 2021's paired OC-density rasters (PANGAEA 928272).

The dataset expresses one quantity as two GeoTIFFs — predicted mean and total
uncertainty, kg/m3, on an identical 500 m LAEA grid — and this reader makes the
pair behave as one honest source. A sample is a CarbonDensity (never a bare
mean) or None (seafloor the model did not map — which is NOT a zero). Every way
the pairing could silently lie is a loud refusal instead: rasters on different
grids, a raster that declares no nodata (and so cannot express absence), or a
pixel mapped in one raster but not the other.
"""

from pathlib import Path

import rasterio
from rasterio.warp import transform as transform_coordinates
from rasterio.windows import Window

from carbon_atlas.carbon.density import CarbonDensity

_WGS84 = "EPSG:4326"


class DensityRasterPair:
    """The mean + uncertainty rasters, opened together and sampled together."""

    def __init__(self, mean_path: Path, uncertainty_path: Path) -> None:
        self._mean = rasterio.open(mean_path)
        self._uncertainty = rasterio.open(uncertainty_path)
        try:
            self._validate_pairing()
        except ValueError:
            self.close()
            raise

    def _validate_pairing(self) -> None:
        for attribute in ("crs", "transform", "shape"):
            mean_value = getattr(self._mean, attribute)
            uncertainty_value = getattr(self._uncertainty, attribute)
            if mean_value != uncertainty_value:
                raise ValueError(
                    f"mean and uncertainty rasters disagree on {attribute}: "
                    f"{mean_value!r} vs {uncertainty_value!r}; sampling across "
                    f"mismatched grids would pair values from different seafloor"
                )
        for dataset, role in ((self._mean, "mean"), (self._uncertainty, "uncertainty")):
            if dataset.nodata is None:
                raise ValueError(
                    f"{role} raster declares no nodata value, so it cannot "
                    f"distinguish 'not mapped' from a measurement; refusing"
                )

    def sample(self, lat: float, lon: float) -> CarbonDensity | None:
        """The carbon density at a WGS84 point, or None where the dataset maps
        nothing (outside its extent, on land, or unmodelled seafloor).

        Raises ``ValueError`` for a pixel mapped in one raster but not the
        other — half a pair must never become a value or a silent None.
        """
        xs, ys = transform_coordinates(_WGS84, self._mean.crs, [lon], [lat])
        row, col = self._mean.index(xs[0], ys[0])
        if not (0 <= row < self._mean.height and 0 <= col < self._mean.width):
            return None

        window = Window(col, row, 1, 1)
        mean = float(self._mean.read(1, window=window)[0, 0])
        uncertainty = float(self._uncertainty.read(1, window=window)[0, 0])
        mean_absent = mean == self._mean.nodata
        uncertainty_absent = uncertainty == self._uncertainty.nodata
        if mean_absent != uncertainty_absent:
            raise ValueError(
                f"pixel (row={row}, col={col}) is mapped in the "
                f"{'uncertainty' if mean_absent else 'mean'} raster but not its "
                f"partner; the dataset pair is corrupt at this pixel"
            )
        if mean_absent:
            return None
        return CarbonDensity(mean=mean, uncertainty=uncertainty)

    def close(self) -> None:
        self._mean.close()
        self._uncertainty.close()

    def __enter__(self) -> "DensityRasterPair":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
