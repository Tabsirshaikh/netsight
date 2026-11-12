"""WP4 fusion: combine the detector score with L3 evidence features into P(real).

A small L2-regularised logistic model on [logit(raw score), evidence features], fitted on
validation detections and judged on held-out test detections against the score-only beta
calibration. Features are standardised with validation statistics. Ablation drops one feature
group at a time; a group earns its place only if removing it makes held-out log loss worse.
Evidence stays a soft input: no feature can veto a contact.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

EPS = 1e-6

FEATURE_GROUPS: dict[str, tuple[str, ...]] = {
    "shadow": ("shadow_present", "shadow_length_px", "shadow_contrast"),
    "texture": ("periodicity_ratio", "gabor_energy"),
    "lines": ("line_strength", "line_length_px"),
    "ripple": ("ripple_coherence_ring", "ripple_coherence_box", "ripple_deviation"),
    "anomaly": ("anomaly_score",),
    "size": ("log_side_px", "log_aspect"),
}


def feature_matrix(
    rows: Sequence[Mapping[str, float | bool | None]], names: Sequence[str]
) -> NDArray[np.float64]:
    """Rows of evidence dicts -> float matrix; None/NaN become 0 (feature absent)."""
    out = np.zeros((len(rows), len(names)))
    for i, r in enumerate(rows):
        for j, n in enumerate(names):
            v = r.get(n)
            out[i, j] = 0.0 if v is None or not np.isfinite(float(v)) else float(v)
    return out


def _logit(p: NDArray) -> NDArray:
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


@dataclass
class FusionModel:
    names: tuple[str, ...]
    mean: NDArray[np.float64]
    std: NDArray[np.float64]
    coef: NDArray[np.float64]  # [intercept, score, features...]

    def _design(self, scores: NDArray, feats: NDArray) -> NDArray:
        z = (feats - self.mean) / self.std if feats.shape[1] else feats
        return np.column_stack([np.ones(len(scores)), _logit(scores), z])

    def predict(self, scores: NDArray, feats: NDArray) -> NDArray[np.float64]:
        eta = self._design(np.asarray(scores, float), np.asarray(feats, float)) @ self.coef
        return 1 / (1 + np.exp(-eta))


def fit_fusion(
    scores: NDArray, feats: NDArray, labels: NDArray, names: Sequence[str], *, l2: float = 1.0
) -> FusionModel:
    """Fit by penalised maximum likelihood (intercept and score weight not penalised)."""
    scores = np.asarray(scores, float)
    feats = np.asarray(feats, float).reshape(len(scores), -1)
    y = np.asarray(labels, float)
    if len(np.unique(y)) != 2:
        raise ValueError("fusion needs both real and false detections")
    mean = feats.mean(0) if feats.shape[1] else np.zeros(0)
    std = feats.std(0) if feats.shape[1] else np.zeros(0)
    std = np.where(std > 0, std, 1.0)
    model = FusionModel(tuple(names), mean, std, np.zeros(2 + feats.shape[1]))
    x = model._design(scores, feats)
    penalty = np.r_[0.0, 0.0, np.full(feats.shape[1], l2)]

    def objective(w: NDArray) -> tuple[float, NDArray]:
        eta = x @ w
        loss = np.mean(np.logaddexp(0, eta) - y * eta) + 0.5 * np.sum(penalty * w**2) / len(y)
        grad = x.T @ (1 / (1 + np.exp(-eta)) - y) / len(y) + penalty * w / len(y)
        return float(loss), grad

    w0 = np.zeros(x.shape[1])
    w0[1] = 1.0
    res = minimize(objective, w0, jac=True, method="L-BFGS-B")
    model.coef = res.x
    return model


def log_loss(p: NDArray, y: NDArray) -> float:
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
