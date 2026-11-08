"""Build candidate review chips from NOAA contacts and side-scan mosaics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image
from pyproj import CRS, Geod, Transformer

from netsight.io.mosaic import Mosaic, read_mosaic

type Box = tuple[float, float, float, float]
type Point = tuple[float, float]
type Status = Literal["ok", "outside", "nodata"]

LABEL_STATUS = "candidate - position from NOAA, box extent unchecked"
_GEOD = Geod(ellps="WGS84")


@dataclass(frozen=True)
class Contact:
    """A georeferenced NOAA contact."""

    survey_id: str
    contact_id: str
    lat: float
    lon: float
    is_real: bool | None
    kind: str
    source_file: str


@dataclass(frozen=True)
class ChipRecord:
    """A candidate chip or a skipped contact with an explicit status."""

    survey_id: str
    contact_id: str
    is_real: bool | None
    kind: str
    chip: np.ndarray
    box_px: Box
    centre_px: Point
    metres_per_px: Point
    window: tuple[int, int]
    status: Status
    valid_fraction: float = 0.0
    provenance: str = ""


def load_contacts(paths: Sequence[Path], survey_id: str) -> list[Contact]:
    """Read contacts in input order, merging positions separated by less than 5 m."""
    contacts: list[Contact] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                if (row.get("survey_id") or "").strip() != survey_id:
                    continue
                try:
                    lat = float(row.get("lat") or "")
                    lon = float(row.get("lon") or "")
                except ValueError:
                    continue
                if not (math.isfinite(lat) and math.isfinite(lon)):
                    continue
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    continue
                contact_id = (row.get("contact_id") or row.get("item_no") or "").strip()
                if not contact_id:
                    continue
                real_text = (row.get("is_real_object") or "").strip().lower()
                is_real = {"true": True, "false": False}.get(real_text)
                contact = Contact(
                    survey_id=survey_id,
                    contact_id=contact_id,
                    lat=lat,
                    lon=lon,
                    is_real=is_real,
                    kind=(row.get("s57_class") or row.get("item_kind") or "").strip(),
                    source_file=str(path),
                )
                for index, previous in enumerate(contacts):
                    _, _, distance = _GEOD.inv(previous.lon, previous.lat, lon, lat)
                    if distance < 5.0:
                        if contact.is_real is True and previous.is_real is not True:
                            contacts[index] = contact
                        break
                else:
                    contacts.append(contact)
    return contacts


@lru_cache(maxsize=32)
def _transformer(crs_wkt: str) -> Transformer:
    """Cache WGS84-to-mosaic transformations."""
    return Transformer.from_crs("EPSG:4326", CRS.from_wkt(crs_wkt), always_xy=True)


def lonlat_to_pixel(mosaic: Mosaic, lon: float, lat: float) -> Point:
    """Return continuous corner-based pixel coordinates; centres are half integers."""
    if mosaic.crs_wkt is None:
        raise ValueError("Mosaic has no CRS")
    x, y = _transformer(mosaic.crs_wkt).transform(lon, lat)
    a, b, c, d, e, f = mosaic.transform
    determinant = a * e - b * d
    if not math.isfinite(determinant) or determinant == 0:
        raise ValueError("Mosaic transform is not invertible")
    return (
        (e * (x - c) - b * (y - f)) / determinant,
        (a * (y - f) - d * (x - c)) / determinant,
    )


def _float_array(mosaic: Mosaic) -> np.ndarray:
    """Convert masked cells and nonfinite samples to a consistent float array."""
    return np.ma.asarray(mosaic.array, dtype=np.float64).filled(np.nan)


def make_chips(
    mosaic: Mosaic,
    contacts: Sequence[Contact],
    *,
    chip_px: int = 256,
    box_m: float = 10.0,
    min_valid: float = 0.5,
) -> list[ChipRecord]:
    """Create chips, retaining skipped records and whole-mosaic intensity scaling."""
    if chip_px <= 0:
        raise ValueError("chip_px must be positive")
    if not math.isfinite(box_m) or box_m <= 0:
        raise ValueError("box_m must be finite and positive")
    if not 0 <= min_valid <= 1:
        raise ValueError("min_valid must lie between zero and one")
    if mosaic.crs_wkt is None:
        raise ValueError("Mosaic has no CRS")
    data = _float_array(mosaic)
    if data.ndim != 2:
        raise ValueError("Mosaic must be two-dimensional")
    height, width = data.shape
    if min(height, width) < chip_px:
        raise ValueError("Mosaic must be at least chip_px pixels on each axis")
    metres_per_px = (abs(mosaic.pixel_size[0]), abs(mosaic.pixel_size[1]))
    if any(not math.isfinite(value) or value <= 0 for value in metres_per_px):
        raise ValueError("Pixel sizes must be finite and nonzero")

    finite = np.isfinite(data)
    scaled = np.zeros(data.shape, dtype=np.uint8)
    if finite.any():
        low, high = np.percentile(data[finite], [1, 99])
        if high > low:
            values = np.clip((data[finite] - low) / (high - low), 0, 1)
            scaled[finite] = np.rint(values * 255).astype(np.uint8)

    half_width = box_m / metres_per_px[0] / 2
    half_height = box_m / metres_per_px[1] / 2
    records: list[ChipRecord] = []
    for contact in contacts:
        col, row = lonlat_to_pixel(mosaic, contact.lon, contact.lat)
        window = (0, 0)
        centre = (col, row)
        box: Box = (0.0, 0.0, 0.0, 0.0)
        fraction = 0.0
        chip = np.empty((0, 0), dtype=np.uint8)
        status: Status = "outside"
        if math.isfinite(col) and math.isfinite(row) and 0 <= col < width and 0 <= row < height:
            col0 = min(max(math.floor(col - chip_px / 2), 0), width - chip_px)
            row0 = min(max(math.floor(row - chip_px / 2), 0), height - chip_px)
            window = (row0, col0)
            cx, cy = col - col0, row - row0
            centre = (cx, cy)
            box = (
                max(0.0, cx - half_width),
                max(0.0, cy - half_height),
                min(float(chip_px), cx + half_width),
                min(float(chip_px), cy + half_height),
            )
            slices = (slice(row0, row0 + chip_px), slice(col0, col0 + chip_px))
            fraction = float(finite[slices].mean())
            status = "ok" if fraction >= min_valid else "nodata"
            if status == "ok":
                chip = scaled[slices].copy()
        records.append(
            ChipRecord(
                survey_id=contact.survey_id,
                contact_id=contact.contact_id,
                is_real=contact.is_real,
                kind=contact.kind,
                chip=chip,
                box_px=box,
                centre_px=centre,
                metres_per_px=metres_per_px,
                window=window,
                status=status,
                valid_fraction=fraction,
                provenance=str(mosaic.provenance),
            )
        )
    return records


def _safe_component(value: str) -> str:
    """Sanitize a filename component, distinguishing altered identifiers."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", value)
    if safe != value or not safe:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
        safe = f"{safe[:64]}_{digest}"
    return safe


