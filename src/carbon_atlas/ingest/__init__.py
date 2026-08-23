"""Ingest layer: parsers for the real external formats the ETL consumes.

This layer sits above the pure domain packages and depends downward only
(docs/ARCHITECTURE.md §2). Everything here is Blind-spot-A territory: each
parser has an @integration test against a committed verbatim sample of the
real published format, because a self-authored fixture can only prove a parser
agrees with itself.
"""
