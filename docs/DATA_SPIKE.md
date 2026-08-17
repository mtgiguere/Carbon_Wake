# Data Exploration Spike — trawling effort & sediment carbon access

> Findings of the PROJECT_SPEC step-1 spike, researched 2026-08-14. Same honesty
> discipline as SCIENCE_BASIS.md: every load-bearing fact is tagged **[VERIFIED]**
> (checked against a primary source or a live HTTP response on that date) or
> **[UNVERIFIED]** (secondary source, inference, or not checked). Access terms and
> URLs rot — re-verify before building on anything here that has aged.

## The two questions this spike answers

1. What bottom-trawling effort data can we actually get from Global Fishing
   Watch (GFW), and under what terms?
2. Is there an openly redistributable sedimentary organic-carbon dataset for the
   North Sea (the ADR-0003 v1 region)?

**Answer in one line: yes to both — v1 (North Sea) is feasible with clean
licensing, with one scientific caveat (gear classification) and one strategic
constraint (non-commercial licensing on the trawling data).**

---

## 1. Trawling effort — Global Fishing Watch

### Access channels

Two real, free channels [VERIFIED]:

- **Bulk static downloads (recommended for our self-hosted ETL):** the
  "Apparent Fishing Effort" dataset **v3.0 (March 2025 release), years
  2012–2024**, downloadable anonymously from Zenodo
  (DOI [10.5281/zenodo.14982712](https://zenodo.org/records/14982712)) and
  mirrored as public BigQuery tables
  (`global-fishing-watch.fishing_effort_v3.*`). Products:
  - daily fishing hours by **flag state + gear type at 0.01°**
    (`fleet-daily-csvs-100-v3-YYYY.zip`) — the one we want;
  - monthly by flag+gear at 0.1°; daily by MMSI at 0.1°; plus
    `fishing-vessels-v3.csv` (per-vessel characteristics).
  [VERIFIED — file list and README-fleet-v3.txt fetched from Zenodo 2026-08-14]
- **API v3** (`https://gateway.api.globalfishingwatch.org/v3/`), standard since
  2024-04-30 [VERIFIED — GFW's own clients]. `4wings/report` returns gridded
  effort as CSV/GeoTIFF/JSON at `LOW` (0.1°) or `HIGH` (0.01°) resolution,
  filterable by `geartype in ('trawlers')`, over EEZ/MPA regions or a custom
  polygon; `4wings/tile` serves MVT/PNG heatmap tiles for interactive maps
  [VERIFIED — API docs]. **API coverage starts 2017** (bulk files go back to
  2012) [VERIFIED — GFW python-client README]. Token: free self-registration at
  globalfishingwatch.org/our-apis/tokens [VERIFIED]; issue/approval wait time
  unknown [UNVERIFIED]. Rate limits: 50,000 req/day, 1.5M/month; 429 + 24h/30d
  lockout on breach [VERIFIED — license & rate-limits page].

### License — the strategic constraint

- The v3 dataset and the APIs are **CC BY-NC 4.0** (verified programmatically via
  the Zenodo API and GFW's license page) [VERIFIED]. Older claims of CC BY-SA
  applied to earlier dataset versions at best [UNVERIFIED history — flagged].
- Implications: redistribution and derived layers are fine **with attribution,
  non-commercially**. Attribution obligations must be passed to downstream
  users; "Powered by Global Fishing Watch" (or full citation) required; GFW
  logo/name use needs written consent [VERIFIED]. The "compatible with a free
  public atlas" reading is our interpretation of CC BY-NC, not a GFW statement
  [UNVERIFIED as legal advice].
- **Consequence: the Trawl Carbon Atlas must remain non-commercial** while it
  carries GFW-derived layers. This fits the project's goals but is now a
  recorded constraint (ADR-0008).

### The gear-type caveat — the scientific constraint

- **GFW's public taxonomy does NOT distinguish bottom trawlers from midwater
  trawlers.** The v3 class is literally "trawlers: trawlers, all types"; the
  only other bottom-contact class is `dredge_fishing` [VERIFIED — quoted from
  README-fleet-v3.txt]. Finer labels like `otter_twin_trawls` are FAO/EU
  registry vocabulary, not GFW classes [VERIFIED absence in v3 README].
- The literature's workaround (Sala/Pristine Seas lineage): cross-reference GFW
  "trawlers" against official vessel registries (EU Fleet Register, Norway,
  Iceland, Faroes, RFMOs) to strip out midwater/pelagic trawlers; treat the
  remainder as otter trawlers and `dredge_fishing` as towed dredges
  [VERIFIED for their 2025 Europe bottom-trawling preprint; the same method in
  Sala et al. 2021 itself is from secondary summaries — UNVERIFIED].
- ICES publishes a VMS-based bottom-trawl footprint for the North Sea — a
  potential validator or alternative [UNVERIFIED — background knowledge, not
  checked this session].
- **Consequence: "bottom-trawling intensity" in v1 will really be "GFW
  'trawlers' + dredge effort, registry-refined if we implement the
  cross-reference."** The map's honesty layer must say which one it is showing.

---

## 2. Sedimentary organic carbon — North Sea

### The pick: Diesing 2021 (PANGAEA 928272)

- **Citation:** Diesing, M. (2021), PANGAEA,
  DOI [10.1594/PANGAEA.928272](https://doi.pangaea.de/10.1594/PANGAEA.928272);
  supplement to Diesing, Thorsnes & Bjarnadóttir (2021), "Organic carbon
  densities and accumulation rates in surface sediments of the North Sea and
  Skagerrak", *Biogeosciences* 18(6), 2139–2160, DOI 10.5194/bg-18-2139-2021.
  [VERIFIED]
- **Coverage:** full North Sea + Skagerrak — all national sectors, unlike the
  UK-EEZ-only alternatives [VERIFIED].
- **Content/format:** six GeoTIFFs at **500 m** (Lambert Azimuthal Equal-Area):
  mean + total-uncertainty rasters for sedimentation rate (cm/yr), **OC density
  (kg/m³)** and **OC accumulation rate (g/m²/yr)** [VERIFIED]. Per-pixel
  uncertainty rasters are a direct fit for this project's
  never-a-bare-number rule.
- **License: CC-BY-4.0** — redistribution with attribution is clean [VERIFIED].
- **Download:** single anonymous zip, ~53 MB — HTTP 200 confirmed 2026-08-14
  [VERIFIED: https://download.pangaea.de/dataset/928272/files/Diesing_2021.zip].
  (PANGAEA quirk: plain HEAD requests can hit a 503 anti-bot page on some
  datasets; GET works [VERIFIED on the 2024 sibling dataset].)

### Runners-up / v2 extensions

| Dataset | Coverage | Res. | License | Status |
|---|---|---|---|---|
| Smeaton et al. 2021 (DOI 10.7489/12354-1) | UK EEZ + IoM + Channel Is. only | ~500 m–5 m | UK OGL (version [UNVERIFIED]) | ~229 MB zip, HTTP 200 [VERIFIED] |
| Atwood et al. 2020 global stock (Figshare 10.6084/m9.figshare.11956356) | Global | ~1 km | CC BY 4.0 [VERIFIED via Figshare API] | ~1 GB/raster, downloads anonymously [VERIFIED] |
| Diesing 2024 Norwegian margin (PANGAEA 965617) | 54.4–83.3°N | 4 km | CC-BY-4.0 [VERIFIED] | northward v2 path, same lineage |
| Diesing et al. 2017 NW-shelf POC % (PANGAEA 871584) | North Sea/Channel/Celtic | 500 m | CC-BY-3.0 [VERIFIED] | concentration only, not stock |
| MOSAIC v2.0 core database (Zenodo 8322094) | Global points | n/a | "other-open" — terms unclear [VERIFIED listing] | validation use only |
| NN-TOC v1 (Zenodo 11186224) | Global | 5 arcmin | CC-BY-4.0 | 25.6 GB, too heavy/coarse for v1 [VERIFIED] |
| EMODnet Geology | — | — | — | **no OC product yet**; planned for the 2025–2027 phase [VERIFIED] |

### Bonus: Sala et al. 2021's own derived layers are public

Dryad DOI [10.25349/D9N89M](https://datadryad.org/dataset/doi:10.25349/D9N89M),
~79.5 MB, anonymous download, includes `co2_efflux.tif` (their trawling-induced
CO2 efflux raster) and `bottom_trawling_Ia.tif` [VERIFIED URLs/files]. License
was reported as CC0-1.0 by one check but not stated on the page another check
fetched — **re-verify before redistributing** [CONFLICTING/UNVERIFIED]. Either
way it is usable as a comparison layer for benchmarking our Sala-preset
reproduction against the authors' own published raster.

---

## What this spike settles (→ ADR-0008)

1. **v1 scope confirmed: North Sea** (ADR-0003 stands) — the data situation is
   not just adequate but good.
2. **v1 carbon layer: Diesing 2021** (CC-BY-4.0, 500 m, uncertainty included).
3. **v1 effort source: GFW bulk v3 fleet-daily 0.01° CSVs from Zenodo** —
   no API dependency in the ETL; the API (token required) is for later
   interactive/tile features, not the pipeline.
4. **The tool is non-commercial** while GFW-derived layers are aboard
   (CC BY-NC 4.0), with a required attribution stack (GFW + Diesing + per-preset
   citations).

## Follow-ups this spike creates

- [ ] Register a GFW account + API token (needed only when interactive tiles or
      post-2024 data arrive; the ETL needs neither). **User action.**
- [ ] Decide the bottom-trawl isolation strategy: GFW "trawlers"+dredge as-is
      (labeled honestly) vs. registry cross-reference (Sala-style, more work,
      more defensible). Candidate for its own ADR when the ETL slice starts.
- [ ] Re-verify the Dryad license for Sala's `co2_efflux.tif` before any
      redistribution.
- [ ] Spot-check the ICES VMS bottom-trawl footprint as validator [UNVERIFIED
      lead].
