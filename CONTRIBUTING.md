# Contributing

Read [`TDD_CONTRACT.md`](TDD_CONTRACT.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
first. This file covers the mechanical gates; those two cover the discipline.

## Setup

```sh
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[dev]"   # Windows
# source .venv/bin/activate && pip install -e ".[dev]"  # POSIX
```

## The gates

CI runs four gates on every push and PR (`.github/workflows/ci.yml`). They are
reproducible locally with the identical tools — run them before you push and CI
holds no surprises:

| Gate | Local command | What it enforces |
|------|---------------|------------------|
| Lint | `ruff check .` | style, imports, common bug patterns |
| Format | `ruff format --check .` | one canonical formatting (use `ruff format .` to fix) |
| Tests + coverage | `pytest --cov=carbon_atlas --cov-report=term-missing` | all tests pass; coverage ≥ 100% floor |
| Dep vulns | `pip-audit` | no known CVEs in installed dependencies |
| Source vulns | `bandit -r src -q` | no flagged insecure patterns in our code |

One-liner for all of them (POSIX/Git-Bash):

```sh
ruff check . && ruff format --check . && \
  pytest --cov=carbon_atlas --cov-report=term-missing && \
  pip-audit && bandit -r src -q
```

### On the coverage floor

100% is a **floor meaning "no line ships untested," not a verification target.**
Coverage counts executed lines, not verified behaviors (see `TDD_CONTRACT.md`).
Under strict TDD every line is born from a failing test, so 100% is the honest
number. For genuinely unreachable defensive code, annotate the line with
`# pragma: no cover` and a one-line reason — never write a hollow test just to
colour a line green. If the floor ever needs to move, that's a decision recorded
in `docs/DECISIONS.md`, not a silent edit.

## Windows quirk: PostgreSQL's PROJ_LIB breaks rasterio

The PostgreSQL/PostGIS installer sets a system-wide `PROJ_LIB` pointing at its
own (older-layout) `proj.db`, which makes every rasterio CRS operation fail
with `DATABASE.LAYOUT.VERSION.MINOR ... It comes from another PROJ
installation`. rasterio ships a current proj.db of its own and finds it when
the variable is absent — so unset it for any test or ETL run:

```sh
unset PROJ_LIB              # Git Bash
$env:PROJ_LIB = $null       # PowerShell
```

CI is unaffected (no PostgreSQL on the runners).

## The loop (every change)

1. Write one test describing the behavior you want. Run it. **Confirm it fails
   (RED)** for the right reason.
2. Write the minimum code to pass. Run it. **Confirm GREEN.**
3. Refactor if needed; keep it green.
4. Run the gates. Commit with a message describing the *behavior* added.
