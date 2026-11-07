"""Ping dropout handling: repair isolated bad rows, keep long gaps visible as not searched."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DropoutResult:
    data: np.ndarray
    repaired_rows: np.ndarray
    gap_rows: np.ndarray


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    runs, start = [], None
    for i, bad in enumerate(mask):
        if bad and start is None:
            start = i
        elif not bad and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, mask.size))
    return runs


def repair_dropouts(
    swath: np.ndarray, *, zero_fraction: float = 0.95, max_interp_rows: int = 2
) -> DropoutResult:
    data = np.asarray(swath, dtype=np.float32).copy()
    n = data.shape[0]
    empty = (data == 0) | np.isnan(data)
    bad = empty.mean(axis=1) > zero_fraction
    repaired = np.zeros(n, dtype=bool)
    gap = np.zeros(n, dtype=bool)
    for start, stop in _runs(bad):
        length = stop - start
        if length <= max_interp_rows and start > 0 and stop < n:
            left, right = data[start - 1], data[stop]
            for k, row in enumerate(range(start, stop), start=1):
                w = k / (length + 1)
                data[row] = (1 - w) * left + w * right
            repaired[start:stop] = True
        else:
            data[start:stop] = np.nan
            gap[start:stop] = True
    return DropoutResult(data=data, repaired_rows=repaired, gap_rows=gap)
