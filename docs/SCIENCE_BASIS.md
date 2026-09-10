# Science Basis — the disputed trawling-carbon estimates

> This is the sourced, verified record of the published estimates the tool
> visualizes. It is the provenance behind every reactivity preset. The project's
> credibility rests on this file being honest about **what is a quoted figure, what
> is derived, and what could not be verified from a primary source.** Update it
> only with a citation, and preserve the verification flags.

The central quantity — CO2 released from bottom-trawling disturbance of seafloor
sedimentary organic carbon — is contested across roughly **two to three orders of
magnitude**. The tool exists to show that span honestly, not to pick a number.

Two distinctions matter throughout and must never be blurred:

- **Aqueous vs atmospheric CO2.** Sala's headline figure is *aqueous* (dissolved in
  the water column). Only a fraction reaches the atmosphere. Mixing the two
  inflates the apparent climate impact.
- **Additionality.** Some of the disturbed carbon would have remineralized to CO2
  anyway. Whether an estimate nets out that natural background is the crux of the
  dispute.

Unit note: 1 Pg (petagram) = 10¹⁵ g = 1 Gt = 1 billion tonnes. CO2:C mass ratio =
44/12 ≈ 3.67. Sala's "0.16–0.40 Pg **C**/yr" and "0.59–1.47 Pg **CO2**/yr" are the
same range in different units — do not double-count them as separate estimates.

---

## Sala et al. 2021 — the original high estimate

