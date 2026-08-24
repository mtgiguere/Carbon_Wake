"""HTTP contract for the preset catalog endpoint.

The API's job here is faithful transport of the pure catalog: every published
preset with its key, label, fraction, citation, additionality flag, and — the
honesty invariants — a derived fraction always ships its derivation note, and
an unquantified atmospheric fraction ships as null, never as a number.

Per ADR-0011 the API serves NO CO2 figures: no disturbed-carbon model is
encoded yet, so there is nothing citable to serve.

Written test-first per TDD_CONTRACT.md.
"""

import pytest

from carbon_atlas.reactivity.presets import PUBLISHED_PRESETS


@pytest.fixture
def presets_payload(client):
    response = client.get("/api/presets/")
    assert response.status_code == 200
    return response.json()


def test_every_published_preset_is_served_keyed_and_cited(presets_payload):
    """The catalog comes through complete — same keys as the pure core, each
    entry carrying its label, fraction, and citation."""
    by_key = {p["key"]: p for p in presets_payload["presets"]}

    assert set(by_key) == {p.key for p in PUBLISHED_PRESETS}
    sala = by_key["sala_2021"]
    assert sala["remineralization_fraction"] == 0.297
    assert "10.1038/s41586-021-03371-z" in sala["citation"]
    assert sala["accounts_for_additionality"] is False


def test_a_derived_fraction_always_ships_with_its_derivation_note(presets_payload):
    """The quoted-vs-derived rule crosses the wire: Hiddink's inferred
    fractions carry their derivation; Sala's quoted one carries null."""
    by_key = {p["key"]: p for p in presets_payload["presets"]}

    assert by_key["sala_2021"]["derivation"] is None
    assert "inferred" in by_key["hiddink_2023_low"]["derivation"].lower()
    assert "inferred" in by_key["hiddink_2023_high"]["derivation"].lower()


def test_an_unquantified_atmospheric_fraction_is_null_not_a_number(presets_payload):
    """Sala 2021 called the aqueous-to-atmosphere fraction 'unknown'; the API
    must say null — serializing it as 0 (or anything) would invent a figure."""
    by_key = {p["key"]: p for p in presets_payload["presets"]}

    assert by_key["sala_2021"]["atmospheric_fraction"] is None
    assert by_key["atwood_2024_low"]["atmospheric_fraction"] == 0.55


def test_the_catalog_serves_no_co2_figures(presets_payload):
    """ADR-0011: until a citable disturbed-carbon model is encoded, no field
    anywhere in this payload may claim to be a CO2 quantity. (Citation TEXT
    may mention CO2 — paper titles do; field NAMES may not.)"""

    def field_names(value):
        if isinstance(value, dict):
            for key, inner in value.items():
                yield key
                yield from field_names(inner)
        elif isinstance(value, list):
            for inner in value:
                yield from field_names(inner)

    assert not [name for name in field_names(presets_payload) if "co2" in name.lower()]
