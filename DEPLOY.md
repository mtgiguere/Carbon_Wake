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
    --data-only -t etl_run -t overlap_cell > atlas_data.sql   # ~90 MB for 2012
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

## 3. Verify like we do

```sh
curl -s https://your-domain/api/runs/           # run list with provenance
curl -s -o /dev/null -w "%{http_code} %{size_download}\n" \
    https://your-domain/api/runs/2/tiles/5/16/10.mvt   # ~200 KB, sub-second
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
