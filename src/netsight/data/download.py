"""Resumable, verified downloads and licence-tier-aware dataset storage."""

from __future__ import annotations

import hashlib
import http.client
import time
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


def _fetch_once(url: str, part: Path, timeout: float) -> None:
    """One request, appending to `part` from its current size. Network errors propagate."""
    offset = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": USER_AGENT}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        if offset and resp.status != 206:
            offset = 0  # server ignored the Range header: start again
        with open(part, "ab" if offset else "wb") as f:
            while True:
                try:
                    block = resp.read(CHUNK)
                except http.client.IncompleteRead as exc:
                    f.write(exc.partial)  # keep what arrived; the next attempt resumes
                    raise
                if not block:
                    break
                f.write(block)


def download(
    url: str, dest: str | Path, *, size: int | None = None, md5: str | None = None,
    timeout: float = 60.0, attempts: int = 8, retry_wait: float = 5.0,
) -> Path:
    """Download url to dest via dest.part, resuming dropped connections; verify size and md5.

    Large files on Zenodo and figshare are often cut off part-way, sometimes without any
    error. A short file is resumed with an HTTP Range request (up to `attempts` times) and
    kept on failure so the next run continues. A file that is too long, or complete with a
    wrong md5, is corrupt and removed.
    """
    dest = Path(dest)
    if dest.exists() and (size is not None or md5) and _verify(dest, size, md5) is None:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    last_error = "no attempt made"
    for attempt in range(attempts):
        failed = False
        try:
            _fetch_once(url, part, timeout)
        except urllib.error.HTTPError as exc:
            complete = size is not None and part.exists() and part.stat().st_size == size
            if exc.code == 416 and complete:
                pass  # range starts past the end: the file is already complete
            elif 400 <= exc.code < 500 and exc.code not in (408, 429):
                raise DownloadError(f"download failed for {url}: {exc}") from exc
            else:
                failed, last_error = True, str(exc)
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            failed, last_error = True, str(exc) or type(exc).__name__
        got = part.stat().st_size if part.exists() else 0
        if size is not None and got < size:
            failed, last_error = True, f"incomplete: {got} of {size} bytes"
        if failed:  # resume on the next attempt; never accept a file cut off mid-transfer
            if attempt + 1 < attempts:
                time.sleep(retry_wait)
            continue
        problem = _verify(part, size, md5)
        if problem:
            part.unlink(missing_ok=True)
            raise DownloadError(f"{dest.name}: {problem}; corrupt partial file removed")
        part.replace(dest)
        return dest
    raise DownloadError(
        f"{dest.name}: {last_error} after {attempts} attempts; partial kept at {part} "
        "and resumed on the next run"
    )


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
