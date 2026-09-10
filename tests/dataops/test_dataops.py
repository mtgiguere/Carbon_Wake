"""Behavioral contract for data operations: manifests, checksums, verified
downloads (RIGOR.md standing rule 7 — data-ops code is product code).

Everything that bit the 2026-09-08 backfill is a test here: a byte count is
not verification (only the publisher's MD5 is); a checksum list with Windows
carriage returns must still parse; an HTTP error body must never become a
"downloaded" file; a mismatching file is deleted and fetched afresh, never
resumed; a file that already verifies is not downloaded again.

Written test-first per TDD_CONTRACT.md.
"""

import hashlib
import io
import json
import urllib.error

import pytest

from carbon_atlas.dataops import (
    CARBON_SOURCE_TEXT,
    ChecksumError,
    ZenodoFile,
    download,
    effort_source_text,
    fetch_verified,
    fleet_daily_key,
    parse_zenodo_manifest,
    verify_md5,
)

_PAYLOAD = b"not really a zip, but bytes are bytes\n" * 1000
_MD5 = hashlib.md5(_PAYLOAD).hexdigest()  # MD5 is what Zenodo publishes


def _record(files):
    return {
        "id": 14982712,
        "files": [
            {
                "key": key,
                "size": size,
                "checksum": checksum,
                "links": {"self": f"https://zenodo.org/api/records/14982712/files/{key}/content"},
            }
            for key, size, checksum in files
        ],
    }


# ---------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------


def test_the_manifest_yields_each_files_key_size_md5_and_url():
    manifest = parse_zenodo_manifest(
        _record(
            [
                (
                    "fleet-daily-csvs-100-v3-2016.zip",
                    807072405,
                    "md5:c06de397e3e075fd94eae5a90e144e15",
                )
            ]
        )
    )

    assert manifest["fleet-daily-csvs-100-v3-2016.zip"] == ZenodoFile(
        key="fleet-daily-csvs-100-v3-2016.zip",
        size=807072405,
        md5="c06de397e3e075fd94eae5a90e144e15",
        url="https://zenodo.org/api/records/14982712/files/fleet-daily-csvs-100-v3-2016.zip/content",
    )


def test_a_checksum_with_a_trailing_carriage_return_still_parses():
    """The 2026-09-08 incident: a list written on Windows carried '\\r' on every
    hash and nothing could ever match. Whitespace around the hash is not data."""
    manifest = parse_zenodo_manifest(
        _record([("a.zip", 1, "md5:c06de397e3e075fd94eae5a90e144e15\r")])
    )
    assert manifest["a.zip"].md5 == "c06de397e3e075fd94eae5a90e144e15"


def test_a_non_md5_checksum_is_refused_naming_the_algorithm():
    with pytest.raises(ValueError, match="sha256"):
        parse_zenodo_manifest(_record([("a.zip", 1, "sha256:abcd")]))


def test_a_malformed_md5_is_refused():
    with pytest.raises(ValueError, match=r"a\.zip"):
        parse_zenodo_manifest(_record([("a.zip", 1, "md5:not-hex")]))


def test_the_fleet_daily_key_names_the_product_file():
    assert fleet_daily_key(2016) == "fleet-daily-csvs-100-v3-2016.zip"


def test_the_provenance_texts_name_the_sources_the_runs_carry():
    """The stored runs' effort_source / carbon_source strings live in code, not
    in a shell script: DOI, license, resolution, and the year."""
    text = effort_source_text(2016)
    assert "Global Fishing Watch" in text and "v3.0" in text and "2016" in text
    assert "10.5281/zenodo.14982712" in text and "CC BY-NC 4.0" in text
    assert "Diesing 2021" in CARBON_SOURCE_TEXT and "10.1594/PANGAEA.928272" in CARBON_SOURCE_TEXT


# ---------------------------------------------------------------------------
# Checksums and downloads
# ---------------------------------------------------------------------------


def test_verify_md5_streams_the_file_and_compares_case_insensitively(tmp_path):
    path = tmp_path / "f.zip"
    path.write_bytes(_PAYLOAD)
    assert verify_md5(path, _MD5) is True
    assert verify_md5(path, _MD5.upper()) is True
    assert verify_md5(path, "0" * 32) is False
    assert verify_md5(tmp_path / "missing.zip", _MD5) is False


