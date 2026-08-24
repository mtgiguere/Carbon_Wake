"""Parser for GFW fleet-daily-100-v3 CSVs (apparent fishing effort, 0.01 deg).

Faithful, streaming transcription of rows into EffortRecords — gear filtering
is the aggregation layer's decision (the ADR-0009 seam), not the parser's.

The format contract is strict on what we consume and indifferent to the rest:
a missing consumed column, an empty consumed value, or an off-grid coordinate
refuses the file with the line number, because every silent alternative
(defaulting, skipping, snapping) quietly corrupts the effort layer. GFW's
schema marks all fields NULLABLE, but the real product contains no empty
values (385k-row scan, 2026-08-23) — so an empty value is format drift, and
format drift must be a loud stop, not a guess.
"""

import csv
import io
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path

from carbon_atlas.effort.aggregate import EffortRecord
from carbon_atlas.effort.grid import cell_from_lower_left

#: The columns this parser reads. Other columns (date, flag, hours,
#: mmsi_present) pass through unexamined and may change freely.
CONSUMED_COLUMNS = ("cell_ll_lat", "cell_ll_lon", "geartype", "fishing_hours")


def parse_fleet_daily(lines: Iterable[str]) -> Iterator[EffortRecord]:
    """EffortRecords from fleet-daily CSV ``lines`` (header first), lazily.

    Accepts any iterable of text lines — an open file, or a zip member wrapped
    in a TextIOWrapper — so a year of dailies streams without ever being fully
    in memory. Raises ``ValueError`` naming the missing column or the offending
    line for anything that violates the format contract above.
    """
    reader = csv.DictReader(lines)
    if reader.fieldnames is None:
        raise ValueError("no header line: not a fleet-daily CSV")
    missing = [column for column in CONSUMED_COLUMNS if column not in reader.fieldnames]
    if missing:
        raise ValueError(f"fleet-daily header is missing consumed column(s): {missing}")

    for row in reader:
        try:
            values = {}
            for column in CONSUMED_COLUMNS:
                value = row[column]
                if not value:
                    raise ValueError(f"empty value in consumed column {column!r}")
                values[column] = value
            yield EffortRecord(
                cell=cell_from_lower_left(
                    float(values["cell_ll_lat"]), float(values["cell_ll_lon"])
                ),
                geartype=values["geartype"],
                fishing_hours=float(values["fishing_hours"]),
            )
        except ValueError as exc:
            raise ValueError(f"line {reader.line_num}: {exc}") from exc


def iter_fleet_daily_zip(zip_path: Path) -> Iterator[EffortRecord]:
    """EffortRecords from every daily CSV member of a fleet-daily year zip.

    Streams member by member (the real zips are gigabytes; nothing is ever
    fully in memory) in sorted-name order, so a run over the same archive is
    reproducible regardless of how the zip was assembled. A zip holding no CSV
    members is the wrong archive and raises — an empty year that looks like an
    ocean nobody fished must not exist.
    """
    with zipfile.ZipFile(zip_path) as archive:
        names = sorted(name for name in archive.namelist() if name.endswith(".csv"))
        if not names:
            raise ValueError(f"no CSV members in {zip_path}")
        for name in names:
            with archive.open(name) as member:
                yield from parse_fleet_daily(io.TextIOWrapper(member, encoding="utf-8"))
