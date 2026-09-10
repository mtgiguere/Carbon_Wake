# Deploying the Trawl Carbon Atlas

> Every step below was executed against a real local instance of this exact
> stack before being written down (first-run before publish, RIGOR.md). The
> stack: PostGIS + the web image (gunicorn/WhiteNoise) + Caddy (automatic
> TLS), per PROJECT_SPEC's deliberate single-VM, no-managed-services choice.

## What you need

- A small VM (2 GB RAM is plenty at portfolio traffic) with Docker + the
  compose plugin, ports 80/443 open.
- Optionally a domain with an A record pointing at the VM (Caddy then gets
  its Let's Encrypt certificate automatically). Without one, the stack
  serves plain HTTP on the VM's IP.

## 1. On the VM

```sh
git clone https://github.com/mtgiguere/Carbon_Wake.git && cd Carbon_Wake
cat > .env <<'ENV'
CARBON_ATLAS_DOMAIN=atlas.example.org     # or ":80" for IP-only, no TLS
CARBON_ATLAS_SECRET_KEY=<long random string>
CARBON_ATLAS_DB_PASSWORD=<strong password>
ENV
docker compose -f docker-compose.prod.yml up -d --build
```

The web entrypoint applies the idempotent schema (and ANALYZE) on boot, so a
fresh stack immediately serves the honest empty state ("no ETL runs yet").

## 2. Ship the data

On the machine that ran the ETL (dev database on port 5434):

```sh
docker exec carbon_wake-postgis-1 pg_dump -U carbon_atlas -d carbon_atlas \
    --data-only -t etl_run -t overlap_cell -t footprint_summary     -t reference_zone -t zone_contrast_summary > atlas_data.sql   # ~90 MB/year
scp atlas_data.sql you@vm:Carbon_Wake/
```

On the VM:

```sh
docker exec -i carbon_wake-postgis-1 psql -q -U carbon_atlas -d carbon_atlas < atlas_data.sql
docker compose -f docker-compose.prod.yml restart web   # entrypoint re-runs ANALYZE
```

**Do not skip the restart/ANALYZE**: a freshly restored table has no planner
statistics, the first tile queries seq-scan 371k rows, blow past gunicorn's
timeout, and the map renders empty. (Found the hard way; see RIGOR.md.)

Alternatively, run the data-ops commands on the VM itself (step 2b; needs the
Diesing rasters downloaded there — docs/DATA_SPIKE.md; ~6–45 minutes per year
depending on the year's size and the machine).

## 2b. The data-ops commands (RIGOR.md rule 7: tested, in the repo)

Every data step is a `python -m carbon_atlas` command — the same code the test
suite exercises, with the publisher's MD5 checked on every download. All take
`--dsn` (default `$CARBON_ATLAS_DB_URL`, else the dev database), `--data-dir`
(default `data/gfw`), and `--carbon-mean` / `--carbon-uncertainty` (default the
Diesing rasters under `data/diesing2021/Diesing_2021`). Unset `PROJ_LIB` first
on a Windows dev box (CONTRIBUTING.md).

```sh
python -m carbon_atlas backfill 2012 2024       # fetch (MD5-verified) + load every missing year,
                                                # then refresh the footprint and zone contrasts
python -m carbon_atlas fetch-year 2017          # one year zip, verified against Zenodo's record
python -m carbon_atlas etl-year 2017            # load one year already on disk (idempotent)
python -m carbon_atlas footprint                # recompute the cumulative footprint (ADR-0017)
python -m carbon_atlas zones data/reference/emodnet_windfarms_polygons_<date>.geojson
                                                # (re)load wind-farm reference zones (ADR-0018)
python -m carbon_atlas zone-contrasts           # measure runs not yet measured (idempotent)
```

The wind-farm polygons come from EMODnet's WFS as one GeoJSON file (CC-BY 4.0;
~1.8 MB Europe-wide — the loader scopes it to the atlas region):

```sh
mkdir -p data/reference
curl -sS -L --fail -o data/reference/emodnet_windfarms_polygons_$(date +%F).geojson \
  "https://ows.emodnet-humanactivities.eu/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=emodnet:windfarmspoly&OUTPUTFORMAT=application/json&SRSNAME=EPSG:4326"
```

Notes. A failed download or a missing file exits 2 with the reason on stderr;
a year already loaded is skipped, never duplicated. Replacing the zones does
NOT invalidate stored contrasts — delete `zone_contrast_summary` rows first
if the polygons changed. A stale footprint is visible, not silent: the panel
names the years it covers. First-run: `etl-year`, `footprint`, `zones`, and
`zone-contrasts` were executed against the dev database on 2026-09-10 (see the
CLI's integration tests for the same sequence against the test database).

## 3. Verify like we do

```sh
curl -s https://your-domain/api/runs/           # run list with provenance
curl -s -o /dev/null -w "%{http_code} %{size_download}\n" \
    https://your-domain/api/runs/2/tiles/5/16/10.mvt   # ~200 KB, sub-second
curl -s https://your-domain/api/footprint/      # the bracket, or 404 until step 2b has run
curl -s https://your-domain/api/zones/wind-farms/ | head -c 300   # zones GeoJSON (count 0 until 2c)
```

Then open the site and drag the slider. If the map is empty but the panel
has numbers, it is almost certainly the ANALYZE step above.

## Updating

```sh
git pull && docker compose -f docker-compose.prod.yml up -d --build
```

## Notes

- The atlas must remain non-commercial while it carries GFW-derived layers
  (CC BY-NC 4.0, ADR-0008); the attribution stack renders on the page.
- Low-zoom tiles are 0.1-degree aggregates (~200 KB); per-cell tiles from z8.
- No auth surface exists: the API is read-only GETs (ADR-0011).
