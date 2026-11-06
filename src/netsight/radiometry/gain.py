"""Radiometric normalisation for ground-range swaths (rows = pings, columns = range bins)."""

from __future__ import annotations

import warnings

import numpy as np


def across_track_equalise(swath: np.ndarray, *, block: int = 200, eps: float = 1e-6) -> np.ndarray:
    """Divide each range column by its mean over ping blocks (empirical beam-pattern/TVG fix)."""
    data = np.asarray(swath, dtype=np.float64)
    out = np.full(data.shape, np.nan, dtype=np.float64)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for start in range(0, data.shape[0], block):
            chunk = data[start : start + block]
            col_mean = np.nanmean(chunk, axis=0)
            level = np.nanmean(col_mean)
            out[start : start + block] = chunk / (col_mean + eps) * level
    return out.astype(np.float32)


def to_log(x: np.ndarray, *, floor: float = 1e-3) -> np.ndarray:
    """Intensity to decibels; multiplicative speckle becomes additive. NaN stays NaN."""
    arr = np.asarray(x, dtype=np.float64)
    with np.errstate(invalid="ignore"):
        return (10.0 * np.log10(np.where(np.isnan(arr), np.nan, np.maximum(arr, floor)))).astype(
            np.float32
        )
