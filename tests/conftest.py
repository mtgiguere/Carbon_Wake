"""Live-PostGIS fixtures for the db integration tests.

These tests need a real PostGIS (docker compose up -d locally; a service
container in CI) — the schema's constraints ARE the behavior under test, and
only the real database can verify them. No database -> the tests FAIL, they do
not skip: a skipped honesty gate is a hollow gate (TDD_CONTRACT.md Bug #5).
"""

import os

import psycopg
import pytest

_DEFAULT_DSN = "postgresql://carbon_atlas:carbon_atlas_dev@localhost:5434/carbon_atlas"


@pytest.fixture(scope="session")
def db_conn():
    from carbon_atlas.db.store import apply_schema

    conn = psycopg.connect(os.environ.get("CARBON_ATLAS_DB_URL", _DEFAULT_DSN), autocommit=True)
    apply_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def conn(db_conn):
    """A clean-slate connection: both ETL tables emptied before each test."""
    db_conn.execute("TRUNCATE etl_run RESTART IDENTITY CASCADE")
    return db_conn
