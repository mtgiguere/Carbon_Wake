"""Data operations: manifests, checksums, verified downloads.

RIGOR.md standing rule 7 — data-ops code is product code. Every lesson of the
2026-09-08 backfill lives here as behavior: a byte count is not verification,
only the publisher's MD5 is; a checksum string is stripped of the whitespace
a Windows text file adds; an HTTP error body is never written as a download
(``urlopen`` raises on 4xx/5xx, and a failed transfer's partial file is
removed); a mismatching file is deleted and fetched whole, never resumed; a
file that already verifies is not fetched again.

Pure by injection: the opener and the sleep are parameters, so every path is
unit-testable without a network.
"""

import contextlib
import hashlib
import re
import time
import urllib.error
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

#: The runs' provenance strings — the citation every stored run carries.
CARBON_SOURCE_TEXT = (
    "Diesing 2021, OC density mean + total uncertainty, 500m "
    "(PANGAEA 10.1594/PANGAEA.928272, CC-BY-4.0)"
)


def effort_source_text(year: int) -> str:
    return (
        "Global Fishing Watch, AIS-based Apparent Fishing Effort v3.0, fleet-daily "
        f"0.01deg, year {year} (Zenodo 10.5281/zenodo.14982712, CC BY-NC 4.0)"
    )


def fleet_daily_key(year: int) -> str:
    """The Zenodo file name of a product year's fleet-daily 0.01-degree zip."""
    return f"fleet-daily-csvs-100-v3-{year}.zip"


@dataclass(frozen=True)
class ZenodoFile:
    """One file of a Zenodo record: name, size, publisher's MD5, download URL."""

    key: str
    size: int
    md5: str
    url: str


class ChecksumError(RuntimeError):
    """No download of a file ever matched the publisher's checksum."""


_MD5 = re.compile(r"^[0-9a-f]{32}$")


def parse_zenodo_manifest(record: Mapping) -> dict[str, ZenodoFile]:
    """A Zenodo record's ``files`` as a manifest keyed by file name.

    Only MD5 checksums are accepted (what Zenodo publishes); the hash is
    stripped and lower-cased, so a list saved on Windows still verifies.
    """
    manifest: dict[str, ZenodoFile] = {}
    for entry in record["files"]:
        key = entry["key"]
        algorithm, _, digest = str(entry["checksum"]).strip().partition(":")
        digest = digest.strip().lower()
        if algorithm.strip().lower() != "md5":
            raise ValueError(f"{key}: unsupported checksum algorithm {algorithm.strip()!r}")
        if not _MD5.match(digest):
            raise ValueError(f"{key}: malformed md5 {digest!r}")
        manifest[key] = ZenodoFile(
            key=key, size=int(entry["size"]), md5=digest, url=entry["links"]["self"]
        )
    return manifest


def verify_md5(path: Path, expected: str, *, chunk_size: int = 1 << 20) -> bool:
    """Whether ``path`` exists and its MD5 equals ``expected`` (case-insensitive)."""
    if not path.is_file():
        return False
    digest = hashlib.md5(usedforsecurity=False)  # integrity against the publisher's MD5
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest() == expected.strip().lower()


def download(
    url: str,
    dest: Path,
    *,
    opener: Callable = urlopen,
    timeout: float = 120.0,
    chunk_size: int = 1 << 20,
) -> None:
    """Fetch ``url`` to ``dest`` through a ``.part`` file that becomes ``dest``
    only when the transfer completes; on any failure the partial file is
    removed and the error propagates. HTTP errors raise (never saved)."""
    part = dest.with_name(dest.name + ".part")
    try:
        with opener(url, timeout=timeout) as response, part.open("wb") as out:
            while chunk := response.read(chunk_size):
                out.write(chunk)
        part.replace(dest)
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def fetch_verified(
    file: ZenodoFile,
    dest: Path,
    *,
    opener: Callable = urlopen,
    sleep: Callable[[float], None] = time.sleep,
    attempts: int = 4,
    pause_seconds: float = 30.0,
) -> str:
    """``dest`` verified against ``file.md5``: "already verified" when it is,
    otherwise download afresh (deleting any mismatching file, never resuming)
    up to ``attempts`` times with ``pause_seconds`` between failures.
    Returns "downloaded", or raises ChecksumError naming the file."""
    if verify_md5(dest, file.md5):
        return "already verified"
    for attempt in range(1, attempts + 1):
        dest.unlink(missing_ok=True)
        # A failed transfer is just a failed attempt; the checksum decides.
        with contextlib.suppress(urllib.error.URLError, OSError):
            download(file.url, dest, opener=opener)
        if verify_md5(dest, file.md5):
            return "downloaded"
        if attempt < attempts:
            sleep(pause_seconds)
    dest.unlink(missing_ok=True)
    raise ChecksumError(
        f"{file.key}: no download matched md5 {file.md5} after {attempts} attempt(s)"
    )
