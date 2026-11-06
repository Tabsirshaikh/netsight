"""Side-scan geometry: altitude, slant-to-ground range and grazing angle (flat-seabed model)."""

from __future__ import annotations

import math
import warnings

import numpy as np


def _nan_median_filter(x: np.ndarray, window: int) -> np.ndarray:
    if window <= 1 or x.size == 0:
        return x.copy()
    half = window // 2
    padded = np.pad(x, half, mode="constant", constant_values=np.nan)
    windows = np.lib.stride_tricks.sliding_window_view(padded, 2 * half + 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(windows, axis=1)


def bottom_track(
    channel: np.ndarray,
    sample_spacing_m: float,
    *,
    frac: float = 0.5,
    run: int = 3,
    smooth_pings: int = 5,
    min_alt_m: float = 0.3,
) -> np.ndarray:
    """First seabed return per ping: first `run` consecutive samples above frac * p90."""
    data = np.nan_to_num(np.asarray(channel, dtype=np.float64), nan=0.0)
    n_pings = data.shape[0]
    start = int(math.ceil(min_alt_m / sample_spacing_m))
    alt = np.full(n_pings, np.nan)
    kernel = np.ones(run, dtype=np.int64)
    for i in range(n_pings):
        row = data[i]
        p90 = np.percentile(row, 90)
        if p90 <= 0:
            continue
        above = (row[start:] > frac * p90).astype(np.int64)
        if above.size < run:
            continue
        hits = np.nonzero(np.convolve(above, kernel, mode="valid") == run)[0]
        if hits.size:
            alt[i] = (hits[0] + start) * sample_spacing_m
    return _nan_median_filter(alt, smooth_pings)


def fuse_altitude(
    recorded: np.ndarray, tracked: np.ndarray, *, tol_m: float = 1.0
) -> tuple[np.ndarray, list[str]]:
    """Use the recorded altitude when it agrees with the bottom track (or no track exists)."""
    recorded = np.asarray(recorded, dtype=np.float64)
    tracked = np.asarray(tracked, dtype=np.float64)
    out = np.full(recorded.shape, np.nan)
    sources: list[str] = []
    for i, (rec, trk) in enumerate(zip(recorded, tracked, strict=True)):
        if math.isfinite(rec) and (not math.isfinite(trk) or abs(rec - trk) <= tol_m):
            out[i] = rec
            sources.append("recorded")
        elif math.isfinite(trk):
            out[i] = trk
            sources.append("bottom_track")
        else:
            sources.append("missing")
    return out, sources


def ground_range_grid(max_ground_m: float, ground_res_m: float) -> np.ndarray:
    n = int(math.ceil(max_ground_m / ground_res_m))
    return (np.arange(n) + 0.5) * ground_res_m


def to_ground_range(
    row: np.ndarray, sample_spacing_m: float, altitude_m: float, grid: np.ndarray
) -> np.ndarray:
    """Resample one near->far channel onto a ground-range grid. Nadir gap and gaps stay NaN."""
    out = np.full(grid.shape, np.nan, dtype=np.float32)
    if not (math.isfinite(altitude_m) and altitude_m > 0):
        return out
    row = np.asarray(row, dtype=np.float64)
    slant = (np.arange(row.size) + 0.5) * sample_spacing_m
    ok = (slant > altitude_m) & np.isfinite(row)
    if ok.sum() < 2:
        return out
    ground = np.sqrt(slant[ok] ** 2 - altitude_m**2)
    out[:] = np.interp(grid, ground, row[ok], left=np.nan, right=np.nan)
    return out


def grazing_angle_deg(grid: np.ndarray, altitude_m: float) -> np.ndarray:
    if not (math.isfinite(altitude_m) and altitude_m > 0):
        return np.full(np.shape(grid), np.nan, dtype=np.float32)
    return np.degrees(np.arctan2(altitude_m, np.asarray(grid, dtype=np.float64))).astype(np.float32)
