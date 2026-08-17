# Decision Log (ADRs)

Lightweight architecture decision records. Newest at the bottom. Each entry is
immutable once written; if we change our mind, we add a new record that supersedes
the old one rather than editing history. This is the "why did they do it this way"
file that saves a future maintainer a week.

Format: **Date — Title** / Context / Decision / Consequences.

---

## 2026-07-20 — ADR-0001: Strict TDD is the working discipline

**Context.** A prior project (documented in `TDD_CONTRACT.md`) ran with
Test-After-Development and accumulated a specific, catalogued set of bugs that all
shared one root cause: tests that confirmed the code just written instead of
specifying the behavior required.

**Decision.** This project runs strict TDD: one test → confirm RED → minimum code
→ confirm GREEN → refactor → commit. No production function is written before a
failing test specifies its behavior. `TDD_CONTRACT.md` is binding, including its
red-flag list (no hollow guards, no `is True`/`is False` on numpy, no
seed-specific assertions, no mechanism-named tests).

**Consequences.** Slower first draft of each function; far cheaper change later.
Coverage is reported but never treated as evidence of verification.

---

## 2026-07-20 — ADR-0002: A pure science core, isolated from all I/O

**Context.** The contract's own addenda prove unit tests are airtight on pure
Python and blind at every I/O boundary. The scientifically load-bearing part of
this project (the disputed CO2 estimate) is small and pure; the rest is I/O.

**Decision.** `carbon_atlas.reactivity` computes every disputed number as pure
functions with no framework, DB, or geospatial import. I/O layers sit above it and
depend downward only. See `docs/ARCHITECTURE.md` §3.

**Consequences.** The must-be-correct code lives entirely on the testable side.
Some glue code is needed to move data from the I/O layers into pure quantities;
that glue is where integration tests focus.

---

## 2026-07-20 — ADR-0003: Region-first scope (North Sea) for v1

**Context.** `PROJECT_SPEC.md` open question: global vs. one well-documented
region. Global is more impressive; regional sedimentary-organic-carbon data is far
better validated and more likely redistributable.

**Decision.** v1 targets one well-studied region (North Sea leading candidate).
The overlap/ETL contract is proven on one region before any global expansion.
Global remains an explicit later goal, not a v1 requirement.

**Consequences.** Smaller, more defensible first dataset; the contract-required
integration test against real external data (Blind spot A) is tractable early.

---

## 2026-07-20 — ADR-0004: Dependencies arrive with their module

**Context.** Speculative dependency lists rot and make "what does this need?"
unanswerable.

**Decision.** `pyproject.toml` runtime dependencies start empty; each is added in
the same PR as the first module importing it. See `docs/ARCHITECTURE.md` §4.

**Consequences.** The first vertical slice (pure reactivity math) installs only the
test toolchain. GeoPandas/Django/DRF/psycopg enter later, each with its layer.

---

## 2026-07-20 — ADR-0005: First vertical slice is the reactivity math, not the ETL

**Context.** Tempting to start with data ingestion. But ingestion sits in the I/O
blind-spot zone, while the reactivity math is the pure, deterministic heart the
whole project exists to get right.

**Decision.** The first RED test targets the reactivity-preset CO2 calculation.
Prove the science core before touching Global Fishing Watch or PostGIS.

**Consequences.** Early tests are fast, deterministic, Hypothesis-friendly, and
independent of any external data situation being resolved first.

---

## 2026-07-22 — ADR-0006: CI quality gates from the first commit

**Context.** Gates added after code exists tend to be retrofitted around whatever
already fails. Adding them before the first commit means the very first commit is
already green, and the bar only ever moves up.

**Decision.** GitHub Actions (`.github/workflows/ci.yml`) runs four gates on every
push and PR, each reproducible locally via the `dev` extra (see `CONTRIBUTING.md`):
lint (`ruff check`), format (`ruff format --check`), tests + a 100% coverage floor
(`pytest --cov`), and vulnerability scanning of both dependencies (`pip-audit`) and
our own source (`bandit`). Tooling choice was left open; these are standard,
zero-config, and installable as plain dev dependencies.

**Consequences.** The coverage floor is a floor, not a verification proxy (see
ADR-0001 and `TDD_CONTRACT.md`); `# pragma: no cover` with a reason is the escape
hatch for unreachable defensive code. `pip-audit` can fail the build on a CVE in a
*dependency we don't control* — that is the intended behavior of a vuln gate and
forces a conscious pin/upgrade rather than silent exposure. As Django/PostGIS
arrive, coverage `omit` patterns (settings, migrations, wsgi/asgi) will be added
here as their own recorded decision.

---

## 2026-08-14 — ADR-0007: Markdown is excluded from ruff

**Context.** ruff ≥ 0.16 formats fenced Python code blocks inside `.md` files by
default. CI (which installs latest ruff per ADR-0004's no-speculative-pins spirit)
started failing `ruff format --check` on `TDD_CONTRACT.md` — a document whose code
snippets are *verbatim historical specimens* of real past bugs (one is literally
about comment spacing). Docs also carry deliberately abbreviated pseudo-code that
is illustrative, not executable.

**Decision.** `exclude = ["*.md"]` in `[tool.ruff]`. Ruff lints and formats
Python source; it does not touch documentation. We keep `ruff>=0.5` unpinned —
tracking the latest formatter on real source is desirable; rewriting quoted
history is not.

**Consequences.** Code blocks in docs are never auto-formatted, so their style
may drift from the source style — acceptable, since their job is fidelity to what
was written (or readable abbreviation), not conformance. If a future doc wants
enforced formatting, it can be carved back in as its own decision.

---

## 2026-08-14 — ADR-0008: v1 data sources — Diesing 2021 + GFW bulk v3

**Context.** The PROJECT_SPEC step-1 data spike (docs/DATA_SPIKE.md) verified
access, formats, and licenses for trawling-effort and sediment-carbon data.

**Decision.** v1 (North Sea, per ADR-0003) builds on:

1. **Carbon:** Diesing 2021, PANGAEA 10.1594/PANGAEA.928272 — 500 m GeoTIFFs of
   OC density and OC accumulation rate **with per-pixel uncertainty**, full
   North Sea + Skagerrak, CC-BY-4.0, ~53 MB anonymous download.
2. **Effort:** GFW Apparent Fishing Effort **v3 bulk files** (Zenodo
   10.5281/zenodo.14982712), fleet-daily 0.01° by flag + gear type, 2012–2024,
   CC BY-NC 4.0. The ETL takes the static files, not the API — no token, no
   rate limits, reproducible inputs. The v3 API (token required) is deferred to
   future interactive/tile features.

**Consequences.** (a) The atlas is **non-commercial** while it carries
GFW-derived layers (CC BY-NC 4.0), and must carry an attribution stack (GFW +
Diesing + per-preset citations) passed on to downstream users. (b) GFW's public
gear class is "trawlers, all types" — bottom vs. midwater is NOT distinguished;
whichever isolation strategy the ETL adopts (as-is + honest labeling vs.
registry cross-reference) is its own future ADR, and the UI must state what the
layer actually shows. (c) Per-pixel carbon uncertainty is available from day
one, so the never-a-bare-number rule extends to the map layer itself.
