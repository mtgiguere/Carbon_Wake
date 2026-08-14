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

## Verification flags (read before trusting any number here)

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