class _FakeOpener:
    """An injectable urlopen: a queue of responses, each either bytes to serve
    or an exception to raise. Records every URL asked for."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.urls = []

    def __call__(self, url, timeout=None):
        self.urls.append(url)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return io.BytesIO(response)


def _http_error(code):
    return urllib.error.HTTPError(
        "https://x", code, "Gateway Time-out", {}, io.BytesIO(b"<html>504</html>")
    )


def test_download_writes_to_a_part_file_and_renames_only_when_complete(tmp_path):
    dest = tmp_path / "f.zip"
    opener = _FakeOpener(_PAYLOAD)

    download("https://x/f", dest, opener=opener)

    assert dest.read_bytes() == _PAYLOAD
    assert not (tmp_path / "f.zip.part").exists()
    assert opener.urls == ["https://x/f"]


def test_an_http_error_body_never_becomes_a_file(tmp_path):
    """The 504 page that curl once saved as a 92-byte 'zip'."""
    dest = tmp_path / "f.zip"

    with pytest.raises(urllib.error.HTTPError):
        download("https://x/f", dest, opener=_FakeOpener(_http_error(504)))

    assert not dest.exists() and not (tmp_path / "f.zip.part").exists()


def _file():
    return ZenodoFile(key="f.zip", size=len(_PAYLOAD), md5=_MD5, url="https://x/f")


def test_fetch_verified_downloads_and_verifies(tmp_path):
    dest = tmp_path / "f.zip"
    opener = _FakeOpener(_PAYLOAD)

    outcome = fetch_verified(_file(), dest, opener=opener, sleep=lambda s: None)

    assert outcome == "downloaded"
    assert verify_md5(dest, _MD5)


def test_an_already_verified_file_is_not_downloaded_again(tmp_path):
    dest = tmp_path / "f.zip"
    dest.write_bytes(_PAYLOAD)
    opener = _FakeOpener()  # any request would fail: the queue is empty

    assert fetch_verified(_file(), dest, opener=opener, sleep=lambda s: None) == "already verified"
    assert opener.urls == []


def test_a_corrupt_file_is_deleted_and_fetched_afresh_never_resumed(tmp_path):
    """Byte-range resumes stitched error pages into archives (2026-09-08). A
    mismatch means the whole file goes and comes back whole."""
    dest = tmp_path / "f.zip"
    dest.write_bytes(_PAYLOAD[:-100])  # truncated, wrong hash
    opener = _FakeOpener(_PAYLOAD)

    outcome = fetch_verified(_file(), dest, opener=opener, sleep=lambda s: None)

    assert outcome == "downloaded"
    assert verify_md5(dest, _MD5)


def test_bad_transfers_and_http_errors_are_retried_with_a_pause_then_given_up(tmp_path):
    dest = tmp_path / "f.zip"
    pauses = []
    opener = _FakeOpener(_http_error(504), _PAYLOAD[:-1], _PAYLOAD)

    outcome = fetch_verified(
        _file(), dest, opener=opener, sleep=pauses.append, attempts=4, pause_seconds=7.0
    )

    assert outcome == "downloaded"
    assert len(opener.urls) == 3
    assert pauses == [7.0, 7.0]  # one pause between each failed attempt and the next

    exhausted = _FakeOpener(_PAYLOAD[:-1], _PAYLOAD[:-1])
    with pytest.raises(ChecksumError, match=r"f\.zip"):
        fetch_verified(
            _file(), tmp_path / "g.zip", opener=exhausted, sleep=lambda s: None, attempts=2
        )
    assert not (tmp_path / "g.zip").exists()


def test_a_manifest_can_be_read_from_a_saved_record_file(tmp_path):
    saved = tmp_path / "record.json"
    saved.write_text(json.dumps(_record([("a.zip", 1, "md5:" + "a" * 32)])), encoding="utf-8")

    manifest = parse_zenodo_manifest(json.loads(saved.read_text(encoding="utf-8")))

    assert set(manifest) == {"a.zip"}