- **Citation:** Sala, E., Mayorga, J., Bradley, D., Cabral, R.B., Atwood, T.B., et al.
  (2021). "Protecting the global ocean for biodiversity, food and climate." *Nature*
  592, 397–402. DOI: [10.1038/s41586-021-03371-z](https://doi.org/10.1038/s41586-021-03371-z).
  (Author Correction: DOI 10.1038/s41586-021-03496-1.)
- **Headline:** **1.47 Pg CO2** in the first year after trawling (aqueous), declining
  to a steady state of **~0.58 Pg CO2/yr** after 9 years of continuous trawling.
- **Key parameter [VERIFIED from the paper's PDF]:** per-pixel remineralization model
  `Ia = SVR · p · (1 − e^(−k·t))`; stated **average remineralization efficiency of
  disturbed carbon = 29.7%**; λ = 0.3 in the multi-year model; 87% of disturbed
  sediment resettles.
- **Scope / caveats [VERIFIED quotes]:** the 1.47 Pg is **aqueous**, not atmospheric —
  the paper says "an unknown fraction of the aqueous CO2 is emitted to the
  atmosphere." Additionality is **not** credited. The authors call it "a preliminary
  best estimate … further research is required."

## Atwood et al. 2024 — the Sala group's atmospheric follow-up

- **Citation:** Atwood, T.B., Romanou, A., DeVries, T., Lerner, P.E., Mayorga, J.S.,
  Bradley, D., Cabral, R.B., Schmidt, G.A., & Sala, E. (2024). "Atmospheric CO2
  emissions and ocean acidification from bottom-trawling." *Frontiers in Marine
  Science* 10:1125137. DOI: [10.3389/fmars.2023.1125137](https://doi.org/10.3389/fmars.2023.1125137).
- **Headline [VERIFIED]:** **0.34–0.37 Pg CO2/yr to the atmosphere** (1996–2020 annual
  average).
- **Key parameter [VERIFIED]:** "55–60% of the CO2 released into the water column …
  is emitted to the atmosphere within ~9 years." Same disturbed-carbon flux as Sala;
  does not adopt Hiddink's additionality correction.

## Epstein et al. 2022 — review / middle-ground critique

- **Citation:** Epstein, G., Middelburg, J.J., Hawkins, J.P., Norris, C.R., & Roberts,
  C.M. (2022). "The impact of mobile demersal fishing on carbon storage in seabed
  sediments." *Global Change Biology* 28(9), 2875–2894.
  DOI: [10.1111/gcb.16105](https://doi.org/10.1111/gcb.16105).
- **Headline:** A systematic review; **no new global point estimate.** Cites Sala's
  0.16–0.40 Pg C/yr as highly uncertain.
- **Argument [VERIFIED from GCB open-access text]:** Sala assumed "anything between 1
  and 69.3%" of disturbed carbon is remineralized — likely too high because they used
  basin-scale incoming-OC-flux parameters rather than the much lower values
  representative of the buried sedimentary *stock*; resuspended carbon may be moved
  elsewhere rather than remineralized.

## Hiddink et al. 2023 — the low-end critique (Nature Matters Arising)

- **Citation:** Hiddink, J.G., van de Velde, S.J., McConnaughey, R.A., De Borger, E.,
  Tiano, J., Kaiser, M.J., Sweetman, A.K., & Sciberras, M. (2023). "Quantifying the
  carbon benefits of ending bottom trawling." *Nature* 617, E1–E2.
  DOI: [10.1038/s41586-023-06014-7](https://doi.org/10.1038/s41586-023-06014-7).
- **Headline:** Argues Sala **overestimated by ~100–1000× (two to three orders of
  magnitude).** Publishes **no single alternative global point estimate** — only the
  magnitude of the overestimate.
- **Argument [SECONDARY sources — see flags]:** Sala applied fresh-surface-carbon
  reactivity (labile fraction and high decay constants) to much less reactive buried
  carbon, and did not credit additionality: "the majority of this organic carbon …
  would decompose and be released as CO2 regardless of whether it is disturbed."

## Sala et al. reply 2023

- **Citation:** Sala, E., et al. "Reply to: Quantifying the carbon benefits of ending
  bottom trawling." *Nature* 617, E3–E5 (2023).
  DOI: [10.1038/s41586-023-06015-6](https://doi.org/10.1038/s41586-023-06015-6).
- **Stance [SECONDARY]:** rejects the critique as lacking "quantitative support";
  full text gated, not read directly.

---

## The range the debate spans

Roughly **0.001 to 1.5 Pg CO2/yr** globally (~2–3 orders of magnitude):

- **High anchor — Sala 2021:** 1.47 Pg CO2/yr first-year (aqueous); ~0.58 Pg/yr
  aqueous steady state; ~0.34–0.37 Pg/yr *atmospheric* per Atwood 2024.
- **Low anchor — Hiddink 2023:** 100–1000× below Sala. Applying that to Sala's
  ~0.58 Pg steady state gives order ~0.0006–0.006 Pg CO2/yr — but **this absolute
  number is an inference; Hiddink published no such figure.** Treat as illustrative.
- **Middle — Epstein 2022:** no competing point value; "highly uncertain, likely
  overstated."

**Consensus:** a single point estimate is not defensible; a range with explicit
uncertainty is the honest representation.

---

## The disturbed-carbon model (researched 2026-08-24 for the v1 estimate layer)

The presets above convert *disturbed carbon mass* to CO2. This section is the
provenance for how disturbed mass itself is computed from effort + carbon data.

### Sala 2021's own chain [VERIFIED — publisher PDF via Archimer, 82604.pdf]

- Per-pixel loss fraction: `Ia_i = SVR_i · p_crd_i · p_lab_i · (1 − e^(−k_i·t))`,
  t = 1 year; `p_crd` (fraction resettling in the pixel) constant at **0.87**.
- `SVR_i = Σ_g SAR_i,g × p_depth_g` — swept area ratio times gear penetration
  depth, applied to the carbon in the **first meter** of sediment (`c_i0`).
- `SAR_i,g = Σ_v TD_i,v × W_v / A_i` — trawled distance (AIS speed × time,
  GFW 2016–2019) times per-vessel gear width over pixel area.
- Gear widths from Eigaard et al. 2016 vessel-size relationships, quoted
  verbatim from Sala's methods:
  - towed & hydraulic dredges: `W = 0.3142 × LOA^1.2454` (LOA in m),
  - otter trawls: `W = 10.6608 × KW^0.2921` (engine power in kW),
  - beam trawls: `W = 0.6601 × KW^0.5078`.
- Speed/depth plausibility filters per gear (from Eigaard): otter 2–4 kn,
  beam 2.5–7 kn, dredges 2–2.5 kn.
- Penetration depths from Hiddink et al. 2017 (PNAS 10.1073/pnas.1618858114):
  **otter 2.44 cm, beam 2.72 cm, towed dredge 5.47 cm, hydraulic dredge
  16.11 cm** [VERIFIED in Sala's methods AND restated in Atwood 2024's
  open-access methods; Hiddink's own PDF not fetched].
- Vessels without official gear classification were classified as **otter
  trawls** ("the most common type of bottom trawlers in the ocean");
  registry-identified midwater trawlers were excluded [VERIFIED quote].
- **The 29.7% ties in here [VERIFIED]:** "The average remineralization
  efficiency of disturbed carbon—estimated as the mean across pixel level
  remineralization rates—is 29.7%." I.e. it is the mean of
  `p_crd · p_lab · (1 − e^(−k))` — the fraction of *disturbed* carbon
  remineralized, resettlement included. Our preset semantics
  (`remineralization_fraction` of disturbed mass) match it exactly; no extra
  0.87 factor may be applied on top.

### What the Trawl Carbon Atlas v1 encodes (and how it deviates)

`disturbed_carbon_mass = fishing_hours × towing_speed × gear_width ×
penetration_depth × OC_density`, per cell, with these deviations from Sala,
each one honest about what our data can support:

1. **Fleet-average gear width instead of per-vessel width.** GFW's fleet-daily
   product has no vessel identities, so Sala's per-vessel `W_v` is replaced by
   a class-average width: Sala's own Eigaard relationship evaluated at the
   fleet-average vessel size computed from GFW's `fishing-vessels-v3.csv`
   (the same dataset's vessel table). The averages used are recorded in
   ADR-0012 with the exact computation.
2. **GFW's "trawlers" class is treated as otter trawls** — Sala's own default
   for unclassified vessels — and `dredge_fishing` as towed (non-hydraulic)
   dredges. Consequence of ADR-0009: midwater trawlers are inside the class,
   so v1 *overstates* swept bottom area where midwater effort is common; the
   labeling requirement extends to any figure derived from it.
3. **Regional surficial OC density instead of a global first-meter stock.**
   Diesing 2021 provides kg/m³ density of *surface* sediments with per-pixel
   uncertainty. Since gear penetrates 2–6 cm — within the surficial layer —
   `swept_area × penetration_depth × density` needs no 1 m stock at all: the
   volume disturbed is priced at the density of the sediment actually
   penetrated. This is arguably *more* defensible regionally than the global
   stock approach; it is still a deviation and is labeled as such.
4. **Uncertainty propagated from the carbon layer only.** Width, speed, and
   penetration depth carry real spread (Eigaard's SDs; Hiddink's ranges) that
   v1 does NOT quantify — the disturbed mass inherits only the carbon
   density's per-pixel uncertainty. Recorded as an explicit unquantified-
   uncertainty caveat, not silently ignored.
5. **Uncertainties combine LINEARLY across cells and gears** (added
   2026-08-24, with the estimate layer). Linear is the conservative, fully
   correlated treatment: Diesing's per-pixel *total* uncertainties include
   systematic model components that cannot be assumed independent between
   pixels, and within a cell the gear classes share one density. Summing in
   quadrature would claim an independence we have not established and would
   understate the band.

### Known limitations of the v1 derived layer (retrospective, 2026-08-24)

The encoding of the published science above is verified; the *derived* layer —
what we compute on top of it — has known weaknesses, ranked by severity. Every
served estimate carries these as caveats (`ESTIMATE_CAVEATS`); this is the
fuller record.

1. **No saturation — RESOLVED 2026-08-26 (ADR-0014).** As identified in the
   2026-08-24 retrospective: disturbed mass was linear in fishing hours, but
   a 0.01° cell holds a finite amount of sediment (the busiest 2012
   Dutch-delta cell had a swept-area ratio ≈255, so the linear model counted
   the same top 2.44 cm ~255 times). **The fix:** per cell and gear, the
   disturbed footprint is now cell_area × (1 − e^(−SAR)) — the Poisson
   footprint estimator. Provenance: Amoroso et al. 2018 (PNAS
   10.1073/pnas.1802379115; read via PMC6205437) estimates footprint on the
   assumption, quoted verbatim, that "the number of times that any point
   within the cell is trawled is randomly (Poisson) distributed"
   [VERIFIED]; the closed form 1 − e^(−SAR) is OUR standard derivation from
   that assumption [DERIVED]. Amoroso also documents that real trawling is
   aggregated ("the most intensively trawled areas accounting for 90% of
   activity comprised 77% of footprint on average") and that "repeated
   passes on a previously trawled seabed each have a smaller impact than the
   first pass" [VERIFIED] — so the Poisson bound still overstates freshly
   swept area and the estimate remains conservative-high. **Measured
   effect:** the naive model had overstated 2012 North Sea disturbed carbon
   by 3.41× (12.47 Mt → 3.66 Mt ± 2.02 Mt). Year-to-year depletion and
   recovery remain unmodeled (first-year framing only).
2. **The headline is a composition Sala never published.** We apply Sala's
   29.7% mean efficiency to a disturbed mass computed differently from his
   (regional surficial density, fleet-average widths, no midwater exclusion).
   The honest description is "Sala's assumptions transplanted onto regional
   data", never "Sala's estimate for the North Sea".
3. **Midwater contamination is material here.** The North Sea hosts
   significant midwater trawling (herring, mackerel); ADR-0009's as-published
   gear classes therefore overstate bottom contact non-trivially in some
   areas. Two candidate remedies are on the roadmap: the registry
   cross-reference (Sala's own method), and an empirical plume-based filter —
   a midwater trawler leaves no sediment plume, so AIS-paired satellite plume
   detections identify bottom contact directly (docs/VALIDATION_SPIKE.md §3).
4. **The uncertainty band is not a confidence interval.** ±7.2 Mt is the
   linear (fully correlated) propagation of Diesing's per-pixel total
   uncertainty through the chain — an indicative band with a stated
   convention, not a statistical CI. Gear-parameter spread (width, speed,
   penetration) is real and unquantified in v1.
5. **2012 AIS coverage undercounts effort** (pre-2017 coverage is thin and
   uneven), so the effort side is biased LOW for that year even as the
   saturation flaw biases disturbed carbon HIGH — the two do not cancel in
   any knowable way.

One genuine strength worth stating alongside: pricing the disturbed volume at
Diesing's *measured surficial* density (the sediment the gear actually
penetrates, with per-pixel uncertainty) is arguably more defensible regionally
than Sala's global first-meter stock.

**Gear widths are year-specific, and 2012's is itself a coverage artifact
(noted 2026-08-27, with the multi-year extension).** The effort-weighted
otter-trawl width computed from GFW's vessel table is 77.28 m for 2012 but
settles to ~63–65 m for 2013–2024 — because 2012's classified fleet held only
5,654 trawlers (early AIS skewed toward large vessels) versus 39,419 by 2024.
Every run is therefore priced with its own year's widths
(`gear_profiles_for_year`, provenance naming the year and vessel count), and
the 2012 estimates carry a known mild high bias on swept area from this
artifact — disclosed here rather than smoothed away.

### Verification additions (2026-08-24)

**Verified against primary full text:**
- Sala 2021 methods: the `Ia` equation, p_crd = 0.87, SVR/SAR construction,
  the three Eigaard width relationships, speed filters, penetration depths,
  otter-trawl default for unclassified vessels, first-meter stock basis, the
  29.7%-is-mean-pixel-efficiency sentence — Archimer publisher PDF.
- Atwood 2024 restates SVR = SAR × penetration depth and the same four
  penetration depths — Frontiers open access.
- Eigaard et al. 2016 (ICES JMS 73:i27–i43, DOI 10.1093/icesjms/fsv099, open
  PDF via DTU Orbit): Table 5 towing speeds (OT_DMF 3.1±0.2 kn, OT range
  2.5–3.4 kn, TBB_DMF 5.2±1.3 kn, DRB_MOL 2.5±0.0 kn); otter-trawl affected
  width "typically in the range of 25–250 m"; dredge widths 0.75–3 m per
  dredge; hourly swept-area estimate ≈1.2 km²/h for OT Nephrops+mixed
  demersal métier.

**NOT verified from primary text:**
- Hiddink et al. 2017's own PDF (penetration depths taken from Sala's and
  Atwood's verbatim citations of it, plus secondary press coverage).

**Verified against primary full text:**
- Sala 2021 figures, 29.7% efficiency, λ=0.3, aqueous caveat — from the Archimer/Ifremer open-access PDF.
- Epstein 2022 "1–69.3%" and the parameter-overestimate argument — GCB open-access (PMC9307015).
- Atwood 2024 0.34–0.37 Pg/yr atmospheric and 55–60% figures — Frontiers open access.
- Hiddink 2023 citation, authors, DOI, pages — PubMed / institutional portals.

**NOT verified from primary full text (secondary sources only) — flagged for spot-check:**
- Hiddink 2023 full text (nature.com, repository PDFs all 403). The 100–1000× factor,
  the reactivity/decay-constant argument, and the additionality quote are corroborated
  by multiple independent secondary sources + the peer-reviewed Epstein paper, but not
  read in Hiddink's own PDF.
- Specific values p = 0.7 and k = 0.3–17 yr⁻¹ attributed to Sala's model come from a
  secondary summary, not Sala's supplementary tables.
- Sala 2023 reply — full text gated.
- Any absolute low-end figure — inferred from Hiddink's factor, never published as such.

## Everyday anchors (added 2026-09-07)

The estimate panel expresses each CO2 figure as a count of something
familiar, so a reader can feel the scale of the *disagreement* — both ends
of the range are anchored in the same unit; one anchored figure never stands
alone (`carbon_atlas.anchors`, docs/IDEAS.md #6).

- **Typical passenger car, one year = 4.6 metric tons CO2.** US EPA, Green
  Vehicle Guide, "Greenhouse Gas Emissions from a Typical Passenger Vehicle":
  "A typical passenger vehicle emits about 4.6 metric tons of carbon dioxide
  per year", assuming 22.2 miles per gallon, 11,500 miles per year, and
  8,887 g CO2 per gallon of gasoline
  (https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle)
  [VERIFIED — primary page fetched 2026-09-07; page last updated 2026-06-03].
  This is a US fleet-average convention (EU fleet averages are lower per
  car); it is a scale, not a measurement of any fleet.

**Comparability limit (stated on the panel, not in a footnote):** a car's
figure is tailpipe CO2 released to the atmosphere; the atlas's headline is
*aqueous* first-year CO2 in seawater, of which an unquantified fraction
reaches the atmosphere (see the caveats). The anchor is therefore "for scale
only" and is never phrased as an equivalence. The count carries the CO2
quantity's uncertainty, divided by the same factor — the anchor can neither
tighten nor loosen a band.

For the 2024 North Sea run this reads: low ≈ 3,400 ± 2,000 car-years
(Hiddink-inferred) to high ≈ 3,400,000 ± 2,000,000 car-years (Sala) — the
1000× dispute, in units a reader already owns.

## The cumulative footprint (added 2026-09-08, ADR-0017)

**The claim.** "Fraction of the carbon-mapped North Sea seabed trawled at
least once, 2012–<latest year>" — a coverage claim independent of every
reactivity preset. Per 0.01° cell and year, SAR = hours × speed × width /
cell area (that year's fleet widths, ADR-0016); the year's footprint is
1 − e^(−SAR) (ADR-0014). Across years the atlas reports a **bracket**:

- **floor** — the largest single-year footprint (no cross-year assumption);
- **Poisson union** — 1 − e^(−ΣSAR), tow placement independent and random
  across years as well as within them [DERIVED — extension of Amoroso's
  within-year assumption; not a published estimator for multi-year union];
- **ceiling** — the annual footprints summed, capped at the cell.

The denominator is the mapped seabed of Diesing 2021 (count of mapped 500 m
pixels × 0.25 km², exact on the LAEA grid). Effort on unmapped seafloor is
reported as an area only.

**Published comparator [VERIFIED — Amoroso et al. 2018, PNAS
10.1073/pnas.1802379115, Table 1 read from PMC6205437 on 2026-09-08].**
North Sea (ICES 4a–4c), VMS/logbook effort 2010–2012, 86% coverage of
bottom-trawling effort, depths 0–1000 m (586 × 10³ km²): regional SAR
1.191 yr⁻¹; area trawled per year **89.3%** under the grid-cell assumption
(approach A), **42.2%** under the random-placement assumption (approach B —
the estimator this atlas uses), **51.7%** under the uniform assumption
(approach C); 39.8% of the region accounts for 90% of activity. Our per-year
mapped footprints are the like-for-like comparison to the 42.2% figure; the
multi-year union has no published counterpart. Differences to expect: our
effort is AIS-based (GFW; thinner coverage before 2017), our gear classes
include midwater trawlers (ADR-0009), and our denominator is the
carbon-mapped seabed rather than the ICES area. Eigaard et al. 2017 (ICES
JMS 74:847–865) report European management-area footprints of 53–99%
(0–200 m, cell-based) and 28–85% after excluding untrawled proportions
[VERIFIED — abstract only; the North Sea row not read].

**Biases, both directions (stated on the product, not here alone).**
Aggregation — real fleets revisit the same tows year after year (Amoroso
2018: the most intensively trawled areas accounting for 90% of activity
comprised 77% of footprint on average) — makes the Poisson union an
overestimate of the true multi-year footprint. AIS under-coverage in early
years makes every figure an underestimate of effort. Midwater contamination
makes swept bottom area an overestimate. None of these cancel in a knowable
way; the floor is the only figure that needs no cross-year assumption.

**First real computation (2026-09-08, years 2012–2015 + 2024, 1,434,122
cells, mapped seabed 531,385 km²):** floor 36.2%, Poisson union 40.4%,
ceiling 43.0%; per year 2012 5.3%, 2013 16.7%, 2014 16.6%, 2015 18.0%,
2024 23.6%. Against Amoroso's 42.2%/yr the AIS-based per-year footprint is
roughly half — the expected direction (VMS covers the EU fleet ≥12 m with
near-complete coverage; AIS carriage and reception were far thinner,
especially before 2017, and small vessels are missed), so the atlas's
coverage figures should be read as what AIS SAW, not what the fleet did.
The 2012→2013 tripling is the AIS coverage jump, not a fishing trend. These
figures change as the backfill completes; the served summary names its years.

## Reference zones: offshore wind farms (added 2026-09-10, ADR-0018)

**Source [VERIFIED 2026-09-08].** EMODnet Human Activities, "Wind Farms
(Polygons)" (CETMAR for EMODnet; annual update), WFS layer
`emodnet:windfarmspoly` at https://ows.emodnet-humanactivities.eu/wfs,
EPSG:4326, GeoJSON output; 600 polygons Europe-wide, 456 inside the Diesing
envelope, of which 150 Production, 19 Construction, 57 Approved, 219 Planned,
10 Dismantled, 1 Test site. License **CC-BY 4.0** (metadata record
8201070b-4b0b-4d54-8910-abcea5dce57f, "otherConstraints"). Attributes: name,
country, status, year (commissioning; **null for 44 of 160 producing farms,
1,739 of 7,178 km² — 29 of them UK**), power_mw, n_turbines, area_sqkm,
type_inst (Grounded/Floating).

**Regulatory background [UNVERIFIED — general knowledge, to be sourced].**
Belgium, the Netherlands, Germany, and Denmark close producing farms to
bottom-contact fishing (safety zones / permit conditions); the UK generally
does not, and co-location with fishing is common. This is why the contrast is
read per country. A primary-source pass (national permit conditions) is owed
before any per-country sentence hardens into a claim.

**The measurement.** For a run with effort year Y: farms with a known
commissioning year ≤ Y−1; inside = hours of the run's cells apportioned by
the intersected fraction of each 0.01° cell to the farm polygon, divided by
the FULL polygon area (PostGIS geography, ellipsoidal); ring = the same for
the 5 km buffer minus every farm. Farms without a year are counted, not
measured. Ratio = inside density / ring density; undefined when the ring saw
no effort.

**Spike verification (2026-09-08, 2024 run = run 2, farms commissioned ≤
2023, rings NOT yet carved of neighbouring farms):**

| Country | farm area km² | inside h/km² | 5 km ring h/km² | ratio |
|---|---|---|---|---|
| United Kingdom | 4,137 | 0.72 | 1.49 | 0.48 |
| Netherlands | 1,049 | 0.08 | 0.69 | 0.11 |
| Germany | 790 | 0.18 | 1.70 | 0.11 |
| Denmark | 512 | 0.20 | 2.95 | 0.07 |
| Belgium | 232 | 0.01 | 0.70 | 0.02 |
| **All** | **6,731** | **0.49** | **1.51** | **0.33** |

2012 control (run 1, farms ≤ 2011, 2,012 km²): all countries inside 0.60 vs
ring 0.45 h/km² (ratio 1.33) — no deficit before the farms existed at scale
(and 2012 AIS coverage is thin; the Dutch 2012 figure, 2.61 vs 2.21 on 400
km², is small-sample noise or midwater effort, not evidence of trawling
inside closed farms — unresolved).

**Product measurement (first run 2026-09-10; producing farms only, unknown
year excluded, rings carved of every farm; six runs, 8 s).** Two rules moved
the figures away from the spike's: excluding the 41 unknown-year farms (29 of
them UK) and excluding farms under construction (their "year" is a plan).

| Run year (farms ≤ year−1) | farms measured | farm km² | inside h/km² | ring h/km² | ratio |
|---|---|---|---|---|---|
| 2012 (≤2011) | 29 | 330 | 0.29 | 0.75 | 0.39 |
| 2013 (≤2012) | 34 | 658 | 0.65 | 2.89 | 0.22 |
| 2014 (≤2013) | 40 | 845 | 0.20 | 2.84 | 0.07 |
| 2015 (≤2014) | 45 | 996 | 0.17 | 2.65 | 0.06 |
| 2016 (≤2015) | 57 | 1,384 | 0.07 | 2.63 | 0.03 |
| 2024 (≤2023) | 106 | 5,049 | 0.64 | 1.54 | 0.41 |

Per country, 2024: Belgium 11 farms / 177 km² ratio **0.01**; Germany 22 /
626 km² **0.04**; Denmark 13 / 463 km² **0.07**; Netherlands 11 / 697 km²
**0.13**; United Kingdom 47 / 3,076 km² **0.81** (inside 0.97 vs ring 1.19
h/km²). The UK figure is the finding: its ratio was **0.02 in 2016** (27
nearshore farms, 753 km²) and **0.81 in 2024**, after the very large
offshore farms commissioned 2019–2023 (Hornsea, Moray, Triton Knoll, Dogger
Bank lineage) entered the measured set — farms sited on heavily trawled
grounds that permit fishing. Whether the inside effort is bottom-contact or
midwater cannot be told from GFW's class (ADR-0009). The 2012 figure (0.39
on 330 km²) is not a clean "before" control either: farms that existed by
2011 were already closed areas in BE/NL/DE/DK. The spike's 2012 ratio of
1.33 was an artifact of including unknown-year farms and is withdrawn.

**What it is not.** Not a matched control (sites are chosen for wind and
depth); not bottom-contact-only effort (ADR-0009); not a trend (AIS coverage
grew); not a statement about safety zones or cable corridors (not in the
polygons).
