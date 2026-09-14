"""Behavioral contract for ``python -m carbon_atlas`` — the data-ops commands.

RIGOR.md standing rule 7: every step that used to be a scratchpad script or a
runbook snippet is a tested command: load a year, compute the footprint, load
the wind-farm zones, measure the zone contrasts, and a backfill that fetches
verified files and runs the lot. Commands are wiring over the tested runners;
these tests pin the wiring, the idempotence, and the honest exit codes.

Written test-first per TDD_CONTRACT.md.
"""

import json
import zipfile
from pathlib import Path

import pytest

from carbon_atlas.cli import main
from carbon_atlas.db.store import (
    latest_footprint_summary,
    list_runs,
    list_wind_farm_zones,
    load_zone_contrast,
)

pytestmark = pytest.mark.integration

_REAL = Path(__file__).parent.parent / "fixtures" / "real"
_CARBON_MEAN = _REAL / "diesing2021" / "OCdensity_quantrf_mean.win60.tif"
_CARBON_UNC = _REAL / "diesing2021" / "OCdensity_quantrf_tot.unc.win60.tif"
_WINDFARMS = _REAL / "emodnet" / "windfarms_polygons.german-bight.geojson"


@pytest.fixture
def data_dir(tmp_path):
    """A data directory holding a 2012 'year zip' built from the real Bight
    fixture under the product's file name."""
    gfw = tmp_path / "gfw"
    gfw.mkdir()
    with zipfile.ZipFile(gfw / "fleet-daily-csvs-100-v3-2012.zip", "w") as archive:
        archive.writestr(
            "day.csv",
            (_REAL / "gfw" / "fleet-daily-100-v3-2012.german-bight-box.csv").read_text(
                encoding="utf-8"
            ),
        )
    return gfw


def _common(test_dsn):
    return [
        "--dsn",
        test_dsn,
        "--carbon-mean",
        str(_CARBON_MEAN),
        "--carbon-uncertainty",
        str(_CARBON_UNC),
    ]


def test_etl_year_loads_a_year_with_the_canonical_provenance_and_is_idempotent(
    conn, test_dsn, data_dir, capsys
):
    rc = main(["etl-year", "2012", "--data-dir", str(data_dir), *_common(test_dsn)])

    assert rc == 0
    (run,) = list_runs(conn)
    assert run.effort_year == 2012
    assert "10.5281/zenodo.14982712" in run.effort_source and "2012" in run.effort_source
    assert "10.1594/PANGAEA.928272" in run.carbon_source
    assert run.cells_mapped == 220 and run.cells_unmapped == 97
    assert f"run {run.id}" in capsys.readouterr().out

    # A second call does not load the year twice.
    rc = main(["etl-year", "2012", "--data-dir", str(data_dir), *_common(test_dsn)])
    assert rc == 0
    assert len(list_runs(conn)) == 1
    assert "already loaded" in capsys.readouterr().out


def test_etl_year_without_the_zip_fails_with_a_named_path_and_nonzero_exit(
    conn, test_dsn, tmp_path, capsys
):
    rc = main(["etl-year", "2013", "--data-dir", str(tmp_path), *_common(test_dsn)])

    assert rc == 2
    err = capsys.readouterr().err
    assert "fleet-daily-csvs-100-v3-2013.zip" in err
    assert list_runs(conn) == ()


def test_footprint_zones_and_zone_contrasts_are_the_runners_and_refresh_idempotently(
    conn, test_dsn, data_dir, capsys
):
    assert main(["etl-year", "2012", "--data-dir", str(data_dir), *_common(test_dsn)]) == 0

    assert main(["footprint", *_common(test_dsn)]) == 0
    assert latest_footprint_summary(conn).years == (2012,)

    assert main(["zones", str(_WINDFARMS), "--region-margin", "1.0", *_common(test_dsn)]) == 0
    assert len(list_wind_farm_zones(conn)) == 4

    assert main(["zone-contrasts", *_common(test_dsn)]) == 0
    (run,) = list_runs(conn)
    assert load_zone_contrast(conn, run.id).cutoff_year == 2011
    assert main(["zone-contrasts", *_common(test_dsn)]) == 0  # nothing left to measure
    assert "0 run" in capsys.readouterr().out


def test_footprint_with_no_runs_exits_nonzero_with_a_message(conn, test_dsn, capsys):
    rc = main(["footprint", *_common(test_dsn)])
    assert rc == 2
    assert "no ETL runs" in capsys.readouterr().err


