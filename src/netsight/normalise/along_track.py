"""Square pixels from sonar metadata: resample waterfall rows by distance travelled.

The swath normaliser puts every ping on a fixed ground-range grid across track, but keeps one row
per ping along track, so the along-track pixel size is (vessel speed / ping rate) and changes with
the sonar settings and the boat. Test B showed this pixel-aspect shift is what hurts the detector
on another sensor (Contact recording: AP50 0.18 -> 0.37 after correcting it). Here the along-track
spacing comes from the recorded navigation, never from the image content.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from netsight.navigation.provenance import METRES_PER_DEG_LAT


def ping_distances(x: np.ndarray, y: np.ndarray, coord_kind: list[str] | np.ndarray) -> np.ndarray:
    """Distance travelled from the previous ping (m); NaN for the first ping and missing nav."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    kinds = np.asarray(coord_kind)
    d = np.full(len(x), np.nan)
    for i in range(1, len(x)):
        if kinds[i] != kinds[i - 1] or kinds[i] == "none":
            continue
        dx, dy = x[i] - x[i - 1], y[i] - y[i - 1]
        if kinds[i] == "latlon":
            dx *= METRES_PER_DEG_LAT * np.cos(np.radians((y[i] + y[i - 1]) / 2))
            dy *= METRES_PER_DEG_LAT
        d[i] = float(np.hypot(dx, dy))
    return d


def robust_spacing(d: np.ndarray, window: int = 25) -> tuple[np.ndarray, float]:
    """Per-ping spacing smoothed with a running median (navigation is noisy at ping scale);
    gaps are filled with the overall median. Returns (spacing, fraction of pings with nav)."""
    d = np.asarray(d, float)
    ok = np.isfinite(d) & (d >= 0)
    if ok.sum() < 3:
        raise ValueError("not enough navigation to measure along-track spacing")
    med = float(np.median(d[ok]))
    filled = np.where(ok, d, med)
    half = window // 2
    padded = np.pad(filled, half, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, 2 * half + 1)
    return np.median(windows, axis=1), float(ok.mean())


@dataclass(frozen=True)
class SquareWaterfall:
    image: np.ndarray  # (rows, cols), along track down, square pixels
    row_to_ping: np.ndarray  # fractional ping index for every output row
    pixel_m: float  # metres per pixel in both directions
    native_along_m: float  # median along-track spacing before resampling
    nav_fraction: float  # share of pings with usable navigation
    stretch: float  # rows out / rows in (> 1 means rows were added)

    def ping_of_row(self, row: float) -> float:
        """Fractional source ping for a (fractional) output row, for geolocating detections."""
        return float(np.interp(row, np.arange(len(self.row_to_ping)), self.row_to_ping))


def square_waterfall(
    image: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    coord_kind: list[str] | np.ndarray,
    across_m: float,
    *,
    max_stretch: float = 8.0,
) -> SquareWaterfall:
    """Resample the rows of a ground-range waterfall (one row per ping) to ``across_m`` spacing."""
    image = np.asarray(image)
    if image.ndim != 2 or image.shape[0] != len(x):
        raise ValueError("image must have one row per ping")
    if not across_m > 0:
        raise ValueError("across_m must be positive")
    spacing, frac = robust_spacing(ping_distances(x, y, coord_kind))
    spacing[0] = spacing[1] if len(spacing) > 1 else spacing[0]
    cum = np.concatenate([[0.0], np.cumsum(spacing[1:])])
    total = cum[-1]
    n_out = max(int(np.floor(total / across_m + 1e-9)) + 1, 1)
    stretch = n_out / image.shape[0]
    if not (1 / max_stretch <= stretch <= max_stretch):
        raise ValueError(f"implausible along-track stretch {stretch:.2f}: check navigation")
    targets = np.arange(n_out) * across_m
    src = np.interp(targets, cum, np.arange(image.shape[0], dtype=float))
    lo = np.floor(src).astype(int)
    hi = np.minimum(lo + 1, image.shape[0] - 1)
    w = (src - lo)[:, None]
    out = (1 - w) * image[lo].astype(np.float64) + w * image[hi].astype(np.float64)
    out = np.where(np.isnan(out), np.nan, out)
    if np.issubdtype(image.dtype, np.integer):
        out = np.clip(
            np.rint(np.nan_to_num(out)), np.iinfo(image.dtype).min, np.iinfo(image.dtype).max
        ).astype(image.dtype)
    return SquareWaterfall(
        image=out,
        row_to_ping=src,
        pixel_m=float(across_m),
        native_along_m=float(np.median(spacing[1:])) if len(spacing) > 1 else float("nan"),
        nav_fraction=frac,
        stretch=float(stretch),
    )
