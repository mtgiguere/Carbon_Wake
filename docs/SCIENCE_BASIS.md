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
   areas. The registry cross-reference (Sala's own method) remains the
   scheduled remedy.
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
