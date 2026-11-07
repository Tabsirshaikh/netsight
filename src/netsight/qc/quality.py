"""Per-ping quality mask Q in [0, 1] with named reason flags."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SEVERITY: dict[str, float] = {
    "attitude": 0.5,
    "attitude_rate": 0.5,
    "altitude_missing": 0.3,
    "altitude_jump": 0.7,
    "towfish_height": 0.3,
    "stripe": 0.6,
    "dropout": 1.0,
    "side_dropout": 0.0,  # one side gapped: coverage is carried by per-side not_searched masks
    "repaired": 0.2,
    "ping_gap": 0.0,
    "nav_missing": 0.0,
}


@dataclass(frozen=True)
class QualityThresholds:
    max_roll_deg: float = 5.0
    max_pitch_deg: float = 5.0
    max_attitude_rate_deg_s: float = 3.0
    max_altitude_jump_m: float = 1.0
    towfish_height_min_frac: float = 0.08  # NOAA HSSD 6.1.2.3: towfish 8-20% of range scale
    towfish_height_max_frac: float = 0.20
    stripe_corr_min: float = 0.2


DEFAULT_THRESHOLDS = QualityThresholds()


@dataclass
class QualityMask:
    q: np.ndarray
    flags: dict[str, np.ndarray]

    def summary(self) -> dict:
        return {
            "mean_q": float(np.mean(self.q)) if self.q.size else float("nan"),
            "min_q": float(np.min(self.q)) if self.q.size else float("nan"),
            "flag_counts": {name: int(f.sum()) for name, f in self.flags.items()},
        }


def _row_corr(a: np.ndarray, b: np.ndarray) -> float:
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 10:
        return float("nan")
    a, b = a[ok], b[ok]
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def _stripe_rows(swath: np.ndarray, threshold: float) -> np.ndarray:
    n = swath.shape[0]
    out = np.zeros(n, dtype=bool)
    if n < 2:
        return out
    corr = np.array([_row_corr(swath[i], swath[i + 1]) for i in range(n - 1)])
    for i in range(n):
        neighbours = []
        if i > 0 and np.isfinite(corr[i - 1]):
            neighbours.append(corr[i - 1])
        if i < n - 1 and np.isfinite(corr[i]):
            neighbours.append(corr[i])
        out[i] = bool(neighbours) and all(c < threshold for c in neighbours)
    return out


def compute_quality(
    *,
    times: np.ndarray,
    ping_numbers: np.ndarray,
    roll_deg: np.ndarray,
    pitch_deg: np.ndarray,
    altitude_m: np.ndarray,
    slant_range_m: np.ndarray,
    swath: np.ndarray,
    gap_rows: np.ndarray,
    repaired_rows: np.ndarray,
    nav_missing: np.ndarray,
    side_dropout_rows: np.ndarray | None = None,
    thresholds: QualityThresholds = DEFAULT_THRESHOLDS,
) -> QualityMask:
    th = thresholds
    n = len(ping_numbers)
    t = np.asarray(times, dtype="datetime64[ms]").astype(np.int64) / 1000.0
    dt = np.diff(t, prepend=t[0] if n else 0.0)
    dt[dt <= 0] = np.nan
    roll = np.asarray(roll_deg, dtype=np.float64)
    pitch = np.asarray(pitch_deg, dtype=np.float64)
    alt = np.asarray(altitude_m, dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        d_att = np.fmax(
            np.abs(np.diff(roll, prepend=roll[:1])), np.abs(np.diff(pitch, prepend=pitch[:1]))
        )
        ratio = alt / np.asarray(slant_range_m, dtype=np.float64)
        flags = {
            "attitude": (np.abs(roll) > th.max_roll_deg) | (np.abs(pitch) > th.max_pitch_deg),
            "attitude_rate": (d_att / dt) > th.max_attitude_rate_deg_s,
            "altitude_missing": ~np.isfinite(alt),
            "altitude_jump": np.abs(np.diff(alt, prepend=alt[:1])) > th.max_altitude_jump_m,
            "towfish_height": np.isfinite(ratio)
            & ((ratio < th.towfish_height_min_frac) | (ratio > th.towfish_height_max_frac)),
        }
    flags["stripe"] = _stripe_rows(np.asarray(swath, dtype=np.float64), th.stripe_corr_min)
    flags["dropout"] = np.asarray(gap_rows, dtype=bool)
    flags["side_dropout"] = (
        np.zeros(n, dtype=bool)
        if side_dropout_rows is None
        else np.asarray(side_dropout_rows, dtype=bool)
    )
    flags["repaired"] = np.asarray(repaired_rows, dtype=bool)
    pn = np.asarray(ping_numbers, dtype=np.int64)
    flags["ping_gap"] = np.concatenate([[False], np.diff(pn) > 1]) if n else np.zeros(0, bool)
    flags["nav_missing"] = np.asarray(nav_missing, dtype=bool)
    q = np.ones(n)
    for name, f in flags.items():
        q *= np.where(f, 1.0 - SEVERITY[name], 1.0)
    return QualityMask(q=q.astype(np.float32), flags=flags)
