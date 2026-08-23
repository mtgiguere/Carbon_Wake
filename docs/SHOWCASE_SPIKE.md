# Showcase / Storytelling Spike — PLANNED, NOT STARTED

> Status: **placeholder**. Captured 2026-08-23 from a project-owner discussion so
> the idea survives until its slot in the build order. No design or code work
> has been done. When the spike runs, its findings replace this note (same
> discipline as DATA_SPIKE.md).

## Why this spike exists

The spec covers the *functional* frontend (map, layer toggles, preset switcher,
uncertainty display) but says nothing about how a non-expert — a journalist, a
policy reader, or anyone landing on the repo — comes to *care* within 30
seconds. That is its own design problem, distinct from building the map, and it
deserves deliberate work rather than whatever falls out of the frontend step.

## The two problems (do not conflate them)

1. **The in-tool experience** — making the interactive map compelling and
   legible to someone who isn't a domain expert. Likely shape: a guided "story
   mode" (camera choreography: here's the fleet → here's the buried carbon →
   here's the overlap → here's the disputed cost as a cited range) that ends in
   a free-explore sandbox. Story first, sandbox second — the proven pattern in
   NYT/Guardian scrollytelling and pudding.cool-style visual essays.
2. **The front door** — repo README hero (animated GIF/screenshot), one-line
   pitch, and a link to a live deployment. Most visitors (including most
   coders) will never read the code; the front door is what they judge.

## The guiding principle: animate the truth

The owner's instinct — a Google-Earth-like map with boats, shoals of fish,
currents, atmosphere — collides head-on with this project's identity
(never-a-bare-number, quoted-vs-derived, ADR-0009 honest labeling) **if** the
moving elements are invented. Faux fish and faux currents would read as
advocacy styling to exactly the audiences the spec targets.

But no faux data is needed: **the real data is already animated.** GFW effort
is daily, 2012–2024 — those are real vessels, and a year of trawling intensity
flowing across the North Sea is genuinely mesmerizing (GFW's own live map
proves it). Candidate honest animations:

- vessel-density / effort flow over time (real daily data);
- trawl-scar trails that fade on a real time axis;
- carbon "plumes" whose size is driven by the actual preset math, labeled with
  the actual citation, and shown as a range, never a point.

Rule to adopt when the spike runs: **the honesty layer extends to visuals** —
anything illustrative is labeled illustrative, exactly as derived preset
fractions carry derivation notes.

## The dispute IS the hook

Most people have never seen a tool that says "scientists disagree about this
number by up to 1000x — drag between their assumptions and watch the map
change." That interaction is the showcase, not a caveat to hide. Lean into it.

## Timing

Run this spike **after the overlap query is proven on real joined data and
before any frontend code** (build-order step 6 boundary). Storyboarding against
real data beats speculating, and Blind spot B (TDD_CONTRACT.md) says visual
work needs concrete targets before building.

## Deliverables when the spike runs

- Audience definition (who exactly is the 30-second visitor?).
- A narrative storyboard for story mode.
- A **visual-honesty policy**: what may be animated, what must be labeled
  illustrative, what is banned.
- The repo front-door plan (README hero, live-demo link, pitch line).
- Tech feasibility notes: Mapbox GL camera choreography, animation layers
  (e.g. deck.gl), performance on real cell counts.
- Attribution check: GFW "Powered by" + CC BY-NC and Diesing CC-BY attribution
  must appear in any showcase material, and the effort layer keeps its
  ADR-0009 label everywhere — including marketing surfaces.
