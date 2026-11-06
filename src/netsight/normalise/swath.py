"""Layer L1: turn a SonarRecord into a QC'd, ground-range, geometry-aware swath."""

from __future__ import annotations

import json
import math
import warnings
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from netsight.core.records import Provenance, SensorDescriptor, SonarRecord
from netsight.geometry.slant import (
    bottom_track,
    fuse_altitude,
    grazing_angle_deg,
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
    equalise_rejected_port: np.ndarray
    equalise_rejected_stbd: np.ndarray
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
            "ground_res_m": float(self.ground_res_m),
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
            "equalise_rejected_cells": {
                "port": int(self.equalise_rejected_port.sum()),
                "stbd": int(self.equalise_rejected_stbd.sum()),
            },
        }

    def to_npz(self, path: str | Path) -> Path:
        path = Path(path)
        if path.suffix != ".npz":
            path = path.with_name(path.name + ".npz")
        np.savez_compressed(
            path,
            ground_m=self.ground_m,
            port=self.port,
            stbd=self.stbd,
            grazing_deg=self.grazing_deg,
            not_searched_port=self.not_searched_port,
            not_searched_stbd=self.not_searched_stbd,
            equalise_rejected_port=self.equalise_rejected_port,
            equalise_rejected_stbd=self.equalise_rejected_stbd,
            altitude_m=self.altitude_m,
            altitude_source=np.array(self.altitude_source, dtype="U16"),
            coord_kind=np.array(self.coord_kind, dtype="U16"),
            nav_source=np.array(self.nav_source, dtype="U16"),
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
    if ground_res_m is not None and not (math.isfinite(ground_res_m) and ground_res_m > 0):
        raise ValueError(f"ground_res_m must be a positive number, got {ground_res_m}")
    port_raw = record.channel_matrix("port")
    stbd_raw = record.channel_matrix("stbd")
    pings = record.pings
    spacing = np.array([p.sample_spacing_m for p in pings])
    n_samples = pings[0].n_samples

    port_fix = repair_dropouts(port_raw)
    stbd_fix = repair_dropouts(stbd_raw)
    gap_port, gap_stbd = port_fix.gap_rows, stbd_fix.gap_rows
    both_gap = gap_port & gap_stbd
    side_only = gap_port ^ gap_stbd
    repaired_rows = (port_fix.repaired_rows | stbd_fix.repaired_rows) & ~both_gap
    notes = list(record.provenance.notes)
    for name, gap in (("port", gap_port), ("starboard", gap_stbd)):
        if gap.all():
            notes.append(f"{name} channel has no usable data")
    provenance = replace(record.provenance, notes=notes)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        combined = np.nanmean(np.stack([port_fix.data, stbd_fix.data]), axis=0)
    # Bottom-track each group of pings that share a sample spacing with that group's spacing.
    tracked = np.full(len(pings), np.nan)
    spacing_key = np.round(spacing / spacing[0], 9)
    for key in np.unique(spacing_key):
        idx = np.nonzero(spacing_key == key)[0]
        tracked[idx] = bottom_track(combined[idx], float(np.median(spacing[idx])))
    recorded = np.array([p.altitude_m for p in pings])
    altitude, altitude_source = fuse_altitude(recorded, tracked)
    if not np.isfinite(altitude).any():
        raise ValueError(
            "no altitude available (recorded or bottom-tracked); cannot convert to ground range"
        )

    native = float(np.median(spacing))
    res = ground_res_m if ground_res_m is not None else choose_ground_resolution(native)
    last_centre = (n_samples - 0.5) * spacing
    usable = np.isfinite(altitude) & (altitude < last_centre)
    if not usable.any():
        raise ValueError(
            f"altitude exceeds slant range (min altitude {float(np.nanmin(altitude)):.2f} m, "
            f"max slant range {float(last_centre.max()):.2f} m); cannot convert to ground range"
        )
    g_last = float(np.sqrt(last_centre[usable] ** 2 - altitude[usable] ** 2).max())
    n_bins = max(1, math.floor(g_last / res + 0.5))
    grid = (np.arange(n_bins) + 0.5) * res
    n, m = len(pings), grid.size
    port_g = np.full((n, m), np.nan, dtype=np.float32)
    stbd_g = np.full((n, m), np.nan, dtype=np.float32)
    grazing = np.full((n, m), np.nan, dtype=np.float32)
    for i in range(n):
        if both_gap[i]:
            continue
        if not gap_port[i]:
            port_g[i] = to_ground_range(port_fix.data[i], spacing[i], altitude[i], grid)
        if not gap_stbd[i]:
            stbd_g[i] = to_ground_range(stbd_fix.data[i], spacing[i], altitude[i], grid)
        grazing[i] = grazing_angle_deg(grid, altitude[i])
    # Coverage is decided before equalisation; equaliser rejections are recorded separately.
    not_port = ~np.isfinite(port_g)
    not_stbd = ~np.isfinite(stbd_g)
    rejected_port = np.zeros_like(not_port)
    rejected_stbd = np.zeros_like(not_stbd)
    if equalise:
        # Short surveys must not be wiped out by the default min_count of 10.
        eq_port = across_track_equalise(port_g, min_count=max(1, min(10, int((~gap_port).sum()))))
        eq_stbd = across_track_equalise(stbd_g, min_count=max(1, min(10, int((~gap_stbd).sum()))))
        rejected_port = ~not_port & ~np.isfinite(eq_port)
        rejected_stbd = ~not_stbd & ~np.isfinite(eq_stbd)
        port_g, stbd_g = eq_port, eq_stbd

    quality = compute_quality(
        times=np.array([p.time for p in pings], dtype="datetime64[ms]"),
        ping_numbers=np.array([p.ping_number for p in pings]),
        roll_deg=np.array([p.roll_deg for p in pings]),
        pitch_deg=np.array([p.pitch_deg for p in pings]),
        altitude_m=altitude,
        slant_range_m=np.array([p.slant_range_m for p in pings]),
        swath=combined,
        gap_rows=both_gap,
        repaired_rows=repaired_rows,
        nav_missing=np.array([str(p.nav_source) == "missing" for p in pings]),
        side_dropout_rows=side_only,
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
        equalise_rejected_port=rejected_port,
        equalise_rejected_stbd=rejected_stbd,
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
        provenance=provenance,
    )
