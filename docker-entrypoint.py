"""Container entrypoint: apply the idempotent schema, then serve.

A fresh stack must serve the honest empty state ("no ETL runs yet"), not a
500 on a missing table — the schema is the store's own apply-then-write
design (ADR-0010), safe to run on every boot.
"""

import os
import sys

import psycopg

from carbon_atlas.db.store import apply_schema

with psycopg.connect(os.environ["CARBON_ATLAS_DB_URL"], autocommit=True) as conn:
    apply_schema(conn)
    # A freshly restored table has no planner statistics; the first tile
    # queries then seq-scan 371k rows, blow past gunicorn's timeout, and the
    # map renders empty (caught by first-run against this very stack).
    # ANALYZE is idempotent and takes about a second.
    conn.execute("ANALYZE")
print("schema applied and analyzed; starting gunicorn", flush=True)
os.execvp(sys.argv[1], sys.argv[1:])
