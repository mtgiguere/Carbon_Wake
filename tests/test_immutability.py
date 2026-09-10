"""Every quantity in the pure science core is immutable — one invariant, one test.

The mutation audit of 2026-09-10 found `frozen=True` -> `False` surviving in
every module: nothing had ever tried to mutate a quantity. Immutability is a
design rule here (a CarbonDensity, a DisturbedCarbon, a preset cannot be
edited after construction, so no caller can quietly change a served number),
so it is asserted once, for every dataclass the pure core defines, rather than
left to per-module mutation scores.

Written test-first per TDD_CONTRACT.md.
"""

import dataclasses
import inspect

import pytest

from carbon_atlas import anchors, disturbance, estimates, footprint, overlap, zones
from carbon_atlas.carbon import density
from carbon_atlas.effort import aggregate, grid
from carbon_atlas.reactivity import presets

_PURE_CORE = (
    presets,
    disturbance,
    estimates,
    footprint,
    anchors,
    zones,
    grid,
    aggregate,
    density,
    overlap,
)


def _core_dataclasses():
    for module in _PURE_CORE:
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == module.__name__ and dataclasses.is_dataclass(obj):
                yield pytest.param(obj, id=f"{module.__name__.split('.')[-1]}.{name}")


def test_the_pure_core_defines_dataclasses_at_all():
    """Guard against the parametrization silently collapsing to nothing."""
    assert len(list(_core_dataclasses())) >= 15


@pytest.mark.parametrize("cls", list(_core_dataclasses()))
def test_every_pure_core_dataclass_is_frozen(cls):
    assert cls.__dataclass_params__.frozen is True, f"{cls.__name__} must be frozen"
