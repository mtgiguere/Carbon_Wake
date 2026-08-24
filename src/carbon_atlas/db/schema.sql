-- ETL-owned schema (ADR-0010). Idempotent: applying it twice is a no-op.
-- The project's honesty rules live here as constraints, not only in Python —
-- this is the last line of defense against a buggy future writer.

CREATE EXTENSION IF NOT EXISTS postgis;

-- One row per ETL run: full provenance, including the ADR-0009 effort-layer
-- label verbatim and BOTH sides' totals (unmapped effort is reported all the
-- way into persistence, never dropped).
CREATE TABLE IF NOT EXISTS etl_run (
    id                      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at              timestamptz NOT NULL DEFAULT now(),
    effort_source           text NOT NULL,
    carbon_source           text NOT NULL,
    effort_layer_label      text NOT NULL,
    cells_mapped            integer NOT NULL CHECK (cells_mapped >= 0),
    cells_unmapped          integer NOT NULL CHECK (cells_unmapped >= 0),
    fishing_hours_mapped    double precision NOT NULL CHECK (fishing_hours_mapped >= 0),
    fishing_hours_unmapped  double precision NOT NULL CHECK (fishing_hours_unmapped >= 0)
);

-- Both sides of the overlap join, one row per 0.01-degree cell per run.
-- Effort is stored PER GEAR CLASS (ADR-0012/0013): the disturbed-carbon model
-- prices the classes differently. NULL in a gear column means "no record of
-- this gear here" — a different claim from a recorded 0.0. The total is a
-- GENERATED column, so it can never disagree with its parts. A cell is either
-- fully mapped (mean AND uncertainty) or fully unmapped (neither) — the
-- never-half-a-pair rule as a table constraint. Adding a gear class is an ADR
-- plus a schema change, by design (the ADR-0009 inclusion set is pinned).
CREATE TABLE IF NOT EXISTS overlap_cell (
    run_id                        bigint NOT NULL REFERENCES etl_run (id) ON DELETE CASCADE,
    lat_index                     integer NOT NULL CHECK (lat_index BETWEEN -9000 AND 8999),
    lon_index                     integer NOT NULL CHECK (lon_index BETWEEN -18000 AND 17999),
    fishing_hours_trawlers        double precision CHECK (fishing_hours_trawlers >= 0),
    fishing_hours_dredge_fishing  double precision CHECK (fishing_hours_dredge_fishing >= 0),
    fishing_hours                 double precision GENERATED ALWAYS AS (
        coalesce(fishing_hours_trawlers, 0) + coalesce(fishing_hours_dredge_fishing, 0)
    ) STORED,
    oc_density_mean               double precision CHECK (oc_density_mean >= 0),
    oc_density_uncertainty        double precision CHECK (oc_density_uncertainty >= 0),
    geom                          geometry(Polygon, 4326) NOT NULL,
    PRIMARY KEY (run_id, lat_index, lon_index),
    CHECK ((oc_density_mean IS NULL) = (oc_density_uncertainty IS NULL)),
    CHECK (fishing_hours_trawlers IS NOT NULL OR fishing_hours_dredge_fishing IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS overlap_cell_geom_idx ON overlap_cell USING gist (geom);
