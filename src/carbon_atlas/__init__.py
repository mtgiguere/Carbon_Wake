"""Trawl Carbon Atlas.

A public, honest visualization layer over the *disputed* science of how much CO2
bottom trawling releases from seafloor sedimentary organic carbon.

Package boundaries (enforced by discipline, documented in docs/ARCHITECTURE.md):

- ``carbon_atlas.reactivity`` — the pure science core. No I/O, no framework, no
  geospatial libs. Given quantities and a named published assumption, it computes
  a CO2 estimate. This is the most-tested code in the project by design.

Modules with I/O (ETL, persistence, the Django/DRF API, the map) are layered
*around* this core and are covered by integration/visual tests, never by unit
tests alone — see the "blind spots" section of the architecture doc.
"""

__version__ = "0.0.1"
