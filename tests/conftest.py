"""Live-PostGIS fixtures for the db integration tests.

These tests need a real PostGIS (docker compose up -d locally; a service
container in CI) — the schema's constraints ARE the behavior under test, and
only the real database can verify them. No database -> the tests FAIL, they do
not skip: a skipped honesty gate is a hollow gate (TDD_CONTRACT.md Bug #5).

The tests run in their OWN database (`carbon_atlas_test`, created on demand on
the same server), never in the working database — a test suite that truncates
real ETL runs between tests is a data-loss bug, not isolation. (The API tests
get the same protection from pytest-django's separate test database.)
"""

import os

import psycopg
import pytest

_DEFAULT_DSN = "postgresql://carbon_atlas:carbon_atlas_dev@localhost:5434/carbon_atlas"
_TEST_DBNAME = "carbon_atlas_test"


@pytest.fixture(scope="session")
def db_conn():
    from psycopg import conninfo, errors

    from carbon_atlas.db.store import apply_schema

    working_dsn = os.environ.get("CARBON_ATLAS_DB_URL", _DEFAULT_DSN)
    with psycopg.connect(working_dsn, autocommit=True) as admin:
        try:
            admin.execute(f'CREATE DATABASE "{_TEST_DBNAME}"')
        except errors.DuplicateDatabase:
            pass

    test_dsn = conninfo.make_conninfo(working_dsn, dbname=_TEST_DBNAME)
    conn = psycopg.connect(test_dsn, autocommit=True)
    # Rebuild from schema.sql every session: the test database must always be
    # exactly what a fresh install gets, immune to pre-1.0 schema evolution
    # (ADR-0013: recreate, don't migrate).
    conn.execute("DROP TABLE IF EXISTS overlap_cell; DROP TABLE IF EXISTS etl_run")
    apply_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def conn(db_conn):
    """A clean-slate connection: both ETL tables emptied before each test."""
    db_conn.execute("TRUNCATE etl_run RESTART IDENTITY CASCADE")
    return db_conn
