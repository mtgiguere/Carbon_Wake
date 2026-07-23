# Trawl Carbon Atlas

A public, interactive tool mapping the overlap between industrial bottom-trawling
grounds and seafloor organic-carbon deposition zones — visualizing a **live,
disputed scientific question** rather than presenting a single settled number.

See [`PROJECT_SPEC.md`](PROJECT_SPEC.md) for the full vision and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how it's built.

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

## Status

Bootstrapping. First vertical slice: the reactivity-preset CO2 calculation core
(pure math), built strict-TDD. Region-first scope (North Sea) for v1.

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
