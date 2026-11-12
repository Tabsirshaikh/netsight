"""Turn injection trials into Pd tables with lower bounds, and check injection realism.

Detection of a trial is decided at its survey's own operating threshold (the label-free count
threshold computed on the survey's detections before injection), so Pd is stated for the same
false-alarm budget the survey's contacts are reported at.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence

import numpy as np

from netsight.trust.bounds import clopper_pearson, one_sided_lower
from netsight.trust.injection import Trial


def _row(key: dict, k: int, n: int, alpha: float) -> dict:
    lo, hi = clopper_pearson(k, n, alpha=alpha) if n else (float("nan"), float("nan"))
    return {
        **key,
        "n": n,
        "detected": k,
        "pd": k / n if n else float("nan"),
        "pd_lower": one_sided_lower(k, n, alpha=alpha) if n else float("nan"),
        "ci_low": float(lo),
        "ci_high": float(hi),
    }


def pd_table(
    trials: Sequence[Trial],
    thresholds: Mapping[str, float],
    *,
    by: Sequence[str] = ("kind", "stratum"),
    alpha: float = 0.10,
    key_fn: Mapping[str, Callable[[Trial], str]] | None = None,
) -> list[dict]:
    """Pd per combination of ``by`` fields; ``pd_lower`` is one-sided at 1 - alpha."""
    extra = dict(key_fn or {})
    counts: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    for t in trials:
        if t.group not in thresholds:
            raise ValueError(f"no threshold for survey {t.group!r}")
        key = tuple(extra[f](t) if f in extra else str(getattr(t, f)) for f in by)
        c = counts[key]
        c[0] += int(t.detected(thresholds[t.group]))
        c[1] += 1
    return [
        _row(dict(zip(by, key, strict=True)), k, n, alpha) for key, (k, n) in sorted(counts.items())
    ]


def range_bin(edges: Sequence[float]) -> Callable[[Trial], str]:
    """Key function binning ``rel_x`` (across-track position) by ``edges``."""
    e = list(edges)

    def key(t: Trial) -> str:
        i = int(np.clip(np.searchsorted(e, t.rel_x, side="right") - 1, 0, len(e) - 2))
        return f"{e[i]:.2f}-{e[i + 1]:.2f}"

    return key


def realism_check(
    injected_detected: int,
    injected_n: int,
    real_detected: int,
    real_n: int,
    *,
    alpha: float = 0.05,
) -> dict:
    """Compare Pd on injected targets with recall on real labelled targets (same threshold).

    ``consistent`` is True when the two (1 - alpha) Clopper-Pearson intervals overlap. Injected
    Pd far above real recall means the injected targets are easier than real ones and Pd from
    injection would be optimistic: such Pd must not be reported as calibrated.
    """
    inj = _row({}, injected_detected, injected_n, alpha)
    real = _row({}, real_detected, real_n, alpha)
    overlap = (
        injected_n > 0
        and real_n > 0
        and inj["ci_low"] <= real["ci_high"]
        and real["ci_low"] <= inj["ci_high"]
    )
    if not overlap and injected_n and real_n:
        verdict = "optimistic" if inj["pd"] > real["pd"] else "pessimistic"
    else:
        verdict = "consistent" if overlap else "insufficient"
    return {
        "injected_pd": inj["pd"],
        "injected_ci": [inj["ci_low"], inj["ci_high"]],
        "injected_n": injected_n,
        "real_recall": real["pd"],
        "real_ci": [real["ci_low"], real["ci_high"]],
        "real_n": real_n,
        "consistent": bool(overlap),
        "verdict": verdict,
    }
