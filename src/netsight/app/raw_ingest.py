"""Raw side-scan files (XTF, JSF) to dashboard images, with navigation provenance (plan 16.1).

read (io) -> QC + ground range (normalise_record) -> port | starboard waterfall, 8-bit ->
square pixels from navigation when plausible -> chunks of at most ``max_rows`` rows. Each
chunk keeps the swath's own not-searched mask and the map from its rows to source pings, so
contacts are located from ping navigation (geo.locate) and coverage needs no image guessing.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

RAW_EXTENSIONS = {".xtf", ".jsf"}
MAX_ROWS = 2000
MAX_CHUNKS = 20


@dataclass
class RawChunk:
    name: str
    image: np.ndarray  # uint8, port (mirrored) | starboard, rows = along track
    not_searched: np.ndarray  # bool, same shape
    row_to_ping: np.ndarray  # fractional source ping per row


@dataclass
class RawSurvey:
    name: str
    swath: Any  # netsight.normalise.swath.NormalisedSwath
    chunks: list[RawChunk]
    summary: dict[str, Any] = field(default_factory=dict)
    port_width: int = 0  # columns of (mirrored) port data; 0 when the port side is absent


def _to_uint8(img: np.ndarray) -> np.ndarray:
    finite = img[np.isfinite(img)]
    if not finite.size:
        return np.zeros(img.shape, np.uint8)
    lo, hi = np.percentile(finite, [1, 99.5])
    scaled = (img - lo) / max(hi - lo, 1e-9) * 255
    return np.clip(np.nan_to_num(scaled, nan=0.0), 0, 255).astype(np.uint8)


def ingest_raw(
    data: bytes, name: str, *, max_rows: int = MAX_ROWS, max_chunks: int = MAX_CHUNKS
) -> RawSurvey:
    """Parse and normalise one raw file; raise ValueError with a plain reason if unusable."""
    from netsight.io import open_survey
    from netsight.normalise.along_track import square_waterfall
    from netsight.normalise.swath import normalise_record

    suffix = Path(name).suffix.lower()
    if suffix not in RAW_EXTENSIONS:
        raise ValueError(f"{name}: not a raw side-scan file (.xtf or .jsf)")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"upload{suffix}"
        path.write_bytes(data)
        record = open_survey(path)
    swath = normalise_record(record)
    res = float(swath.ground_res_m)
    # a side with no data at all (single-sided records) is left out, not shown as black
    sides = [
        (np.fliplr(swath.port), np.fliplr(swath.not_searched_port))
        if not swath.not_searched_port.all()
        else None,
        (swath.stbd, swath.not_searched_stbd) if not swath.not_searched_stbd.all() else None,
    ]
    used = [s for s in sides if s is not None]
    if not used:
        raise ValueError(f"{name}: neither channel has usable data")
    port_width = sides[0][0].shape[1] if sides[0] is not None else 0
    image = np.hstack([s[0] for s in used])
    mask = np.hstack([s[1] for s in used])
    image8 = _to_uint8(image)
    notes = list(swath.provenance.notes)
    row_to_ping = np.arange(image8.shape[0], dtype=float)
    stretch = 1.0
    try:
        sq = square_waterfall(image8, swath.x, swath.y, swath.coord_kind, across_m=res)
        image8, row_to_ping, stretch = sq.image, np.asarray(sq.row_to_ping, float), sq.stretch
        mask = mask[np.clip(np.rint(row_to_ping).astype(int), 0, mask.shape[0] - 1)]
    except ValueError as exc:
        notes.append(f"rows not resampled to square pixels: {exc}")
    n_rows = image8.shape[0]
    n_chunks = -(-n_rows // max_rows)
    if n_chunks > max_chunks:
        raise ValueError(
            f"{name}: too long for the dashboard ({n_rows} rows = {n_chunks} images, limit "
            f"{max_chunks}); split the file or use the command line"
        )
    stem = Path(name).stem
    chunks = []
    for k in range(n_chunks):
        a, b = k * max_rows, min((k + 1) * max_rows, n_rows)
        chunks.append(
            RawChunk(
                name=f"{stem}_rows{a:05d}-{b - 1:05d}.png",
                image=np.ascontiguousarray(image8[a:b]),
                not_searched=np.ascontiguousarray(mask[a:b]),
                row_to_ping=row_to_ping[a:b],
            )
        )
    meta = swath.metadata()
    summary = {
        "file": name,
        "format": record.sensor.source_format,
        "sensor": record.sensor.to_dict(),
        "n_pings": int(record.n_pings),
        "time_start": meta["time_start"],
        "time_end": meta["time_end"],
        "nav_source_counts": meta["nav_source_counts"],
        "coord_kinds": meta["coord_kinds"],
        "altitude_source_counts": meta["altitude_source_counts"],
        "ground_res_m": res,
        "along_track_stretch": float(stretch),
        # share of the displayed swath; a side with no data at all is listed, not averaged in
        "not_searched_fraction": float(mask.mean()),
        "absent_sides": [s for s, x in zip(("port", "starboard"), sides, strict=True) if x is None],
        "quality": meta["quality"],
        "images": [c.name for c in chunks],
        "notes": notes,
        "reader": swath.provenance.to_dict().get("reader"),
        "sha256": swath.provenance.to_dict().get("sha256"),
    }
    return RawSurvey(name=name, swath=swath, chunks=chunks, summary=summary, port_width=port_width)


def locate_box(raw: RawSurvey, chunk_index: int, box: tuple[float, ...]) -> dict[str, Any]:
    """Position of a box centre from ping navigation (flat seabed, first-order ellipse)."""
    from netsight.geo.locate import locate_contact

    sw = raw.swath
    chunk = raw.chunks[chunk_index]
    edge = raw.port_width  # nadir column in the waterfall
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    side = "port" if cx < edge else "stbd"
    ground = (edge - cx if side == "port" else cx - edge) * float(sw.ground_res_m)
    row = float(np.clip(cy, 0, len(chunk.row_to_ping) - 1))
    ping = int(
        np.clip(
            np.rint(np.interp(row, np.arange(len(chunk.row_to_ping)), chunk.row_to_ping)),
            0,
            len(sw.x) - 1,
        )
    )
    pos = locate_contact(
        ping_x=float(sw.x[ping]),
        ping_y=float(sw.y[ping]),
        coord_kind=str(sw.coord_kind[ping]),
        nav_source=str(sw.nav_source[ping]),
        heading_deg=float(sw.heading_deg[ping]),
        side=side,
        ground_range_m=float(ground),
        ground_res_m=float(sw.ground_res_m),
    )
    latlon = pos.coord_kind == "latlon" and not pos.withdrawn
    return {
        "lon": float(pos.x) if latlon else None,
        "lat": float(pos.y) if latlon else None,
        "map_x": float(pos.x) if pos.coord_kind == "projected" and not pos.withdrawn else None,
        "map_y": float(pos.y) if pos.coord_kind == "projected" and not pos.withdrawn else None,
        "ellipse95": None if pos.withdrawn else list(pos.ellipse95),
        "cov_en_m2": None if pos.withdrawn else list(pos.cov_en_m2),
        "side": side,
        "ground_range_m": float(ground),
        "ping": ping,
        "nav_source": pos.nav_source,
        "method": pos.method + "; ping navigation from the raw file",
        "withdrawn_reason": pos.reason,
    }
