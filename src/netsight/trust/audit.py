"""Operator audits that repair what label-free checks cannot see (research 2026-11-13).

Contact audit: the operator confirms or rejects a RANDOM sample of the survey's candidate
detections (not the top-ranked ones: a top-N sample made recalibration worse on held-out
surveys). On the sensor-shifted Contact recording, 50-100 random decisions cut calibration
error from 0.083 to 0.044-0.035; on surveys that pass the applicability gate the update adds
nothing, so the dashboard asks for it only when the gate says "indicative".

Recall audit: the operator marks every object in a few random images; a one-sided binomial
test says whether recall there is below the validation recall. In simulation on the held-out
test blocks, 30 images caught 82% of significant recall drops (the within-sensor drops the
geometry gate misses) with 2% false flags; 10 images caught 46%.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

CONTACT_AUDIT_SIZE = 50
RECALL_AUDIT_IMAGES = 30
MIN_AUDIT_OBJECTS = 10
PRIOR_STRENGTH = 2.0  # L2 pull of the update towards "no change" (slope 1, intercept 0)


def sample_audit(scores: ArrayLike, n: int, rng: np.random.Generator) -> list[int]:
    """Indices of a uniform random sample of ``n`` candidates (all of them when fewer)."""
    s = np.asarray(scores, float).reshape(-1)
    if s.size <= n:
        return list(range(s.size))
    return sorted(int(i) for i in rng.choice(s.size, n, replace=False))


def _logit(p: NDArray) -> NDArray:
    q = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(q / (1 - q))


class Recalibration:
    """P(real) update on the logit scale: logit(p') = slope * logit(p) + intercept."""

    def __init__(self, slope: float, intercept: float) -> None:
        self.slope, self.intercept = float(slope), float(intercept)

    def apply(self, p: ArrayLike) -> NDArray[np.float64]:
        return 1 / (1 + np.exp(-(self.slope * _logit(np.asarray(p, float)) + self.intercept)))

    def to_dict(self) -> dict:
        return {"slope": self.slope, "intercept": self.intercept}


def fit_recalibration(
    probabilities: ArrayLike, real: ArrayLike, prior_strength: float = PRIOR_STRENGTH
) -> Recalibration:
    """Penalised logistic fit of audit outcomes on the shown probabilities' logits."""
    from scipy.optimize import minimize

    z = _logit(np.asarray(probabilities, float).reshape(-1))
    y = np.asarray(real, float).reshape(-1)
    if z.size != y.size or not np.isin(y, (0.0, 1.0)).all():
        raise ValueError("one 0/1 outcome per audited probability is required")

    def loss(w: NDArray) -> float:
        eta = w[0] * z + w[1]
        nll = np.sum(np.logaddexp(0, eta) - y * eta)
        return float(nll + prior_strength * ((w[0] - 1) ** 2 + w[1] ** 2))

    w = minimize(loss, np.array([1.0, 0.0]), method="BFGS").x
    return Recalibration(w[0], w[1])


def calibration_check(probabilities: ArrayLike, real: ArrayLike, alpha: float = 0.05) -> dict:
    """Do the audited outcomes agree with the shown probabilities? (Poisson-binomial z-test.)"""
    from scipy.stats import norm

    p = np.asarray(probabilities, float).reshape(-1)
    y = np.asarray(real, float).reshape(-1)
    expected, var = float(p.sum()), float(np.sum(p * (1 - p)))
    z = (float(y.sum()) - expected) / np.sqrt(var) if var > 0 else 0.0
    pval = float(2 * norm.sf(abs(z)))
    return {
        "n": int(p.size),
        "predicted": expected / max(p.size, 1),
        "observed": float(y.mean()) if y.size else float("nan"),
        "p_value": pval,
        "consistent": bool(pval >= alpha),
    }


def recall_audit(
    detected: int, objects: int, validation_recall: float, alpha: float = 0.05
) -> dict:
    """One-sided binomial test of audited recall against the validation recall."""
    from scipy.stats import binom

    out = {
        "detected": int(detected),
        "objects": int(objects),
        "recall": detected / objects if objects else float("nan"),
        "validation_recall": float(validation_recall),
    }
    if objects < MIN_AUDIT_OBJECTS:
        return {
            **out,
            "p_value": None,
            "below_validation": None,
            "note": f"too few objects marked ({objects} < {MIN_AUDIT_OBJECTS}); audit more images",
        }
    pval = float(binom.cdf(detected, objects, validation_recall))
    return {**out, "p_value": pval, "below_validation": bool(pval < alpha), "note": ""}
