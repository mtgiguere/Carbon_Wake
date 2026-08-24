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

---

## 2026-08-23 — ADR-0009: v1 shows GFW gear classes as-is, honestly labeled

**Context.** ADR-0008 consequence (b): GFW's public taxonomy lumps bottom and
midwater trawlers into one "trawlers" class. The literature's remedy (the
Sala/Pristine Seas lineage) cross-references GFW vessels against official fleet
registries to strip out midwater/pelagic trawlers — more defensible, but a
substantial workstream (registry acquisition, vessel matching) that would sit
in front of any overlap existing at all.

**Decision** (project owner, 2026-08-23). v1 uses GFW `trawlers` +
`dredge_fishing` effort **as published**, and every surface that shows the
layer (map UI, API responses, docs) must label it as *"all trawlers (bottom
and midwater) plus dredgers"* — never as "bottom trawling". The registry
cross-reference remains on the roadmap as a swap-in refinement with its own
future ADR; the gear filter is kept a single, replaceable seam in the code so
that swap stays cheap.

**Consequences.** (a) The overlap ships sooner and the honest-labeling burden
moves into the UI/API contract, which fits the project's ethos — the whole tool
is an exercise in labeling uncertainty. (b) v1's effort layer *overstates*
bottom-contact effort wherever midwater trawling is common; the label carries
that caveat. (c) The set of included gear classes is a named constant in one
place, so the future registry-refined filter replaces one seam, not a scatter
of string literals.

---

## 2026-08-23 — ADR-0010: ETL-owned PostGIS schema is raw SQL + psycopg, honesty rules as constraints

**Context.** Step 3 needs the overlap persisted. Django arrives at step 4 and
brings its own migration machinery — but only for the tables it owns (curation:
sources, citations, confidence tiers). Letting a future framework own the ETL's
tables now would invert the dependency arrows (ARCHITECTURE §2) and stall step
3 on step 4's stack.

**Decision.**

1. The ETL-owned tables (`etl_run`, `overlap_cell`) are defined in a plain,
   idempotent `schema.sql` applied by `carbon_atlas.db` via **psycopg 3** (the
   dependency arrives with this module, ADR-0004). Django will own only its
   curation tables; if it needs the ETL tables it maps them unmanaged.
2. The project's honesty rules are enforced **in the database as CHECK
   constraints**, not only in Python: fishing hours non-negative, carbon
   mean/uncertainty non-negative and — the never-half-a-pair rule —
   `(mean IS NULL) = (uncertainty IS NULL)`. A mapped cell has the full pair;
   an unmapped cell has neither; nothing else can exist in the table.
3. One table holds both sides of the join (`oc_density_* IS NULL` = unmapped),
   so unmapped effort is stored with the same fidelity as mapped effort —
   reported, never dropped, all the way into persistence.
4. Every `etl_run` row records provenance: sources, the ADR-0009 effort-layer
   label verbatim, and both sides' cell/hour totals.
5. Cell geometry is stored as `geometry(Polygon, 4326)` with a GiST index,
   built in SQL from the integer cell indices — the WGS84 0.01° grid is the
   storage geometry; projection to LAEA or web-mercator is a query/tile-time
   concern.

**Consequences.** (a) A corrupt half-pair cannot be inserted even by a buggy
future writer — the schema is the last line of the honesty defense and is
integration-tested directly. (b) Two schema-management regimes will coexist
once Django lands (SQL for ETL tables, migrations for curation tables); the
boundary is "who writes the table". (c) The dev stack gains docker-compose.yml
(PostGIS on host port 5434 — 5432/5433 are taken on the dev machine).

---

## 2026-08-24 — ADR-0011: The v1 API is a thin, read-only DRF layer over the tested store

**Context.** Step 4 (Django + DRF). The temptation at this layer is to grow a
parallel data-access stack: ORM models for the ETL tables, GeoDjango for the
geometry, and computed CO2 figures in every response.

**Decision.**

1. **Views call the store, not an ORM.** DRF views obtain Django's underlying
   psycopg connection (`django.db.connection.connection` — Django's postgres
   backend is psycopg 3) and call the already-tested `carbon_atlas.db.store`
   functions. No Django models exist for the ETL tables; ORM models arrive
   only with the curation tables they own (step 5, per ADR-0010).
2. **No GeoDjango.** `django.contrib.gis` would drag GDAL/GEOS system
   libraries into every install (a swamp on Windows) to do what the store's
   PostGIS SQL already does, where it is integration-tested. Cell polygons in
   API responses are built from the integer cell indices in Python.
