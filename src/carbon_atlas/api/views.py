"""DRF views for the read-only v1 API."""

from dataclasses import asdict

import psycopg
from django.db import connection
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from carbon_atlas.db.store import list_runs
from carbon_atlas.reactivity.presets import PUBLISHED_PRESETS


def _store_connection() -> psycopg.Connection:
    """The raw psycopg connection under Django's — what the store functions
    speak (ADR-0011: views call the tested store, never an ORM)."""
    connection.ensure_connection()
    return connection.connection


class PresetCatalogView(APIView):
    """The published reactivity presets, verbatim from the pure core.

    Faithful transport of the catalog and its honesty invariants: a derived
    fraction ships with its derivation note, an unquantified atmospheric
    fraction ships as null. No CO2 figures — none exist to serve (ADR-0011).
    """

    def get(self, request: Request) -> Response:
        return Response({"presets": [asdict(preset) for preset in PUBLISHED_PRESETS]})


class RunListView(APIView):
    """Every ETL run's provenance, newest first.

    Provenance is the honesty layer at the API: sources, the ADR-0009 label
    verbatim, and BOTH sides' totals — mapped and unmapped effort alike.
    """

    def get(self, request: Request) -> Response:
        return Response({"runs": [asdict(run) for run in list_runs(_store_connection())]})
