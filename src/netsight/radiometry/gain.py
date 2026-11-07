"""Radiometric normalisation for ground-range swaths (rows = pings, columns = range bins)."""

from __future__ import annotations

import warnings

import numpy as np


def _block_slices(n_pings: int, block: int) -> list[slice]:
    """Ping blocks of `block` rows; a tail shorter than `block // 2` merges into the previous."""
    starts = list(range(0, n_pings, block))
    slices = [slice(s, min(s + block, n_pings)) for s in starts]
    if len(slices) > 1 and n_pings - starts[-1] < block // 2:
        tail = slices.pop()
        slices[-1] = slice(slices[-1].start, tail.stop)
    return slices


def across_track_equalise(
    swath: np.ndarray, *, block: int = 200, min_count: int = 10, eps: float = 1e-6
) -> np.ndarray:
    """Divide each range column by its median over ping blocks (empirical beam-pattern/TVG fix).

    `swath` must be non-negative linear intensity (not dB). Each block's column levels are the
    per-column `nanmedian`; the output is rescaled to the median of those levels. Columns with
    fewer than `min_count` finite values in a block come out NaN for that block, as do columns
    whose level is `<= eps` (e.g. a median of 0), which would otherwise be amplified by ~1/eps;
    such columns are excluded from the block level. Blocks are `block` pings long; a short tail
    (< `block // 2`) is merged into the previous block. Swaths (or tails) with fewer than
    `min_count` pings therefore produce NaN; `min_count > block` raises ValueError.

    Equalisation is empirical: an along-track feature spanning more than half a block's pings
    pulls the column median and can still be partly or wholly erased.
    """
    if block < 1:
        raise ValueError(f"block must be >= 1, got {block}")
    if min_count < 1:
        raise ValueError(f"min_count must be >= 1, got {min_count}")
    if min_count > block:
        raise ValueError(f"min_count ({min_count}) must be <= block ({block})")
    data = np.asarray(swath, dtype=np.float64)
    out = np.full(data.shape, np.nan, dtype=np.float64)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for rows in _block_slices(data.shape[0], block):
            chunk = data[rows]
            col_level = np.nanmedian(chunk, axis=0)
            col_level[np.isfinite(chunk).sum(axis=0) < min_count] = np.nan
            col_level[col_level <= eps] = np.nan
            level = np.nanmedian(col_level)
            out[rows] = chunk / (col_level + eps) * level
    return out.astype(np.float32)


def to_log(x: np.ndarray, *, floor: float = 1e-3) -> np.ndarray:
    """Intensity to decibels; multiplicative speckle becomes additive. NaN stays NaN."""
    arr = np.asarray(x, dtype=np.float64)
    with np.errstate(invalid="ignore"):
        return (10.0 * np.log10(np.where(np.isnan(arr), np.nan, np.maximum(arr, floor)))).astype(
            np.float32
        )
