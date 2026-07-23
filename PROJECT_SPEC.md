# Trawl Carbon Atlas

A public, interactive tool mapping the overlap between industrial bottom-trawling grounds and seafloor organic carbon deposition zones — visualizing a live, disputed scientific question rather than presenting a single settled number.

## The core idea

Bottom trawling drags heavy gear across the seafloor, resuspending sediment. Some of the organic carbon buried there mineralizes to CO2 and outgasses. A 2021 Nature paper (Sala et al.) estimated this at 0.6–1.5 petagrams of CO2/year globally — roughly aviation-industry scale. Follow-up research has disputed the magnitude by one to two orders of magnitude, and the science remains actively contested as of 2026. Regional models (e.g. North Sea) have mapped the overlap between trawling grounds and carbon deposition zones rigorously, but no open, global, interactive tool exists that lets a user explore this overlap themselves or compare competing scientific estimates side by side.

This project is not new science. It's a public, honest visualization layer on top of real, disputed research — showing the overlap, showing the uncertainty range explicitly, and citing the competing estimates rather than picking a side.

## Goals

1. Overlay global bottom-trawling intensity against sedimentary organic carbon stock/deposition maps.
2. Let a user toggle between different published reactivity/remineralization assumptions (Sala et al.'s original high estimate vs. more conservative recalculations) and see the resulting CO2-release estimate change.
3. Present this as a credible, citation-backed public resource — usable by conservation orgs, journalists, and policy audiences, not just a personal demo.
4. Support a data-curation workflow so sources, citations, and confidence levels on datasets can be reviewed and maintained over time rather than hardcoded once.

## Data sources (to confirm access details during setup)

- **Trawling intensity**: Global Fishing Watch — public AIS-derived fishing effort / bottom-trawling data, via their API.
- **Sedimentary organic carbon**: published regional and global datasets from the trawling-carbon literature (Sala et al. 2021 global 1km² grid; North Sea regional model data; other published sedimentary OC compilations). Needs a research pass to identify what's redistributable/publicly downloadable vs. request-only.
- **Reactivity/remineralization assumptions**: encode the competing published estimates (Sala et al. high estimate; Hiddink et al. / Epstein et al. conservative recalculations) as named, citable presets rather than a single hardcoded constant.

## Architecture

- **Ingestion / ETL**: Python (GeoPandas, pandas) — pulls AIS trawling data and carbon stock datasets, normalizes to a common grid, loads into PostGIS. Runs as scheduled or on-demand jobs, not a web framework concern.
- **Storage**: PostgreSQL + PostGIS, self-hosted via Docker Compose on a single VM (deliberately not a managed cloud DB — see "Why this stack" below). Row-level security (RLS) gates data by confidence/verification tier if/when a curation workflow is added.
- **Backend**: Django + Django REST Framework.
  - DRF serves the geospatial overlay data and computed CO2-estimate presets to the frontend.
  - Django admin is the curation interface for data sources, citations, and confidence tiers — this is genuinely Django's strong suit, not a bolt-on.
- **Auth**: Keycloak, self-hosted alongside the rest of the stack. Only needed if/when contributor accounts (submitting corrections, saved regions) are added — not required for a read-only public MVP, but the architecture should leave room for it.
- **Frontend**: Mapbox GL JS (or similar WebGL map library) — global map, trawling-intensity and carbon-stock layers, a toggle for reactivity-assumption presets, an uncertainty-range display rather than a single point estimate.
- **Deployment**: Docker Compose on a single VM. No Kubernetes, no managed AWS services — deliberately self-hosted to build that muscle directly (see below).

## Why this stack (context for whoever picks this up)

This project's tech choices aren't just "whatever's easiest" — a few are deliberate:

- **Django over FastAPI**: close to a toss-up technically for a mostly-read geospatial API, but Django admin is a real, natural fit for the data-source/citation curation workflow this project needs, not forced in.
- **Self-hosted Docker Compose over AWS-managed services**: deliberate departure from a cloud-native default, to build genuine single-VM/self-hosted operational experience (Postgres roles/grants, container networking, no managed-service safety net).
- **Keycloak over Auth0**: self-hostable, fits the same non-cloud-native deployment story.
- **Postgres RLS**: used for real, not decoratively — if/when different confidence tiers of data need different visibility.

## Suggested build order

1. **Data exploration spike**: confirm what's actually accessible from Global Fishing Watch's API and identify a usable global or regional sedimentary organic carbon dataset. This determines feasible initial scope (global vs. one well-studied region like the North Sea or a US shelf area).
2. **ETL + PostGIS schema**: get one region's trawling data and one carbon dataset loaded and spatially joined. Prove the overlap query works before building anything else.
3. **Reactivity presets**: encode the 2-3 competing published estimates as named, documented calculation presets against the joined data.
4. **Django + DRF API**: serve the overlay data and preset-driven estimates.
5. **Django admin curation**: data source / citation management.
6. **Frontend map**: static overlay first, then the preset toggle and uncertainty display.
7. **Docker Compose deployment**: get it running self-hosted end to end.
8. **(Later) Keycloak + contributor accounts**: only once there's a real reason for user-submitted content.

## Open questions to resolve early

- Global scope vs. one well-documented region for v1 — global is more impressive but the data situation (especially sedimentary organic carbon) is much better validated regionally (e.g. North Sea).
- Licensing/redistribution terms for the carbon stock datasets — some published research data is request-only or has attribution requirements.
- How to represent uncertainty visually without implying false precision (this is the whole point of the project, so it's worth getting right rather than defaulting to a single choropleth number).

## Non-goals

- Not attempting new oceanographic science or novel carbon-flux modeling — this is a communication/visualization layer on existing, cited, published estimates.
- Not competing with existing whale-strike, ghost-gear, or general fishing-effort tools — those are separately well-covered spaces (see project notes).
