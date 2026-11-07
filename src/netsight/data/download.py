"""Resumable, verified downloads and licence-tier-aware dataset storage."""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from pathlib import Path

CHUNK = 1 << 20
USER_AGENT = "netsight-data/0.1 (research data download)"


class DownloadError(RuntimeError):
    pass


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as f:
        while block := f.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def _verify(path: Path, size: int | None, md5: str | None) -> str | None:
    """Return an error message, or None if the file matches."""
    if size is not None and path.stat().st_size != size:
        return f"size {path.stat().st_size} != expected {size}"
    if md5 and _md5(path) != md5.lower():
        return "md5 mismatch"
    return None


def download(
    url: str, dest: str | Path, *, size: int | None = None, md5: str | None = None,
    timeout: float = 60.0,
) -> Path:
    """Download url to dest via dest.part, resuming a partial file; verify size and md5."""
    dest = Path(dest)
    if dest.exists() and (size is not None or md5) and _verify(dest, size, md5) is None:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    offset = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": USER_AGENT}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            if offset and resp.status != 206:
                offset = 0  # server ignored the Range header: start again
            with open(part, "ab" if offset else "wb") as f:
                while block := resp.read(CHUNK):
                    f.write(block)
    except (urllib.error.URLError, OSError) as exc:
        raise DownloadError(f"download failed for {url}: {exc}") from exc
    problem = _verify(part, size, md5)
    if problem:
        part.unlink(missing_ok=True)
        raise DownloadError(f"{dest.name}: {problem}; partial file removed")
    part.replace(dest)
    return dest


def tier_dir(data_root: str | Path, entry: dict) -> Path:
    """Research-only data lives apart so it can never be mixed into commercial training sets."""
    root = Path(data_root) / "raw"
    if entry.get("tier") == "research_only":
        return root / "research_only" / entry["id"]
    return root / entry["id"]


def fetch_dataset_files(
    entry: dict, data_root: str | Path, *, names: list[str] | None = None
) -> list[Path]:
    """Download a register entry's files (all, or the named ones) into its tier directory."""
    if entry.get("availability") == "blocked":
        raise DownloadError(f"{entry['id']} is marked blocked in the licence register")
    files = entry.get("files") or []
    if names:
        files = [f for f in files if f["name"] in names]
        missing = set(names) - {f["name"] for f in files}
        if missing:
            raise DownloadError(f"{entry['id']}: no such file(s) {sorted(missing)}")
    if not files:
        raise DownloadError(f"{entry['id']}: no downloadable files listed in the register")
    target = tier_dir(data_root, entry)
    return [
        download(f["url"], target / f["name"], size=f.get("size"), md5=f.get("md5"))
        for f in files
    ]