def test_backfill_fetches_verified_files_then_loads_and_refreshes(
    conn, test_dsn, data_dir, tmp_path, capsys, monkeypatch
):
    """The backfill is: for each year not yet loaded, fetch the year zip and
    verify it against the manifest's MD5, run the ETL, then refresh the
    footprint and zone contrasts once. Here the manifest is a saved record and
    the 'download' is served by a fake opener from a fixture zip."""
    import hashlib

    good_zip = (data_dir / "fleet-daily-csvs-100-v3-2012.zip").read_bytes()
    md5 = hashlib.md5(good_zip).hexdigest()
    record = {
        "files": [
            {
                "key": f"fleet-daily-csvs-100-v3-{year}.zip",
                "size": len(good_zip),
                "checksum": f"md5:{md5}",
                "links": {"self": f"https://zenodo.test/{year}"},
            }
            for year in (2012, 2013)
        ]
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(record), encoding="utf-8")
    served = []

    def fake_opener(url, timeout=None):
        import io

        served.append(url)
        return io.BytesIO(good_zip)

    monkeypatch.setattr("carbon_atlas.cli.urlopen", fake_opener)

    rc = main(
        [
            "backfill",
            "2012",
            "2013",
            "--data-dir",
            str(data_dir),
            "--manifest-file",
            str(manifest),
            *_common(test_dsn),
        ]
    )

    assert rc == 0
    assert served == ["https://zenodo.test/2013"]  # 2012 was already on disk and verified
    years = sorted(run.effort_year for run in list_runs(conn))
    assert years == [2012, 2013]
    assert latest_footprint_summary(conn).years == (2012, 2013)
    out = capsys.readouterr().out
    assert "2012: already verified" in out and "2013: downloaded" in out
    assert "footprint summary" in out
    assert "zone contrasts" not in out  # no zones loaded: nothing to measure, no false claim

    # Idempotent: a second backfill loads nothing and downloads nothing more —
    # but with zones now present, its refresh measures every run against them.
    assert main(["zones", str(_WINDFARMS), "--region-margin", "1.0", *_common(test_dsn)]) == 0
    rc = main(
        [
            "backfill",
            "2012",
            "2013",
            "--data-dir",
            str(data_dir),
            "--manifest-file",
            str(manifest),
            *_common(test_dsn),
        ]
    )
    assert rc == 0
    assert served == ["https://zenodo.test/2013"]
    out = capsys.readouterr().out
    assert "2012: already loaded" in out and "2013: already loaded" in out
    assert "zone contrasts: measured 2 run(s)" in out
    assert len(list_runs(conn)) == 2


def test_unknown_command_and_no_command_exit_with_usage(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["nonsense"])
    assert excinfo.value.code == 2
    with pytest.raises(SystemExit):
        main([])


def test_fetch_year_reads_the_zenodo_record_over_http_and_downloads_verified(
    tmp_path, capsys, monkeypatch
):
    import hashlib
    import io

    payload = b"zip bytes" * 100
    record = {
        "files": [
            {
                "key": "fleet-daily-csvs-100-v3-2020.zip",
                "size": len(payload),
                "checksum": "md5:" + hashlib.md5(payload).hexdigest(),
                "links": {"self": "https://zenodo.test/2020"},
            }
        ]
    }

    def fake_opener(url, timeout=None):
        if url.startswith("https://zenodo.org/api/records/"):
            return io.BytesIO(json.dumps(record).encode())
        return io.BytesIO(payload)

    monkeypatch.setattr("carbon_atlas.cli.urlopen", fake_opener)

    rc = main(["fetch-year", "2020", "--data-dir", str(tmp_path / "gfw")])

    assert rc == 0
    assert (tmp_path / "gfw" / "fleet-daily-csvs-100-v3-2020.zip").read_bytes() == payload
    assert "2020: downloaded" in capsys.readouterr().out

    rc = main(["fetch-year", "2021", "--data-dir", str(tmp_path / "gfw")])
    assert rc == 2
    assert "fleet-daily-csvs-100-v3-2021.zip is not in the Zenodo record" in capsys.readouterr().err


def test_progress_lines_are_flushed_as_they_happen(tmp_path, monkeypatch):
    """A backfill runs for hours with stdout redirected to a log; block
    buffering would hide every progress line until exit (seen 2026-09-10 on
    the first real run). Each line is flushed when printed."""
    import hashlib
    import io
    import sys

    payload = b"zip bytes" * 10
    record = {
        "files": [
            {
                "key": "fleet-daily-csvs-100-v3-2020.zip",
                "size": len(payload),
                "checksum": "md5:" + hashlib.md5(payload).hexdigest(),
                "links": {"self": "https://zenodo.test/2020"},
            }
        ]
    }
    manifest = tmp_path / "record.json"
    manifest.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr("carbon_atlas.cli.urlopen", lambda url, timeout=None: io.BytesIO(payload))

    class Recorder(io.StringIO):
        flushes = 0

        def flush(self):
            Recorder.flushes += 1
            super().flush()

    out = Recorder()
    monkeypatch.setattr(sys, "stdout", out)

    rc = main(
        [
            "fetch-year",
            "2020",
            "--data-dir",
            str(tmp_path / "gfw"),
            "--manifest-file",
            str(manifest),
        ]
    )

    assert rc == 0
    assert "2020: downloaded" in out.getvalue()
    assert Recorder.flushes >= 1
