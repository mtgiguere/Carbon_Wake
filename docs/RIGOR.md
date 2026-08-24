# Rigor — how this project earns (and audits) its own trust

> Written 2026-08-24, after the first full vertical slice (raw data → PostGIS →
> API → cited CO2 range) went end to end. This is the document for anyone —
> collaborator, reviewer, journalist, skeptical scientist — who wants to know
> not *what* the tool says but *why they should believe how it was built*.
> It includes the failures. Documented failures are rigor evidence; a project
> that reports only its successes is advertising.

## The one-paragraph claim

Every number this tool serves traces to a primary published source or to a
derivation that names itself as one; every load-bearing behavior was specified
in a failing test before the code existed; the honesty rules are enforced by
machines (type constructors, database constraints, HTTP-contract tests), not
by good intentions; and the known flaws are printed on the product, not
footnoted behind it.

## Where everything lives

| Question | Document |
|---|---|
| What are we building, and why these tools? | `PROJECT_SPEC.md` |
| How is it built; what are the layers and rules? | `docs/ARCHITECTURE.md` |
| Why is TDD non-negotiable here? (real bugs, real evidence) | `TDD_CONTRACT.md` |
| Every irreversible decision, with context and consequences | `docs/DECISIONS.md` (ADR-0001…0013) |
| The provenance of every scientific number, flag by flag | `docs/SCIENCE_BASIS.md` |
| What the data spike verified about sources and licenses | `docs/DATA_SPIKE.md` |
| How we'll present this honestly to non-experts (planned) | `docs/SHOWCASE_SPIKE.md` |
| The mechanical gates and how to run them | `CONTRIBUTING.md` |

## The verification discipline

**Quoted vs derived, always.** A figure is either verified against a primary
source on a stated date, or flagged. The reactivity presets carry a
`derivation` field: Hiddink's fractions are labeled *inferred* in the data
model itself, because Hiddink published a factor, not a number. Sala's methods
were verified from the publisher's own PDF — which is how we caught that his
29.7% efficiency already includes resettlement, preventing a silent
double-count of the 0.87 factor.

**Real-format fixtures, committed.** Unit tests with self-authored fixtures
only prove a parser agrees with itself (TDD_CONTRACT.md, Blind spot A). So the
repo carries verbatim samples of the real published inputs — a byte-for-byte
head of a GFW fleet-daily CSV, windowed copies of the real Diesing rasters —
with attribution and provenance READMEs, and integration tests pin them to
ground truth computed *independently of the code under test* (plain dicts and
raw rasterio at fixture-creation time).

**Reality decides parser semantics.** GFW's schema marks every field NULLABLE;
a 385,000-row scan of the real product found zero empty values — so an empty
value is treated as format drift (loud stop), never guessed into a zero.

**Independent recomputation before pinning.** Every "the answer is X" test
value was computed by a separate script path before the pipeline was asked to
reproduce it. This caught a real error: a pinned count of 22 measured "cells
with both gears" when the assertion meant "cells with any dredge record" (33)
— the recount corrected the *test*; the pipeline was right.

## The honesty rules are structural

- **Types:** a `CarbonDensity` cannot exist without its uncertainty; NaN, the
  raster nodata sentinel, and negative masses are impossible to construct.
- **Database:** CHECK constraints refuse half a carbon pair, negative hours,
  and effort rows with no gear; the per-cell total is a GENERATED column that
  cannot disagree with its parts. Tests prove *PostgreSQL* rejects the bad
  rows, not our Python.
- **API:** tests require the word "midwater" in the effort-layer label,
  `null` (never 0) where Sala said "unknown", derivation notes on inferred
  fractions, and the model caveats inside every estimate payload — including
  the currently-known saturation flaw (below).
- **Absence ≠ zero, everywhere:** an unmapped cell is `None`/`NULL`, never a
  0; a recorded zero survives as 0.0; the distinction reaches the schema.
- **Unmapped effort is a first-class result** — counted, stored, served —
  because a map that quietly discards what it cannot color lies by omission.

## The testing discipline, quantified (as of 2026-08-24)

203 tests across seven suites (pure cores, ingest, db, etl, api), all written
RED-first; 100% line+branch coverage held as a *floor, not a verification
claim* (see TDD_CONTRACT.md on why coverage proves execution, not behavior);
Hypothesis property tests on every pure module. Properties have caught real
issues twice: an IEEE-float underflow that falsified a naive "nonzero in,
nonzero out" claim (the test now pins the exact algebraic identity), and the
grid round-trip guarantee that float noise can never split a cell.

Two structural properties deserve mention because they guard shortcuts: the
SQL moment-sum path is property-tested to equal the per-cell model *exactly*,
and CO2 uncertainty flows through the same reactivity-core functions as the
mean, so the pair cannot drift apart.

## The incident log (failures, honestly)

| When | What happened | Root cause | Fix |
|---|---|---|---|
| 2026-08-23 | Full-region ETL hung twice, ~1h lost; first diagnosis wrong (blamed a task timeout) | psycopg `executemany` stalled indefinitely at ~371k rows (server waiting in ClientRead) | Bulk load rewritten as COPY + staged INSERT; loads in seconds; incident recorded in the commit |
| 2026-08-24 | Two local commits landed with a failing test | piping pytest through `tail` masked its exit code | squashed to green before push; exit codes now checked explicitly |
| 2026-08-24 | The stored 2012 run vanished | **db test fixtures truncated the WORKING database between tests — shipped in PR #8, live through five PRs** | tests moved to their own `carbon_atlas_test` database, schema rebuilt fresh each session |
| 2026-08-24 | Foreseeable rework: per-gear effort (PR #12) | first ETL slice aggregated gear-blind even though ADR-0009 said classes would be priced differently | redesigned end to end; lesson: read your own ADRs' consequences forward |

## Current scientific status — read this before citing any number

The **encoding** of the published science is strong (verified sources,
faithful parameter lineage). The **derived layer** has known limitations,
fully listed in SCIENCE_BASIS.md ("Known limitations of the v1 derived
layer"). The one that gates everything:

> **The v1 model has no saturation.** Disturbed carbon is linear in effort;
> real hotspot cells have swept-area ratios in the hundreds, so the same
> sediment is counted many times and totals are overstated — possibly by a
> large factor. Every served estimate discloses this. The bounded model is
> the next scheduled science slice; until it lands and the 2012 run is
> re-reported, all figures are **pipeline-proof, not publication-grade**.

A skeptical climate scientist should also note: the headline is Sala's
assumptions transplanted onto regional data (a composition Sala never
published); midwater trawling contaminates the effort class (ADR-0009,
labeled); the uncertainty band is a stated linear-propagation convention, not
a confidence interval; and 2012 AIS coverage undercounts effort. All of this
is printed on the product.

## What's deliberately NOT here

No new oceanographic science. No point estimates of a disputed quantity. No
CO2 figure without a citation trail. No uncertainty silently dropped, and no
map layer named for something the data cannot support.

## Roadmap discipline

Next, in order: (1) the bounded saturation model — science pass, ADR, rerun,
and an honest "the naive model said 12.5 Mt; the bounded one says X" report;
(2) the showcase/storytelling spike (docs/SHOWCASE_SPIKE.md); (3) the frontend
map. Each is its own set of RED→GREEN cycles, and this document gets updated
when reality contradicts it.