def _json_number(value: float) -> float | None:
    """Represent nonfinite projected coordinates as JSON null."""
    return value if math.isfinite(value) else None


def write_chips(records: Sequence[ChipRecord], out_dir: Path) -> Path:
    """Write review PNGs, candidate YOLO labels, and a manifest of all outcomes."""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    used_names: set[str] = set()
    for record in records:
        entry: dict[str, object] = {
            "survey_id": record.survey_id,
            "contact_id": record.contact_id,
            "is_real": record.is_real,
            "kind": record.kind,
            "box_px": record.box_px,
            "centre_px": [_json_number(value) for value in record.centre_px],
            "metres_per_px": record.metres_per_px,
            "window": record.window,
            "status": record.status,
            "valid_fraction": record.valid_fraction,
            "provenance": record.provenance,
            "label_status": LABEL_STATUS,
        }
        if record.status == "ok":
            stem = f"{_safe_component(record.survey_id)}_{_safe_component(record.contact_id)}"
            if stem in used_names:
                raise ValueError(f"Duplicate output filename: {stem}")
            used_names.add(stem)
            image_name = f"{stem}.png"
            label_name = f"{stem}.txt"
            Image.fromarray(record.chip).save(out_dir / image_name)
            height, width = record.chip.shape
            x0, y0, x1, y1 = record.box_px
            values = (
                (x0 + x1) / (2 * width),
                (y0 + y1) / (2 * height),
                (x1 - x0) / width,
                (y1 - y0) / height,
            )
            line = "0 " + " ".join(f"{value:.12f}" for value in values) + "\n"
            (out_dir / label_name).write_text(line, encoding="utf-8")
            entry.update(image_file=image_name, label_file=label_name)
        manifest.append(entry)
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main(argv: Sequence[str] | None = None) -> None:
    """Run chip generation and select the most valid overlapping mosaic window."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", required=True)
    parser.add_argument("--mosaics", required=True, nargs="+", type=Path)
    parser.add_argument("--contacts", required=True, nargs="+", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--chip-px", type=int, default=256)
    parser.add_argument("--box-m", type=float, default=10.0)
    args = parser.parse_args(argv)
    contacts = load_contacts(args.contacts, args.survey)
    selected: dict[tuple[str, str], ChipRecord] = {}
    priority = {"outside": 0, "nodata": 1, "ok": 2}
    for path in args.mosaics:
        mosaic = read_mosaic(path)
        for record in make_chips(mosaic, contacts, chip_px=args.chip_px, box_m=args.box_m):
            key = (record.survey_id, record.contact_id)
            previous = selected.get(key)
            score = (priority[record.status], record.valid_fraction)
            if previous is None or score > (priority[previous.status], previous.valid_fraction):
                selected[key] = record
    manifest_path = write_chips(list(selected.values()), args.out)
    print(manifest_path)


if __name__ == "__main__":
    main()
