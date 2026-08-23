# Architecture — The Project Bible

> If you are picking this project up cold, read this file, then `TDD_CONTRACT.md`,
> then `docs/DECISIONS.md`. Those three tell you *how* we build and *why* the
> choices are what they are. `PROJECT_SPEC.md` tells you *what* we're building.

This document is the durable map of the system. It is updated in the same PR as
any change that alters the shape of the code. A change that makes this document
wrong is an incomplete change.

---

## 1. The one idea that shapes everything

The Trawl Carbon Atlas exists to visualize a **disputed** number honestly. The
central scientific figure — CO2 released from trawling-disturbed seafloor carbon
— is contested in the literature by **one to two orders of magnitude**. The
software's job is not to pick a winner; it is to hold the competing published
estimates side by side and show the range.

That single idea drives the most important architectural decision: the disputed
numbers are produced by a **pure, isolated science core** that can be tested to
exhaustion, and everything else (data ingestion, storage, the API, the map) is a
delivery mechanism layered around it.

---

## 2. Layers

```
                    ┌─────────────────────────────────────────────┐
   the map          │  Frontend — Mapbox GL JS (WebGL)            │  ← visual tests
                    └───────────────▲─────────────────────────────┘
                                    │ JSON (overlay + preset estimates)
                    ┌───────────────┴─────────────────────────────┐
   the API          │  Django + DRF                                │  ← API/contract tests
                    └───────────────▲─────────────────────────────┘
                                    │
                    ┌───────────────┴─────────────────────────────┐
   persistence      │  PostgreSQL + PostGIS (Docker)              │  ← integration tests
                    └───────────────▲─────────────────────────────┘
                                    │
                    ┌───────────────┴─────────────────────────────┐
   ETL              │  GeoPandas/pandas ingest + spatial join      │  ← integration tests
                    └───────────────▲─────────────────────────────┘
                                    │ disturbed-carbon quantities
                    ┌───────────────┴─────────────────────────────┐
   SCIENCE CORE     │  carbon_atlas.reactivity  (PURE)            │  ← unit + property tests
                    │  named presets → CO2 estimate → range        │     (the most-tested code)
                    └─────────────────────────────────────────────┘
```

**The dependency arrow only points down.** The science core knows nothing about
databases, HTTP, GeoPandas, or Mapbox. You can compute every CO2 estimate in the
project with nothing installed but the standard library. This is what makes the
scientifically-load-bearing code trivially testable and safe to extend.

---

## 3. The pure-core rule (non-negotiable)

The pure packages — `carbon_atlas.reactivity` (the disputed science),
`carbon_atlas.effort` (the 0.01° grid model and effort aggregation), and
`carbon_atlas.carbon` (carbon quantities that never travel without their
uncertainty) — must never import:

- a web framework (Django, DRF, FastAPI),
- a database driver (psycopg, sqlalchemy),
- a geospatial or heavy-numeric I/O lib (geopandas, rasterio, netCDF) —
  plain numeric types are fine; *file/format* handling is not.

If a computation feels like it needs one of those, the computation is in the wrong
layer: pull the pure part down into the core and leave the I/O in the layer above.

**Why:** the addenda in `TDD_CONTRACT.md` prove, with real bugs, that unit tests
are airtight on pure Python and blind at every I/O boundary. So we make the code
that *must* be correct (the disputed science) live entirely on the airtight side.

---

## 4. Dependencies arrive with their module

`pyproject.toml` starts with an **empty** runtime dependency list. We add a
dependency in the same PR as the first module that imports it, never speculatively.

Consequences:
- A fresh checkout at any point installs only what the code present actually uses.
- "What does this project depend on?" is answered by reading `pyproject.toml`, and
  the answer is always true.
- The science core stays provably dependency-free, because nothing forces a heavy
  import into its install footprint.

---

## 5. The blind spots — standing requirements, not afterthoughts

`TDD_CONTRACT.md` documents, from a previous project, exactly where green test
suites lie. This project lives disproportionately in those zones (it is mostly
external data + a WebGL map), so their remedies are **requirements from day one**,
not lessons to relearn:

- **Blind spot A — external formats.** Any code that parses a download, an API
  response, or a file schema gets an `@pytest.mark.integration` test against one
  real, small, committed sample under `tests/fixtures/real/`. A self-authored
  fixture only proves the parser agrees with itself.
- **Blind spot B — rendering.** DOM assertions ("the button exists", "the legend
  toggles") are not visual verification. A map layer gets a software-WebGL
  (SwiftShader) pixel smoke test, or at minimum a human eyeballs a screenshot,
  before it is called "working".
- **Blind spot C — threshold guards.** A pixel-diff or numeric-threshold guard is
  untrustworthy until the real signal and the noise floor are both *measured* and
  the threshold is shown to sit provably between them. "It passed" is not a
  measurement.

Periodic (not CI-gated) **mutation audits** on correctness-critical pure code
(the reactivity core, any validation) are how we hunt for hollow tests. Tooling
caveats for Windows are in `TDD_CONTRACT.md`.

---

## 6. Testing layout

```
tests/
  reactivity/            unit + Hypothesis property tests for the pure science core
  effort/                unit + property tests for the grid/aggregation pure core
  carbon/                unit + property tests for the carbon-quantity pure core
  ingest/                parser contract tests + @integration tests on real samples
  fixtures/
    real/                small, committed, redistributable real-format samples
      gfw/               verbatim head of a real GFW fleet-daily CSV (see its README)
      diesing2021/       windowed copies of the real OC-density raster pair (README)
```

Default `pytest` run excludes nothing by marker yet; as `integration`/`visual`
suites grow, the fast unit run is `pytest -m "not integration and not visual"`.

---

## 7. Build order (mirrors PROJECT_SPEC "suggested build order")

1. Reactivity presets (pure core) — done. The science, provable, first.
2. Data-exploration spike — done (docs/DATA_SPIKE.md, ADR-0008): sources are
   GFW fleet-daily v3 bulk CSVs + Diesing 2021 GeoTIFFs, North Sea first.
3. **ETL + PostGIS schema** ← we are here. One region's trawling + one carbon
   dataset, spatially joined, overlap query proven. So far: the pure effort
   grid/aggregation core, the streaming GFW fleet-daily parser (stdlib csv —
   no pandas needed to ingest effort), the pure carbon-density type
   (mean + uncertainty inseparable), and the Diesing paired-raster reader
   (rasterio; nodata means absence, corrupt pairing fails loudly). Next: the
   effort↔carbon join, then PostGIS.
4. Django + DRF API serving overlay + preset-driven estimates.
5. Django admin curation for sources/citations/confidence tiers.
6. Frontend map: static overlay, then the preset toggle and uncertainty display.
7. Docker Compose deployment, self-hosted end to end.
8. (Later) Keycloak + contributor accounts.

Each step is its own set of RED→GREEN cycles. We do not start a step until the
one below it is green and documented.
