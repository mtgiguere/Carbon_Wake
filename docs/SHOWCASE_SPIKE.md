# Showcase / Storytelling Spike — findings (run 2026-08-26)

> Status: **complete**. This replaces the 2026-08-23 placeholder, per its own
> instruction. Same honesty discipline as every spike: web-verified facts are
> flagged; design judgments are labeled as judgments. Nothing here is built —
> these findings feed the frontend step, where the tech choices get their own
> ADR and every visual claim meets Blind spot B (pixel tests) before it is
> called working.

## 1. Audience — who is the 30-second visitor?

Three personas, in priority order, each with what they must grasp in 30
seconds:

1. **The journalist / science communicator.** Needs: the hook ("scientists
   disagree about trawling's CO2 by up to 1000×; drag the slider yourself"),
   one striking visual, and a citation trail they can defend to an editor.
2. **The policy / NGO analyst.** Needs: a defensible regional number WITH its
   range and caveats, per-area drill-down (their patch of sea), and the
   sources list — they will be challenged on it.
3. **The skeptical scientist.** Needs: the methods, fast — a visible path
   from any pixel to its provenance, the limitations stated before they ask,
   and RIGOR.md one click away. This persona is won or lost on honesty, and
   winning them protects the other two.

## 2. The story we can now tell (it got better since the placeholder)

The placeholder's framing holds — **the dispute is the hook** — and the work
since added a second hook the placeholder couldn't have: **the audit story**.
"Our own review caught our model overstating by 3.4×, and we published the
correction with the fix" (ADR-0014) is the most credible sentence this
project can say to a skeptic. Use it.

### Story-mode storyboard (six beats + coda)

All figures below are real, current, and already served by the API:

1. **The fleet.** A year of real 2012 trawling animates across the North Sea
   (GFW daily data — real vessels, honestly labeled "all trawlers, bottom and
   midwater, plus dredgers"). 531k fishing hours in view.
2. **The carbon beneath.** Crossfade to Diesing's seafloor carbon — and its
   per-pixel uncertainty as a second visual channel, introduced as a
   first-class idea, not an apology.
3. **The overlap.** The two layers intersect: 153,834 cells light up. Camera
   dives to the Dutch delta hotspots (up to 427 trawl-hours in one cell —
   swept end to end ~250 times over).
4. **The disputed number.** The preset slider walks the same map from
   **3,982 tonnes (Hiddink-inferred) to 3.98 million tonnes (Sala)** of
   first-year aqueous CO2 — each stop naming its paper, quoted-vs-derived
   flag visible. This interaction IS the product.
5. **What we don't know.** The unmapped-effort layer appears (296k hours the
   carbon map can't price — drawn distinctly, never blank-as-ocean), the
   uncertainty bands widen into view, and the caveats surface as UI, not
   fine print.
6. **Explore yourself.** Sandbox: pan, per-cell inspection (hours by gear,
   carbon ± uncertainty), bbox queries, gear toggle, year slider (once
   multi-year runs exist).

**Coda — the trust beat:** one panel on the 3.41× self-correction, linking
RIGOR.md. Turn the audit into the credibility close.

### The front door (repo/README + landing)

- One-line pitch: *"Scientists disagree about bottom trawling's CO2 impact by
  a factor of 1000. Explore the disagreement yourself — every number cited."*
- Hero: a short animated capture of beat 3→4 (overlap, then the slider).
- Three links: the live map (step 7), "How we compute this" (SCIENCE_BASIS),
  "How to audit us" (RIGOR).

## 3. The visual-honesty policy (adopt when frontend starts; testable)

1. **Animate only real data.** Real vessel effort, real carbon, real time.
   No faux fauna, currents, or atmosphere. Any purely illustrative element
   (e.g. a diagram of gear penetrating sediment) is labeled *illustration*.
2. **Color encodes measured quantities only**, with legends naming units and
   the source dataset.
3. **No mean without its uncertainty reachable in one gesture** — the
   never-a-bare-number rule extended to pixels.
4. **Unmapped ≠ zero, visually.** Cells with effort but no carbon data get a
   distinct treatment (hatch/neutral), never the ocean background.
5. **Layer names use the ADR-0009 label verbatim.** The word "bottom" alone
   never labels the effort layer.
6. **Every on-screen number is one click from its citation** (the API already
   ships citations with every figure; the UI must not strip them).
7. **The range is the default view.** A single-preset view is an explicit
   user choice, visibly labeled with the chosen preset.

## 4. Tech feasibility (verified 2026-08-24/26)

- **Map library: MapLibre GL JS** — recommended (final choice = ADR at
  frontend start). BSD-3, Linux Foundation governance, fork of Mapbox GL JS
  1.13, provider-independent, no token [VERIFIED — maplibre repo/npm,
  MapTiler/Geoapify histories]. Mapbox GL JS v2+ is proprietary-licensed
  with token+billing — against the self-hosted ethos. PROJECT_SPEC said
  "Mapbox GL JS (or similar)"; MapLibre is the "similar" that fits.
- **Basemap: Protomaps PMTiles** self-hosted (whole basemap = one static
  file read by HTTP range requests; no tile server, no key; regional extract
  via pmtiles CLI) [VERIFIED — protomaps.com/docs]; **OpenFreeMap** is the
  zero-effort hosted fallback (free, no key) [VERIFIED — github/hyperknot].
  Either way OSM ODbL attribution is required on the map [VERIFIED].
- **Our data layer:** 154k cells is too heavy as one GeoJSON fetch. Serve
  **vector tiles from PostGIS via ST_AsMVT** through a small DRF endpoint —
  the GiST-indexed geometry column was built for exactly this. (Feasibility
  judgment; not built.)
- **Preset slider:** the science stays server-side. The UI switches between
  per-preset numbers the API already serves; if per-cell preset coloring is
  wanted, the cells/tiles payload grows a server-computed per-cell disturbed
  mass — the client never re-derives science.
- **Time animation:** one ETL run per year, 2012–2024 (recent-year zips are
  ~3.3 GB; ingest ≈6 min/year on this machine) → a year slider over runs.
- **Story mode:** MapLibre camera choreography (`flyTo`/`easeTo`) driven by
  a scrollytelling controller; prototype against Blind spot B from day one —
  **every layer gets a SwiftShader pixel smoke test before it is called
  visible.**

## 5. Attribution stack (must appear on every showcase surface)

GFW "Powered by Global Fishing Watch" + CC BY-NC 4.0 (the atlas stays
non-commercial, ADR-0008); Diesing 2021 CC-BY-4.0; OpenStreetMap ODbL (basemap);
per-preset paper citations wherever an estimate shows; the ADR-0009 label
wherever effort shows.

## 6. What this spike deliberately does NOT decide

Final visual design, scroll mechanics, palette, and copy — those are
prototyped against real pixels when the frontend step starts (with the map
library ADR). This spike fixes the audience, the narrative spine, the honesty
rules, and the technically-verified foundations, so that step starts with
taste decisions only.
