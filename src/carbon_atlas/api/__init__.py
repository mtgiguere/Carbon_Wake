"""The read-only v1 API (ADR-0011).

Views are transport, nothing more: the preset catalog comes verbatim from the
pure reactivity core, and data endpoints call the tested store layer over the
raw psycopg connection. No query logic lives here — an API test failing means
the HTTP contract broke, never the science.
"""
