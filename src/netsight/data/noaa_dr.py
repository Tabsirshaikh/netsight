"""Parse side-scan contact tables out of NOAA Descriptive Report (DR) text.

DRs list investigated or significant contacts in tables such as:

    227-034244S H33-I-E 12.133 28-48-19.481 91-16-40.857 Confirmed as insignificant
    228-233126P 12.743 28-44-51.261 N 91-12-08.347 W

i.e. contact id, optional investigation name, least depth (m or n/a), latitude and longitude in
degrees-minutes-seconds (n/a when not developed), optional hemisphere letters, and remarks that
may wrap onto the next short lines. Rows without remarks are classified from the table caption.
Contacts only mentioned in prose are not rows. These outcomes are expert dispositions, sometimes
developed with multibeam; they are not diver/ROV physical verification.
"""

from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path

CONTACT_ID = re.compile(r"^\s*(\d{3}-\d{6}[PS])\b(.*)$")
DMS = re.compile(r"^(\d{1,3})-(\d{1,2})-(\d{1,2}(?:\.\d+)?)$")
NUMBER = re.compile(r"^\d+(?:\.\d+)?$")
CAPTION = re.compile(r"^\s*Table No\.\s*\d+\.?\s*(.*)$", re.IGNORECASE)
MAX_CONTINUATION_LINES = 5
MAX_CONTINUATION_LENGTH = 40

# (pattern, disposition, is_real_object) - first match wins, so order matters.
DISPOSITION_RULES: tuple[tuple[re.Pattern[str], str, bool | None], ...] = (
    (re.compile(r"\bdton\d*\b|danger to navigation", re.I), "dton", True),
    (re.compile(r"disprov", re.I), "disproved", False),
    (re.compile(r"no height", re.I), "no_height", None),
    (re.compile(r"depression", re.I), "seabed_feature", False),
    (re.compile(r"insignificant", re.I), "real_insignificant", True),
    (re.compile(r"obstruction|wreck", re.I), "real_obstruction", True),
    (re.compile(r"pipeline|cable", re.I), "real_known_feature", True),
)


@dataclass
class ContactOutcome:
    survey_id: str
    contact_id: str
    investigation: str | None
    least_depth_m: float | None
    lat: float | None
    lon: float | None
    hemisphere_assumed: bool
    remarks: str
    table_caption: str
    disposition: str
    is_real_object: bool | None
    ground_truth: str
    page: int
    source: str = "dr_text"


def dms_to_degrees(text: str) -> float | None:
    m = DMS.match(text.strip())
    if not m:
        return None
    deg, minutes, seconds = (float(g) for g in m.groups())
    return deg + minutes / 60.0 + seconds / 3600.0


def classify_disposition(text: str) -> tuple[str, bool | None]:
    for pattern, disposition, is_real in DISPOSITION_RULES:
        if pattern.search(text):
            return disposition, is_real
    return "unknown", None


def _is_na(token: str) -> bool:
    return token.lower() in ("n/a", "na", "-")


def _parse_row(rest: str, default_hemispheres: tuple[str, str]):
    """Parse the tokens after a contact id. Returns None if the line is not a table row."""
    tokens = rest.split()
    i = 0
    investigation = None
    if i < len(tokens) and re.search(r"[A-Za-z]", tokens[i]) and not _is_na(tokens[i]):
        investigation = tokens[i]
        i += 1
    if i >= len(tokens) or not (NUMBER.match(tokens[i]) or _is_na(tokens[i])):
        return None  # prose such as "contact 229-043001P, which has ..."
    depth = None if _is_na(tokens[i]) else float(tokens[i])
    i += 1
    if i < len(tokens) and tokens[i].lower() == "m":
        i += 1
    coords: list[float | None] = []
    assumed = False
    for axis, default in zip(("lat", "lon"), default_hemispheres, strict=True):
        if i >= len(tokens):
            return None
        token = tokens[i]
        i += 1
        if _is_na(token):
            coords.append(None)
            continue
        value = dms_to_degrees(token)
        if value is None:
            return None
        hemi = default
        if i < len(tokens) and tokens[i].upper() in (("N", "S") if axis == "lat" else ("E", "W")):
            hemi = tokens[i].upper()
            i += 1
        else:
            assumed = True
        coords.append(-value if hemi in ("S", "W") else value)
    remarks = " ".join(tokens[i:])
    return investigation, depth, coords[0], coords[1], assumed, remarks


