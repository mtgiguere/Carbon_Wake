"""Behavioral contract for the gear-inclusion seam.

ADR-0009: v1 uses GFW's gear classes as published — "trawlers" (which lumps
bottom and midwater together) plus "dredge_fishing" — and every surface showing
the layer must label it honestly, never as "bottom trawling". These tests pin
both halves: WHICH classes are in, and that the label DISCLOSES the lumping.
The inclusion set is one named constant so the future registry-refined filter
(its own ADR) replaces one seam, not a scatter of string literals.

Written test-first per TDD_CONTRACT.md.
"""

import pytest

from carbon_atlas.effort.gears import (
    EFFORT_LAYER_LABEL,
    INCLUDED_GEARTYPES,
    is_included_gear,
)


@pytest.mark.parametrize("geartype", ["trawlers", "dredge_fishing"])
def test_gfw_towed_bottom_contact_classes_are_included(geartype):
    """The two GFW classes with (possible) towed bottom contact are in: all
    trawlers, and dredgers."""
    assert is_included_gear(geartype)


@pytest.mark.parametrize(
    "geartype",
    ["drifting_longlines", "purse_seines", "fixed_gear", "fishing", "squid_jigger"],
)
def test_non_towed_gfw_classes_are_excluded(geartype):
    """Gear that does not tow across the seafloor contributes nothing to the
    disturbance layer — including GFW's unsure catch-all class 'fishing'."""
    assert not is_included_gear(geartype)


def test_gear_names_are_matched_exactly_not_fuzzily():
    """'Trawlers' with a capital T is NOT a GFW class. A near-miss means the
    input vocabulary changed — it must fall out of the filter, not be
    accommodated, so the integration test against real data catches the drift."""
    assert not is_included_gear("Trawlers")
    assert not is_included_gear("trawlers ")


def test_the_layer_label_discloses_what_is_actually_included():
    """ADR-0009's honest-labeling half, pinned at the data level: the label
    shown for this layer must disclose that midwater trawlers are included and
    must never present the layer as plain 'bottom trawling'."""
    label = EFFORT_LAYER_LABEL.lower()

    assert "midwater" in label
    assert "dredge" in label
    assert "bottom trawling" not in label


def test_the_inclusion_set_is_exactly_the_two_decided_classes():
    """ADR-0009 names exactly two classes. A third sneaking in (or one dropped)
    is a decision change, which requires a new ADR — so the set itself is
    pinned, not just membership probes."""
    assert INCLUDED_GEARTYPES == frozenset({"trawlers", "dredge_fishing"})
