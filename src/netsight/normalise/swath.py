"""Layer L1: turn a SonarRecord into a QC'd, ground-range, geometry-aware swath."""

from __future__ import annotations

import json
import math
import warnings
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from netsight.core.records import Provenance, SensorDescriptor, SonarRecord
from netsight.geometry.slant import (
    bottom_track,
    fuse_altitude,
    grazing_angle_deg,
    ground_range_grid,
    to_ground_range,
)
from netsight.qc.dropout import repair_dropouts
from netsight.qc.quality import (
    DEFAULT_THRESHOLDS,
    QualityMask,
    QualityThresholds,
    compute_quality,
)
from netsight.radiometry.gain import across_track_equalise

TIERS_M: dict[str, float] = {
    "sas": 0.02,
    "sidescan_fine": 0.05,
    "sidescan": 0.10,
    "sidescan_coarse": 0.20,
    "mbes": 0.50,
}


def choose_ground_resolution(native_spacing_m: float) -> float:
    candidates = sorted(TIERS_M.values())
    for res in candidates:
        if res >= native_spacing_m * 0.999:
            return res
    return candidates[-1]


@dataclass
class NormalisedSwath:
    ground_res_m: float
    ground_m: np.ndarray
    port: np.ndarray
    stbd: np.ndarray
    grazing_deg: np.ndarray
    not_searched_port: np.ndarray
    not_searched_stbd: np.ndarray
    altitude_m: np.ndarray
    altitude_source: list[str]
    x: np.ndarray
    y: np.ndarray
    coord_kind: list[str]
    nav_source: list[str]
    heading_deg: np.ndarray
    times: np.ndarray
    quality: QualityMask
    sensor: SensorDescriptor
    provenance: Provenance

    def metadata(self) -> dict:
        return {
            "ground_res_m": self.ground_res_m,
            "n_pings": int(self.port.shape[0]),
            "n_bins": int(self.port.shape[1]),
            "sensor": self.sensor.to_dict(),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.summary(),
            "nav_source_counts": dict(Counter(self.nav_source)),
            "altitude_source_counts": dict(Counter(self.altitude_source)),
            "coord_kinds": sorted(set(self.coord_kind)),
            "time_start": str(self.times[0]) if self.times.size else None,
            "time_end": str(self.times[-1]) if self.times.size else None,
            "not_searched_fraction": float(
                (self.not_searched_port.mean() + self.not_searched_stbd.mean()) / 2
            ),
        }

    def to_npz(self, path: str | Path) -> Path:
        path = Path(path)
        np.savez_compressed(
            path,
            ground_m=self.ground_m,
            port=self.port,
            stbd=self.stbd,
            grazing_deg=self.grazing_deg,
            not_searched_port=self.not_searched_port,
            not_searched_stbd=self.not_searched_stbd,
            altitude_m=self.altitude_m,
            x=self.x,
            y=self.y,
            heading_deg=self.heading_deg,
            times_ms=self.times.astype("datetime64[ms]").astype(np.int64),
            quality_q=self.quality.q,
            **{f"flag_{k}": v for k, v in self.quality.flags.items()},
            metadata=np.array(json.dumps(self.metadata())),
        )
        return path


def normalise_record(
    record: SonarRecord,
    *,
    ground_res_m: float | None = None,
    thresholds: QualityThresholds = DEFAULT_THRESHOLDS,
    equalise: bool = True,
) -> NormalisedSwath:
    if record.n_pings == 0:
        raise ValueError("record has no pings")
    port_raw = record.channel_matrix("port")
    stbd_raw = record.channel_matrix("stbd")
    pings = record.pings
    spacing = np.array([p.sample_spacing_m for p in pings])
    slant = np.array([p.slant_range_m for p in pings])

    port_fix = repair_dropouts(port_raw)
    stbd_fix = repair_dropouts(stbd_raw)
    gap_rows = port_fix.gap_rows | stbd_fix.gap_rows
    repaired_rows = (port_fix.repaired_rows | stbd_fix.repaired_rows) & ~gap_rows

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        combined = np.nanmean(np.stack([port_fix.data, stbd_fix.data]), axis=0)
    tracked = bottom_track(combined, float(np.median(spacing)))
    recorded = np.array([p.altitude_m for p in pings])
    altitude, altitude_source = fuse_altitude(recorded, tracked)
    if not np.isfinite(altitude).any():
        raise ValueError(
            "no altitude available (recorded or bottom-tracked); cannot convert to ground range"
        )

    res = ground_res_m or choose_ground_resolution(float(np.median(spacing)))
    max_ground = math.sqrt(float(slant.max()) ** 2 - float(np.nanmin(altitude)) ** 2)
    grid = ground_range_grid(max_ground, res)
    n, m = len(pings), grid.size
    port_g = np.full((n, m), np.nan, dtype=np.float32)
    stbd_g = np.full((n, m), np.nan, dtype=np.float32)
    grazing = np.full((n, m), np.nan, dtype=np.float32)
    for i in range(n):
        if gap_rows[i]:
            continue
        port_g[i] = to_ground_range(port_fix.data[i], spacing[i], altitude[i], grid)
        stbd_g[i] = to_ground_range(stbd_fix.data[i], spacing[i], altitude[i], grid)
        grazing[i] = grazing_angle_deg(grid, altitude[i])
    if equalise:
        # Short surveys must not be wiped out by the default min_count of 10.
        min_count = max(1, min(10, int((~gap_rows).sum())))
        port_g = across_track_equalise(port_g, min_count=min_count)
        stbd_g = across_track_equalise(stbd_g, min_count=min_count)
    not_port = ~np.isfinite(port_g) | gap_rows[:, None]
    not_stbd = ~np.isfinite(stbd_g) | gap_rows[:, None]

    quality = compute_quality(
        times=np.array([p.time for p in pings], dtype="datetime64[ms]"),
        ping_numbers=np.array([p.ping_number for p in pings]),
        roll_deg=np.array([p.roll_deg for p in pings]),
        pitch_deg=np.array([p.pitch_deg for p in pings]),
        altitude_m=altitude,
        slant_range_m=slant,
        swath=combined,
        gap_rows=gap_rows,
        repaired_rows=repaired_rows,
        nav_missing=np.array([str(p.nav_source) == "missing" for p in pings]),
        thresholds=thresholds,
    )
    return NormalisedSwath(
        ground_res_m=res,
        ground_m=grid,
        port=port_g,
        stbd=stbd_g,
        grazing_deg=grazing,
        not_searched_port=not_port,
        not_searched_stbd=not_stbd,
        altitude_m=altitude,
        altitude_source=altitude_source,
        x=np.array([p.x for p in pings]),
        y=np.array([p.y for p in pings]),
        coord_kind=[str(p.coord_kind) for p in pings],
        nav_source=[str(p.nav_source) for p in pings],
        heading_deg=np.array([p.heading_deg for p in pings]),
        times=np.array([p.time for p in pings], dtype="datetime64[ms]"),
        quality=quality,
        sensor=record.sensor,
        provenance=record.provenance,
    )
