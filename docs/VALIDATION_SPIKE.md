# Measurement & Validation Spike — PLANNED, NOT STARTED

> Status: **placeholder**. Captured 2026-08-27 from a project-owner idea (the
> same pattern as docs/SHOWCASE_SPIKE.md's placeholder): use the atlas not
> just to *display* the disputed science but to **target the measurements
> that could narrow it**. No design or code work has been done. When a slice
> runs, its findings replace the relevant section here.

## The owner's insight

Satellites can see *what got stirred up* (sediment plumes, via ocean-color /
hyperspectral imagery) even though no sensor can see the dissolved CO₂
itself. So: layer real observation assets over the effort map, and the atlas
becomes a **sampling-design and archive-mining tool** — "which existing
sensors have been sitting inside heavy trawling grounds all along, and on
which days did trawlers pass them?"

## Three slices, effort-ranked

### 1. The monitoring-infrastructure layer + targeting query (days of work)

- Plot existing in-situ assets over the effort map: ICOS ocean stations,
  moored pCO₂/turbidity buoys, BGC-Argo float tracks, SOCAT ship lines
  (all open data; a point/line layer).
- The targeting query is already within PostGIS's reach: "every cell within
  N km of asset X, ranked by trawl hours" (`ST_DWithin` over the GiST
  index). Because the raw GFW *daily* files stay on disk, the atlas can then
  emit **event lists**: "trawlers worked within 3 km of buoy B on these
  dates" — exactly what an archive-mining study needs (buoy time series on
  trawled days vs. matched quiet days). Near-zero cost, genuinely
  publishable, and the study runs on data that already exists.
- Bonus reference zones: offshore wind farms are de facto trawl exclosures —
  mappable, and natural controls for inside/outside comparisons.

### 2. The Sentinel-2 plume pilot (a real project)

- Ocean-color imagery (Sentinel-2 10 m; PACE hyperspectral for composition)
  can detect individual trawler sediment plumes — published precedent
  exists. This validates the model's FRONT end empirically: effort here
  really did resuspend sediment, and hyperspectral composition (mineral vs.
  organic/CDOM) bears on the labile fraction — the single most disputed
  parameter in the Sala/Hiddink fight.
- The confounder to respect: the southern North Sea is NATURALLY turbid
  (tides, storms, the Wadden coast). Attribution requires AIS pairing — a
  linear turbidity feature trailing a known trawler track on a calm day —
  never raw turbidity maps.
- Pilot shape: a handful of clear-day Sentinel-2 scenes over the Dutch-delta
  hotspot, matched to same-day AIS tracks from our dailies.

### 3. Plume-based bottom-contact discrimination (research-grade)

- A midwater trawler leaves NO sediment plume. Plume-confirmed effort is,
  by physics, bottom-contact effort. At scale, AIS-plume pairing yields an
  **empirical, registry-free answer to ADR-0009's midwater-contamination
  caveat** — currently handled by an honest label and a deferred registry
  cross-reference. This would be the atlas's first original scientific
  contribution rather than a visualization of published work.

## What imagery cannot do (recorded so nobody re-derives it)

Dissolved CO₂/DIC is optically invisible (no visible/NIR signature), and
ocean-color instruments see only the top optical depth (~meters), not the
bottom water where trawl CO₂ accumulates. Atmospheric CO₂ imagers (OCO-2/3,
the coming CO2M plume mappers) are built for concentrated point sources;
trawling's outgassing is water-mediated, decade-delayed, and current-smeared —
orders of magnitude below detectability per unit area. The chemistry end
belongs to ships, floats, buoys, and benthic landers; slice 1 exists to point
them (and their archives) at the right places and days.

## Honesty rules that apply when this runs

Real detections only, AIS-attributed, never raw turbidity sold as trawling;
every layer labeled with instrument + date; natural-background confounders
stated on the layer, not in a footnote; the visual-honesty policy
(docs/SHOWCASE_SPIKE.md §3) governs any imagery shown.

## Slot on the roadmap

After the current multi-year / story-mode arc. Slice 1 first — it is cheap,
it compounds (every later slice uses its layer), and it turns the atlas from
a display into an instrument.
