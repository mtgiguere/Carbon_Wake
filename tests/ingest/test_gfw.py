"""Behavioral contract for the GFW fleet-daily CSV parser.

The parser turns fleet-daily-100-v3 CSV lines into EffortRecords. Two kinds of
tests, per docs/ARCHITECTURE.md §5:

- Unit tests with self-authored lines specify the contract: what a row becomes,
  and that format drift (missing column, empty value, wrong grid) fails loudly
  instead of guessing. GFW's schema marks every field NULLABLE, but a 385k-row
  scan of the real 2012 product found zero empty values — so an empty value is
  treated as format drift, not as a case to silently invent semantics for.
- An @integration test parses a committed VERBATIM head of a real published
  day file (tests/fixtures/real/gfw/), because a self-authored fixture can only
  prove the parser agrees with itself (Blind spot A).

Written test-first per TDD_CONTRACT.md.
"""

import math
from pathlib import Path

import pytest

from carbon_atlas.effort.aggregate import aggregate_fishing_hours
from carbon_atlas.effort.grid import GridCell
from carbon_atlas.ingest.gfw import parse_fleet_daily

_HEADER = "date,cell_ll_lat,cell_ll_lon,flag,geartype,hours,fishing_hours,mmsi_present"

_REAL_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "real"
    / "gfw"
    / "fleet-daily-100-v3-2012-02-04.head500.csv"
)


def test_a_row_becomes_an_effort_record_with_snapped_cell_and_float_hours():
    """One fleet-day row yields one record: the corner floats snapped to the
    exact cell, geartype as-is, fishing_hours parsed to float."""
    lines = [_HEADER, "2012-02-04,55.55,3.01,GBR,trawlers,1.4472,0.75,1"]

    records = list(parse_fleet_daily(lines))

    assert len(records) == 1
    assert records[0].cell == GridCell(lat_index=5555, lon_index=301)
    assert records[0].geartype == "trawlers"
    assert records[0].fishing_hours == 0.75


def test_all_gear_classes_pass_through_unfiltered():
    """Parsing is faithful transcription — gear filtering is the aggregation
    layer's decision (the ADR-0009 seam), not the parser's."""
    lines = [
        _HEADER,
        "2012-02-04,55.55,3.01,GBR,purse_seines,2.0,1.5,1",
        "2012-02-04,55.55,3.01,GBR,trawlers,2.0,0.5,1",
    ]

    records = list(parse_fleet_daily(lines))

    assert [r.geartype for r in records] == ["purse_seines", "trawlers"]


def test_a_header_only_file_yields_no_records():
    """An empty day (header, no rows) is valid input meaning no effort."""
    assert list(parse_fleet_daily([_HEADER])) == []


def test_a_missing_consumed_column_fails_loudly_naming_it():
    """If GFW renames or drops a column we consume, the parser must refuse the
    whole file and say which column vanished — never limp along on defaults."""
    header_without_geartype = "date,cell_ll_lat,cell_ll_lon,flag,hours,fishing_hours,mmsi_present"

    with pytest.raises(ValueError, match="geartype"):
        list(parse_fleet_daily([header_without_geartype, "2012-02-04,55.55,3.01,GBR,2.0,1.5,1"]))


def test_input_without_any_header_fails_loudly():
    """No lines at all means we cannot even check the format — refuse."""
    with pytest.raises(ValueError):
        list(parse_fleet_daily([]))


def test_an_empty_value_in_a_consumed_field_fails_loudly_with_the_line_number():
    """The schema says NULLABLE but the real product contains no empty values
    (385k-row scan, 2026-08-23). If one ever appears we do not know what it
    means, so inventing 0.0 (or skipping the row) would silently corrupt the
    layer. Refuse, and say where."""
    lines = [
        _HEADER,
        "2012-02-04,55.55,3.01,GBR,trawlers,1.0,0.5,1",
        "2012-02-04,55.56,3.01,GBR,trawlers,1.0,,1",
    ]

    with pytest.raises(ValueError, match="line 3"):
        list(parse_fleet_daily(lines))


def test_unconsumed_fields_may_be_empty_without_failing():
    """Strictness is scoped to what we consume: an empty flag (a field we never
    read) must not kill the ETL."""
    lines = [_HEADER, "2012-02-04,55.55,3.01,,trawlers,1.0,0.5,1"]

    records = list(parse_fleet_daily(lines))

    assert len(records) == 1


def test_a_wrong_grid_coordinate_fails_with_the_line_number():
    """A corner not on the 0.01-degree grid is a wrong-format file; the grid
    module raises, and the parser adds WHERE so a 25k-row file is debuggable."""
    lines = [
        _HEADER,
        "2012-02-04,55.55,3.01,GBR,trawlers,1.0,0.5,1",
        "2012-02-04,55.555,3.01,GBR,trawlers,1.0,0.5,1",
    ]

    with pytest.raises(ValueError, match="line 3"):
        list(parse_fleet_daily(lines))


def test_parsing_is_lazy_a_generator_not_a_list():
    """A year of dailies is millions of rows; the parser must stream. Taking
    one record from a malformed-later file proves no eager full read happens."""
    lines = iter([_HEADER, "2012-02-04,55.55,3.01,GBR,trawlers,1.0,0.5,1", "garbage"])

    records = parse_fleet_daily(lines)

    assert next(records).fishing_hours == 0.5  # the bad line was never reached


# --- Reality (Blind spot A) --------------------------------------------------


@pytest.mark.integration
def test_real_published_day_file_parses_completely_and_matches_ground_truth():
    """The committed verbatim head of a real GFW day file parses end to end,
    and the numbers agree with ground truth computed independently from the
    raw CSV at fixture-extraction time (see fixtures/real/gfw/README.md).

    This is the test that catches the assumption a self-authored fixture
    cannot: that GFW's actual header, quoting, and value formats are what the
    parser believes they are."""
    with _REAL_FIXTURE.open(encoding="utf-8") as f:
        records = list(parse_fleet_daily(f))

    assert len(records) == 500
    assert records[0].cell == GridCell(lat_index=-5515, lon_index=-5997)
    assert records[0].geartype == "trawlers"
    assert records[0].fishing_hours == 0.0

    totals = aggregate_fishing_hours(records)
    included_hours = sum(totals.values())
    assert sum(1 for r in records if r.geartype == "trawlers") == 177
    assert math.isclose(included_hours, 61.8818, rel_tol=1e-9)
