# Trawl Carbon Atlas

A public, interactive tool mapping the overlap between industrial bottom-trawling
grounds and seafloor organic-carbon deposition zones — visualizing a **live,
disputed scientific question** rather than presenting a single settled number.

See [`PROJECT_SPEC.md`](PROJECT_SPEC.md) for the full vision,
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how it's built, and
[`docs/RIGOR.md`](docs/RIGOR.md) for how the project earns — and audits — its
own trust (verification discipline, structural honesty rules, the incident
log, and the current scientific status including known flaws).

## Project principles (read before contributing)

This project optimizes for one thing above features: **a codebase someone can pick
up cold in two years and extend without fear.** In priority order:

1. **Strict TDD.** Every function is written test-first, RED before GREEN. The
   discipline, and the real bugs that earned it, are in [`TDD_CONTRACT.md`](TDD_CONTRACT.md).
   This is not negotiable and not decorative.
2. **A pure science core, isolated from I/O.** The disputed CO2 numbers are
   computed by pure functions with no database, network, or framework anywhere
   near them. They are the most-tested code in the repo.
3. **Documentation as a first-class artifact.** Architecture, decisions, and the
   *why* behind them are written down as we go — see `docs/`.
4. **Honesty about uncertainty.** The tool shows the competing published
   estimates and their range. It never launders a disputed figure into a
   confident one.

## Status (2026-08-24)

The full data spine is working end to end for the v1 region (North Sea):
a year of real Global Fishing Watch effort joins real Diesing 2021 seafloor
carbon in PostGIS, and a read-only API serves the overlap plus the disputed
CO2 estimate as a **cited, attributed range with uncertainty** — for 2012,
spanning the published 1000× disagreement (Hiddink to Sala), with the model's
caveats embedded in every payload.

**Scientific status:** the retrospective's saturation flaw is fixed
(ADR-0014: Poisson footprint bound; the naive model had overstated 2012
disturbed carbon 3.41×). Remaining limitations — fleet-average gear widths,
midwater contamination of the GFW trawler class, uncertainty as a stated
propagation convention rather than a CI, thin 2012 AIS coverage — are listed
in `docs/SCIENCE_BASIS.md` ("Known limitations") and served inside every
estimate payload. See `docs/RIGOR.md` before citing any number.

Next: the storytelling spike (`docs/SHOWCASE_SPIKE.md`), then the frontend map.

## Getting started (dev)

```sh
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[dev]"   # Windows
# source .venv/bin/activate  &&  pip install -e ".[dev]" # POSIX
pytest
```

Dependencies are added **only when the module that needs them is built** — so a
fresh checkout at this stage installs just the test toolchain. See
`docs/ARCHITECTURE.md` for why.
