"""Django project configuration for the read-only v1 API (ADR-0011).

Deliberately thin: settings and URL routing only. The API views live in
:mod:`carbon_atlas.api`; every query they run belongs to the tested store
layer below.
"""
