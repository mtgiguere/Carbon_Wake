"""Behavioral contract for the carbon-density value type.

Diesing 2021 publishes organic-carbon density as PAIRED rasters — a mean and a
per-pixel total uncertainty (both kg/m3). The project's never-a-bare-number
rule, applied at the type level: a carbon density that has lost its uncertainty
must be impossible to construct, and the raster's nodata sentinel (-3.4e38)
must be impossible to smuggle in as if it were a measurement.

Written test-first per TDD_CONTRACT.md.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from carbon_atlas.carbon.density import CarbonDensity


def test_a_density_carries_its_mean_and_its_uncertainty_together():
    """The pair is the value: Dogger Bank's ~2.03 kg/m3 is meaningless without
    its ~2.15 kg/m3 total uncertainty riding along."""
    density = CarbonDensity(mean=2.0309148, uncertainty=2.1486087)

    assert density.mean == 2.0309148
    assert density.uncertainty == 2.1486087


@pytest.mark.parametrize(("mean", "uncertainty"), [(0.0, 0.0), (0.0, 1.5), (55.0, 0.0)])
def test_zero_mean_or_zero_uncertainty_is_valid(mean, uncertainty):
    """A carbon-free pixel (mean 0) and a hypothetically exact prediction
    (uncertainty 0) are both physically meaningful boundaries — inclusive."""
    density = CarbonDensity(mean=mean, uncertainty=uncertainty)

    assert density.mean == mean
    assert density.uncertainty == uncertainty


@pytest.mark.parametrize("mean", [-0.0001, -1.0, -3.4e38])
def test_negative_mean_is_rejected_including_the_nodata_sentinel(mean):
    """A negative carbon density is physical nonsense — and the raster nodata
    sentinel (-3.4e38) is exactly the value that must never survive as data.
    Reject at construction; converting nodata to absence is the reader's job,
    BEFORE this type is ever built."""
    with pytest.raises(ValueError):
        CarbonDensity(mean=mean, uncertainty=1.0)


@pytest.mark.parametrize("uncertainty", [-0.0001, -1.0, -3.4e38])
def test_negative_uncertainty_is_rejected(uncertainty):
    """Uncertainty is a magnitude; a negative one is a corrupted input."""
    with pytest.raises(ValueError):
        CarbonDensity(mean=1.0, uncertainty=uncertainty)


@pytest.mark.parametrize(
    ("mean", "uncertainty"),
    [
        (float("nan"), 1.0),
        (1.0, float("nan")),
        (float("inf"), 1.0),
        (1.0, float("inf")),
    ],
)
def test_non_finite_values_are_rejected(mean, uncertainty):
    """NaN and infinity poison every downstream computation silently; a value
    type that admits them is a bare number waiting to happen."""
    with pytest.raises(ValueError):
        CarbonDensity(mean=mean, uncertainty=uncertainty)


@given(
    mean=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    uncertainty=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
)
def test_every_physically_valid_pair_constructs_and_round_trips(mean, uncertainty):
    """Property: the whole non-negative finite domain is accepted, unaltered —
    no clipping, no normalization, no surprises."""
    density = CarbonDensity(mean=mean, uncertainty=uncertainty)

    assert density.mean == mean
    assert density.uncertainty == uncertainty
