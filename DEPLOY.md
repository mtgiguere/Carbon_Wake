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

Alternatively, run the ETL on the VM itself (needs the GFW year zip and the
Diesing rasters downloaded there — see docs/DATA_SPIKE.md for sources; ~6
minutes per year once downloaded).

## 2b. Recompute the cumulative footprint (after any new year lands)

The footprint headline (ADR-0017) is an offline summary over every stored
year; it does not update itself. After loading or adding runs, on the machine
holding the Diesing rasters (the dev box, or the VM after an on-VM ETL):

```sh
python - <<'PY'
from pathlib import Path
import psycopg
from carbon_atlas.etl import run_footprint_summary
d = Path("data/diesing2021/Diesing_2021")
with psycopg.connect("postgresql://carbon_atlas:carbon_atlas_dev@localhost:5434/carbon_atlas") as conn:
    print("footprint summary id", run_footprint_summary(
        conn=conn,
        carbon_mean=d / "OCdensity_quantrf_mean.tif",
        carbon_uncertainty=d / "OCdensity_quantrf_tot.unc.tif",
    ))
    conn.commit()
PY
```

(Unset `PROJ_LIB` first on a Windows dev box — CONTRIBUTING.md.) Executed
2026-09-08 over five years / 1.43 M cells: 44 seconds. Then ship the dump as
in step 2 — `footprint_summary` is in the table list above. A stale summary
is visible, not silent: the panel names the years it covers.

## 2c. Load the reference zones and measure them (once, then after new years)

Offshore wind farms (ADR-0018) come from EMODnet's WFS as one GeoJSON file
(CC-BY 4.0; ~1.8 MB, Europe-wide — the loader scopes it to the atlas region):

```sh
mkdir -p data/reference
curl -sS -L --fail -o data/reference/emodnet_windfarms_polygons_$(date +%F).geojson   "https://ows.emodnet-humanactivities.eu/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=emodnet:windfarmspoly&OUTPUTFORMAT=application/json&SRSNAME=EPSG:4326"
python - <<'PY'
from pathlib import Path
import psycopg
from carbon_atlas.etl import run_wind_farm_zones, run_zone_contrasts
d = Path("data/diesing2021/Diesing_2021")
geojson = sorted(Path("data/reference").glob("emodnet_windfarms_polygons_*.geojson"))[-1]
with psycopg.connect("postgresql://carbon_atlas:carbon_atlas_dev@localhost:5434/carbon_atlas") as conn:
    print("zones stored", run_wind_farm_zones(
        conn, geojson=geojson,
        carbon_mean=d / "OCdensity_quantrf_mean.tif",
        carbon_uncertainty=d / "OCdensity_quantrf_tot.unc.tif",
    ))
    print("runs measured", run_zone_contrasts(conn))   # idempotent: only unmeasured runs
    conn.commit()
PY
```

Executed 2026-09-10 on the dev database: 169 zones in 2 s, six runs measured
in 8 s. Re-run the Python step after every new year (it measures only runs
without a stored contrast); re-run both steps to refresh the EMODnet snapshot
(replacing zones does NOT invalidate stored contrasts — delete
`zone_contrast_summary` rows first if the polygons changed).

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
