"""Persistence layer: the ETL-owned PostGIS store (ADR-0010).

Sits above the pure domain modules and depends downward only. The schema lives
in schema.sql beside the code that applies it; the honesty rules are enforced
by the database itself as constraints, and the integration tests exercise them
against a real PostGIS.
"""
