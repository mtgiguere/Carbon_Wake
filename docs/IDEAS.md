# Idea backlog — captured, not committed

> Options, not obligations (owner's rule, 2026-08-27): an idea recorded here
> has earned nothing but survival. Each entry carries its value, its honest
> cost, and its risks, so a future session can pick one up cold — or
> deliberately never. Bigger, maturer spikes live in their own docs
> (SHOWCASE_SPIKE.md, VALIDATION_SPIKE.md); this file is the wider net.

## 1. "Draw your own area" — the personal query

Drag a box (or pick a named area) and get the disputed number for THAT patch:
hours, disturbed carbon, the Sala↔Hiddink range, caveats attached. Turns the
visitor from spectator into investigator — a journalist interrogates their
coastline, a policy reader their proposed closure.

- **Cost: days.** The PostGIS bbox machinery exists (`trawled_cells_intersecting`,
  the estimate chain); this is one region-scoped estimate endpoint plus a map
  draw interaction.
- **Honesty:** a hypothetical closure DISPLACES effort rather than deleting
  it — the response must say so; and small boxes have wide relative
  uncertainty (few cells).
- Best-candidate next interactive slice; it is the storyboard's "explore
  yourself" beat, made personal.

## 2. Cumulative footprint — one defensible headline number

After the 2013–2023 backfill: union the Poisson footprints across all years
and answer *"what fraction of the North Sea seabed has been trawled at least
once since 2012?"* — Amoroso-style, using machinery we already have
(1 − e^(−SAR), extended across summed years).

- **Cost: small, but gated on the backfill** (12 more downloads + runs).
- **Honesty advantage:** it is a *coverage* claim (physics both camps accept),
  not a CO₂ claim (the disputed part) — a headline that needs no preset.
- Watch: cross-year union must handle AIS coverage growth (early years
  under-detect; the footprint is a lower bound and must say so).

## 3. "Accidental sanctuaries" — the wind-farm layer

Offshore wind farms are de facto trawl-exclusion zones; EMODnet publishes
their footprints openly. Overlaid on 2024 effort they should appear as
visible holes — an instantly legible story ("industry accidentally built
marine reserves") that doubles as the reference-zone layer
VALIDATION_SPIKE.md slice 1 wants anyway.

- **Cost: small** (one open-data polygon layer + styling).
- **Honesty:** verify the exclusion actually holds in our effort data before
  narrating it (some farms permit some fishing); label farm commissioning
  dates — a hole is only meaningful after the farm existed.

## 4. The carbon cost of dinner

Join ICES landings statistics (open, by statistical rectangle) to our
per-area CO₂ ranges: *"the carbon range per kg of North Sea sole — somewhere
between negligible and worse than beef, depending on whose science you
trust."* The strongest public-resonance idea on this list; food is how
people connect to the sea.

- **Cost: a real spike** — new data source, rectangle↔cell reconciliation,
  and an allocation model (area emissions → species landings) that needs its
  own SCIENCE_BASIS pass and ADR before any number ships. The seafood-
  footprint literature (e.g. Parker & Tyedmers lineage) is the anchor to
  verify against.
- **Risk:** allocation choices can smuggle in advocacy either direction;
  this one is honesty-hard, which is exactly why it must not be improvised.

## 5. "Happening now" — the live layer

GFW's realtime API (free token — deferred since ADR-0008) showing trawlers
working over carbon hotspots as the visitor watches. Present tense is
storytelling gold; nothing else on this list makes the issue feel current.

- **Cost: medium** — the API integration we deliberately postponed, token
  management, and a rate-limit-respecting proxy.
- **Honesty:** live AIS positions are NOT classified effort (no neural-net
  fishing detection at realtime granularity in the public tier) — the layer
  must be labeled "vessels present", never "fishing".
- Interview-demo consideration: adds a third-party dependency to the live
  site (see portfolio memory: keep the demo dependency-light) — perhaps a
  toggle, off by default.

## 6. Everyday-unit anchors (small)

In the estimate panel: "15.7 Mt ≈ annual emissions of ~3.4 million cars;
15.7 kt ≈ a few thousand — *the disagreement is the story*." Comms research
says anchors land; the honesty move is anchoring BOTH ends so the range
itself is the message. Cost: an afternoon (with the conversion factor cited).

## 7. Cell permalinks — shareability (small)

Every cell gets a URL (`/?cell=5390,764&year=2024`) that opens the map there
with its full provenance popover. Turns the atlas into something people pass
around; costs little (URL state + a cell-detail popup, which the tiles'
properties already power).

## 8. Split-screen "referee mode" (speculative)

Two synchronized panes of the same map/period framed under Team Sala vs Team
Hiddink assumptions. Educational about HOW assumptions drive conclusions —
but the preset slider already teaches this, and the map's spatial pattern is
preset-invariant, so the panes would differ only in panel numbers. Probably
redundant; recorded so we remember *why* we didn't do it.
