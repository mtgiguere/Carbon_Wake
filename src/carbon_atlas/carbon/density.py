"""Organic-carbon density, mean and uncertainty as one inseparable value.

Diesing 2021 publishes OC density as paired rasters — a mean and a per-pixel
total uncertainty (both kg/m3). The never-a-bare-number rule, enforced at the
type level: the pair IS the value, so code that has a density always has its
uncertainty, and nothing downstream can quietly drop it.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CarbonDensity:
    """Organic-carbon density (kg/m3): predicted mean + total uncertainty.

    Both components must be finite and non-negative. This makes the raster
    nodata sentinel (-3.4e38) impossible to smuggle in as a measurement —
    converting nodata to *absence* is the reader's job, before construction.
    NaN/inf are rejected for the same reason: they poison downstream sums
    silently, which is how a bare (false) number reaches the map.
    """

    mean: float
    uncertainty: float

    def __post_init__(self) -> None:
        for name, value in (("mean", self.mean), ("uncertainty", self.uncertainty)):
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative; got {value!r}")
