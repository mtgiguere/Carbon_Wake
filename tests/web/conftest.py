"""Fixtures for the browser-driven page tests.

These tests run against ``live_server`` + ``transactional_db``. pytest-django's
flush between transactional tests covers Django-managed tables only — and the
ETL-owned tables (ADR-0010: raw SQL, no models) are not among them, so a run
or footprint summary seeded by one test would leak into the next and, for
instance, make a "no summary computed" test see the previous test's summary.
Every transactional page test therefore starts from empty ETL tables.
"""

import pytest


@pytest.fixture(autouse=True)
def _empty_etl_tables(request):
    if "transactional_db" not in request.fixturenames:
        yield
        return
    request.getfixturevalue("transactional_db")
    from django.db import connection

    from carbon_atlas.db.store import apply_schema

    connection.ensure_connection()
    apply_schema(connection.connection)
    connection.connection.execute(
        "TRUNCATE etl_run RESTART IDENTITY CASCADE; TRUNCATE footprint_summary RESTART IDENTITY"
    )
    yield
