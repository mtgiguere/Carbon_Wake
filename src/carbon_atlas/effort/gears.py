"""Which GFW gear classes count toward the disturbance layer, and its honest name.

ADR-0009: GFW's public taxonomy does not separate bottom trawlers from midwater
trawlers, and v1 deliberately uses the classes as published rather than
gating the whole project on a registry cross-reference. The price of that
decision is paid here, in the label: the layer says what it actually contains.

This module is the single seam a future registry-refined filter replaces.
"""

#: The GFW gear classes included in the effort layer — the classes whose gear
#: can tow across the seafloor. NOTE: "trawlers" is GFW's whole trawler class,
#: bottom AND midwater; the layer label below must always disclose that.
INCLUDED_GEARTYPES = frozenset({"trawlers", "dredge_fishing"})

#: What every surface (map UI, API, docs) must call this layer. Never "bottom
#: trawling" — that is a claim the underlying gear classes cannot support.
EFFORT_LAYER_LABEL = (
    "All trawlers (bottom and midwater) plus dredgers — GFW gear classes as published"
)


def is_included_gear(geartype: str) -> bool:
    """Whether a GFW ``geartype`` value counts toward the effort layer.

    Matches GFW's class names exactly — a near-miss means the input vocabulary
    changed, and it must fall out of the filter so real-data integration tests
    catch the drift, rather than be fuzzily accommodated.
    """
    return geartype in INCLUDED_GEARTYPES