def parse_contact_tables(
    pages: list[str], survey_id: str, *, default_hemispheres: tuple[str, str] = ("N", "W")
) -> list[ContactOutcome]:
    """Extract contact-outcome rows from the DR text, one string per PDF page."""
    rows: list[ContactOutcome] = []
    seen: set[tuple[str, str | None, str]] = set()
    caption = ""
    for page_no, page in enumerate(pages, start=1):
        lines = page.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            cap = CAPTION.match(line)
            if cap:
                caption = cap.group(1).strip()
            m = CONTACT_ID.match(line)
            parsed = _parse_row(m.group(2), default_hemispheres) if m else None
            if not parsed:
                i += 1
                continue
            investigation, depth, lat, lon, assumed, remarks = parsed
            j = i + 1
            extra: list[str] = []
            while j < len(lines) and len(extra) < MAX_CONTINUATION_LINES:
                nxt = lines[j].strip()
                if (
                    not nxt
                    or len(nxt) > MAX_CONTINUATION_LENGTH
                    or CONTACT_ID.match(nxt)
                    or CAPTION.match(nxt)
                ):
                    break
                extra.append(nxt)
                j += 1
            remarks = " ".join([remarks, *extra]).strip()
            disposition, is_real = classify_disposition(remarks or caption)
            key = (m.group(1), investigation, remarks)
            if key not in seen:
                seen.add(key)
                rows.append(
                    ContactOutcome(
                        survey_id=survey_id,
                        contact_id=m.group(1),
                        investigation=investigation,
                        least_depth_m=depth,
                        lat=lat,
                        lon=lon,
                        hemisphere_assumed=assumed,
                        remarks=remarks,
                        table_caption=caption,
                        disposition=disposition,
                        is_real_object=is_real,
                        ground_truth="multibeam_developed" if depth is not None
                        else "expert_disposition",
                        page=page_no,
                    )
                )
            i = j
    return rows


ITEMS_INVESTIGATED = re.compile(r"Number of items investigated\s+(\d+)", re.IGNORECASE)
SSS_COVERAGE = re.compile(r"\b(100|200)\s*%\s*(?:side\s*scan|SSS)", re.IGNORECASE)
SIDE_SCAN = re.compile(r"side\s*scan|\bSSS\b", re.IGNORECASE)
SEPARATE_LIST = re.compile(r"Separates?\s+[IVX]+\s+Side\s+Scan\s+Contact", re.IGNORECASE)


def dr_summary(pages: list[str], survey_id: str) -> dict:
    """Survey-level facts used by the contact-data kill test (one dict per survey)."""
    text = "\n".join(pages)
    items = ITEMS_INVESTIGATED.search(text)
    coverages = [int(c) for c in SSS_COVERAGE.findall(text)]
    return {
        "survey_id": survey_id,
        "pages": len(pages),
        "items_investigated": int(items.group(1)) if items else None,
        "contact_rows": len(parse_contact_tables(pages, survey_id)),
        "contact_list_in_separate": bool(SEPARATE_LIST.search(text)),
        "sss_coverage_percent": max(coverages) if coverages else None,
        "mentions_side_scan": bool(SIDE_SCAN.search(text)),
    }


def write_contacts_csv(rows: list[ContactOutcome], path: str | Path) -> Path:
    path = Path(path)
    names = [f.name for f in fields(ContactOutcome)]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    return path
