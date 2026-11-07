"""NOAA NCEI hydrographic survey folders (CC0): URLs, listings and fetching."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from netsight.data.download import USER_AGENT, DownloadError, download

NCEI_COAST = "https://data.ngdc.noaa.gov/platforms/ocean/nos/coast"
SURVEY_ID = re.compile(r"^H(\d{5})$", re.IGNORECASE)
LINK = re.compile(r'<a href="([^"?/][^"]*)">')


def survey_folder_url(survey_id: str) -> str:
    """NCEI groups H-surveys in blocks of 2000 (H12001-H14000 holds H12333)."""
    m = SURVEY_ID.match(survey_id.strip())
    if not m:
        raise ValueError(f"not an H-survey id: {survey_id!r} (expected e.g. H12333)")
    n = int(m.group(1))
    start = ((n - 1) // 2000) * 2000 + 1
    return f"{NCEI_COAST}/H{start:05d}-H{start + 1999:05d}/H{n:05d}/"


def list_folder(url: str, *, timeout: float = 60.0) -> list[dict]:
    """Entries of an Apache-style directory listing: name and whether it is a folder."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except OSError as exc:
        raise DownloadError(f"could not list {url}: {exc}") from exc
    names = [n for n in LINK.findall(html) if not n.startswith(("http", "mailto", "../"))]
    return [{"name": n, "is_dir": n.endswith("/")} for n in dict.fromkeys(names)]


def fetch_survey(
    survey_id: str, data_root: str | Path, *, parts: tuple[str, ...] = ("DR",)
) -> list[Path]:
    """Download the given sub-folders (e.g. DR, TIFF, MBAB) of one survey."""
    base = survey_folder_url(survey_id)
    sid = survey_id.upper()
    dest_root = Path(data_root) / "raw" / "noaa" / sid
    available = {e["name"].rstrip("/") for e in list_folder(base) if e["is_dir"]}
    paths: list[Path] = []
    for part in parts:
        if part not in available:
            continue
        folder = base + part + "/"
        for entry in list_folder(folder):
            if not entry["is_dir"]:
                target = dest_root / part / entry["name"]
                paths.append(download(folder + entry["name"], target))
    return paths
