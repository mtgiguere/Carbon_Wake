"""Fixtures for API tests against the Django test database.

pytest-django creates a test database on the same PostGIS server the rest of
the suite uses; the ETL-owned tables in it come from the same schema.sql the
ETL applies (ADR-0010/0011) — there are no migrations for them. Tests seed
through the RAW psycopg connection underneath Django's connection, so the
seeded rows live inside the test transaction and roll back with it, and the
views (reading over that same connection) see exactly what was seeded.
"""

import pytest


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    from django.db import connection

    from carbon_atlas.db.store import apply_schema

    with django_db_blocker.unblock():
        connection.ensure_connection()
        apply_schema(connection.connection)


@pytest.fixture
def raw_conn(db):
    """The psycopg connection under Django's — the one the store functions
    (and the views, per ADR-0011) speak to."""
    from django.db import connection

    connection.ensure_connection()
    return connection.connection