3. **Read-only v1.** GET endpoints only: the preset catalog, run provenance,
   and bbox-scoped trawled cells. Auth arrives with contributor features
   (PROJECT_SPEC step 8), not before.
4. **No CO2 numbers over the wire — yet.** The reactivity presets convert
   *disturbed carbon mass* to CO2, and no citable disturbed-carbon model
   (gear penetration depth, swept-volume ratio) is encoded yet. Until that
   model exists with SCIENCE_BASIS provenance and its own ADR, the API serves
   the presets' fractions, citations, and derivation notes — never a CO2
   figure it cannot source. Serving one anyway would be inventing science in
   the serializer.
5. Django settings read the same `CARBON_ATLAS_DB_URL` DSN as everything else
   (parsed with `psycopg.conninfo`, no extra dependency); `pytest-django`
   joins the dev toolchain and API tests run against a schema.sql-initialized
   test database on the same PostGIS server.

**Consequences.** (a) The API layer contains no query logic of its own to get
wrong — its tests are about HTTP contracts (shapes, errors, honesty labels),
not re-proofs of SQL. (b) When the disturbed-carbon model lands, estimate
endpoints get added alongside it, citations first. (c) GeoDjango can still be
adopted later by its own ADR if tile serving demands it.

---

## 2026-08-24 — ADR-0012: The v1 disturbed-carbon model — Sala's chain, honestly downscaled

**Context.** The reactivity presets convert *disturbed carbon mass* to CO2;
nothing computed that mass. Sala 2021's methods (now verified from the
publisher PDF — see SCIENCE_BASIS.md "The disturbed-carbon model") define the
chain: AIS effort → swept area (distance × gear width) → swept volume
(× penetration depth) → disturbed carbon (× carbon stock).

**Decision.** `carbon_atlas.disturbance` (pure) encodes
`hours × speed × width × penetration_depth × OC_density` per cell, with every
parameter travelling in a `GearProfile` that carries its provenance, and the
mass inheriting the carbon density's per-pixel uncertainty exactly. The
default profiles, one per ADR-0009 gear class:

| | trawlers (as otter trawls) | dredge_fishing (as towed dredges) |
|---|---|---|
| width | **77.28 m** | **26.02 m** |
| speed | 3.0 kn | 2.25 kn |
| penetration | 2.44 cm | 5.47 cm |

Width computation: Sala's own Eigaard 2016 relationships
(`W = 10.6608·KW^0.2921` for otter trawls, `W = 0.3142·LOA^1.2454` for
dredges) evaluated **per vessel** in GFW's `fishing-vessels-v3.csv` (year
2012: 5,654 trawlers with engine power, 105 dredgers with length), then
**weighted by each vessel's fishing hours** — the width that represents an
hour of effort, avoiding the Jensen error of plugging an average vessel into
a nonlinear formula. Speeds are the midpoints of Sala's per-gear plausibility
ranges (otter 2–4 kn, dredges 2–2.5 kn); penetration depths are Hiddink
2017's means as quoted verbatim by Sala 2021 and Atwood 2024.

Deviations from Sala, each recorded in SCIENCE_BASIS.md: fleet-average width
instead of per-vessel (fleet-daily effort has no vessel identities); GFW
"trawlers" treated as otter trawls (Sala's own default for unclassified
vessels — with ADR-0009's midwater caveat attached to every derived figure);
regional surficial OC density instead of a global first-meter stock (gear
penetrates 2–6 cm, within the surficial layer, so the disturbed volume is
priced at the density of the sediment actually penetrated); and uncertainty
propagated from the carbon layer only (gear-parameter spread is real but
unquantified in v1 — stated, not ignored).

**Consequences.** (a) The chain to CO2 is now closable with zero new science:
`disturbed_mass × preset.remineralization_fraction × 44/12` — Sala's 29.7% is
verified to be the mean pixel-level efficiency of *disturbed* carbon
(resettlement included), so no extra 0.87 factor may be applied on top.
(b) **Blocking gap for the wiring slice:** the ETL currently SUMS trawler and
dredge hours into one per-cell total (ADR-0009's seam feeds aggregation), but
this model prices the two classes differently — per-gear aggregation and
storage must land before any cell-level CO2 estimate is computed. (c) The
2012-weighted widths are period-appropriate for the stored 2012 run; a run
over another year should recompute them from that year's vessel table (the
computation is one documented script pass).
