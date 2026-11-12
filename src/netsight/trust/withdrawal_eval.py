"""WP7 acceptance measurement: does the applicability gate flag the survey blocks where
NetSight's calibrated claims actually fail?

Units are consecutive blocks of a held-out test survey. For each block:
- gate score: how far the block's detection geometry lies outside the training envelope of the
  same kind of data (0 inside), and the gate's own decision (calibrated / indicative);
- outcome "claims failed": the block's calibration error of calibrated probabilities exceeds a
  pre-set limit, or its recall at the survey budget falls below the validation recall interval.

Reported: AUROC of the gate score for "claims failed", and failure rates among flagged and
passed blocks. The limits are fixed here, before results are looked at.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np

ECE_LIMIT = 0.10
BLOCK_IMAGES = 50
MIN_BLOCK_DETECTIONS = 20


def auroc(scores: Sequence[float], labels: Sequence[bool]) -> float:
    """Mann-Whitney AUROC (ties count half); NaN when one class is empty."""
    s = np.asarray(scores, float)
    y = np.asarray(labels, bool)
    pos, neg = s[y], s[~y]
    if not len(pos) or not len(neg):
        return float("nan")
    greater = (pos[:, None] > neg[None, :]).sum()
    ties = (pos[:, None] == neg[None, :]).sum()
    return float((greater + 0.5 * ties) / (len(pos) * len(neg)))


def envelope_distance(
    median_log_aspect: float,
    median_side_px: float,
    log_aspect_range: tuple[float, float],
    side_px_range: tuple[float, float],
) -> float:
    """Distance outside the envelope in log units (aspect plus log object size); 0 inside.
    NaN inputs (too few boxes to estimate) give NaN."""
    if not (np.isfinite(median_log_aspect) and np.isfinite(median_side_px)):
        return float("nan")
    lo, hi = log_aspect_range
    d_aspect = max(lo - median_log_aspect, 0.0, median_log_aspect - hi)
    slo, shi = np.log(side_px_range[0]), np.log(side_px_range[1])
    ls = np.log(median_side_px)
    d_side = max(slo - ls, 0.0, ls - shi)
    return float(d_aspect + d_side)


@dataclass(frozen=True)
class BlockResult:
    dataset: str
    survey: str
    block: int
    n_images: int
    n_detections: int
    gate_level: str
    gate_distance: float
    ece: float
    recall: float
    recall_floor: float
    failed: bool
    failure: str

    def to_dict(self) -> dict:
        return asdict(self)


def summarise(blocks: Sequence[BlockResult]) -> dict:
    """AUROC and flagged/passed failure rates over blocks with an estimable gate score."""
    from netsight.trust.bounds import clopper_pearson

    usable = [b for b in blocks if np.isfinite(b.gate_distance)]
    flagged = [b for b in blocks if b.gate_level != "calibrated"]
    passed = [b for b in blocks if b.gate_level == "calibrated"]

    def rate(group: list[BlockResult]) -> dict:
        k, n = sum(b.failed for b in group), len(group)
        lo, hi = clopper_pearson(k, n) if n else (float("nan"), float("nan"))
        return {"failed": k, "n": n, "rate": k / n if n else float("nan"), "ci95": [lo, hi]}

    return {
        "blocks": len(blocks),
        "blocks_with_gate_score": len(usable),
        "auroc_distance": auroc([b.gate_distance for b in usable], [b.failed for b in usable]),
        "flagged": rate(flagged),
        "passed": rate(passed),
        "ece_limit": ECE_LIMIT,
        "block_images": BLOCK_IMAGES,
    }
