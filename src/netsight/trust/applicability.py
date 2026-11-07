"""Applicability gate: decide the claim level for a survey (plan section 9).

Claim levels:
- calibrated: inside the envelope the calibrator was validated on, injection canary passed;
- indicative: soft problems (calibrator not yet validated, no canary run, score drift);
  scores are relative only and no Pd is claimed;
- withdrawn: outside the envelope (hard gate) or the canary failed; no probabilities or Pd
  are shown, only a candidate list.

Missing metadata fails the hard gate: what cannot be checked is not assumed to match.
The soft embedding gate (kNN / Mahalanobis on detector features) is added with the detector.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike
from scipy.stats import binom, ks_2samp

RANGE_TOLERANCE = 0.10  # numeric conditions may exceed the seen range by 10%
DRIFT_ALPHA = 0.01
CANARY_ALPHA = 0.01
MIN_DRIFT_SCORES = 30

STATEMENTS = {
    "calibrated": (
        "Probabilities are calibrated for this survey: it lies inside the validated envelope "
        "of calibrator {calibrator_id} and the injection canary passed."
    ),
    "indicative": (
        "Scores are relative only: calibration is not valid for this survey. No probabilities "
        "of detection are claimed."
    ),
    "withdrawn": (
        "Outside the validated envelope: no probabilities or Pd are shown; candidate list only."
    ),
}


@dataclass(frozen=True)
class SurveyConditions:
    sensor_type: str
    model: str | None
    frequency_khz: float | None
    range_m: float | None  # slant range scale per side
    resolution_m: float | None  # ground resolution of the normalised swath
    processing_chain: str | None


@dataclass(frozen=True)
class Envelope:
    """Conditions covered by the calibration surveys."""

    sensor_types: frozenset[str]
    models: frozenset[str]
    frequency_khz: tuple[float, float]
    range_m: tuple[float, float]
    resolution_m: tuple[float, float]
    processing_chains: frozenset[str]
    calibrator_id: str
    calibrator_validated: bool

    @classmethod
    def from_surveys(
        cls,
        surveys: Sequence[SurveyConditions],
        *,
        calibrator_id: str,
        calibrator_validated: bool,
    ) -> Envelope:
        if not surveys:
            raise ValueError("an envelope needs at least one calibration survey")

        def span(name: str) -> tuple[float, float]:
            values = [getattr(s, name) for s in surveys]
            if any(v is None for v in values):
                raise ValueError(f"calibration survey without {name}")
            return float(min(values)), float(max(values))

        def names(name: str) -> frozenset[str]:
            values = {getattr(s, name) for s in surveys}
            if None in values:
                raise ValueError(f"calibration survey without {name}")
            return frozenset(values)

        return cls(
            sensor_types=names("sensor_type"),
            models=names("model"),
            frequency_khz=span("frequency_khz"),
            range_m=span("range_m"),
            resolution_m=span("resolution_m"),
            processing_chains=names("processing_chain"),
            calibrator_id=calibrator_id,
            calibrator_validated=calibrator_validated,
        )


def hard_gate(envelope: Envelope, survey: SurveyConditions) -> list[str]:
    """Reasons the survey falls outside the envelope; empty when it is inside."""
    reasons: list[str] = []

    def member(label: str, value: str | None, allowed: frozenset[str]) -> None:
        if value is None:
            reasons.append(f"{label} unknown")
        elif value not in allowed:
            reasons.append(f"{label} {value!r} not in calibration set {sorted(allowed)}")

    def within(label: str, value: float | None, span: tuple[float, float], unit: str) -> None:
        low, high = span[0] * (1 - RANGE_TOLERANCE), span[1] * (1 + RANGE_TOLERANCE)
        if value is None or not np.isfinite(value):
            reasons.append(f"{label} unknown")
        elif not low <= value <= high:
            reasons.append(
                f"{label} {value:g} {unit} outside calibrated {span[0]:g}-{span[1]:g} {unit}"
            )

    member("sensor type", survey.sensor_type, envelope.sensor_types)
    member("sonar model", survey.model, envelope.models)
    within("frequency", survey.frequency_khz, envelope.frequency_khz, "kHz")
    within("range scale", survey.range_m, envelope.range_m, "m")
    within("resolution", survey.resolution_m, envelope.resolution_m, "m")
    member("processing chain", survey.processing_chain, envelope.processing_chains)
    return reasons


@dataclass(frozen=True)
class DriftResult:
    statistic: float
    p_value: float
    drift: bool
    n_reference: int
    n_survey: int


def score_drift(
    reference_scores: ArrayLike, survey_scores: ArrayLike, *, alpha: float = DRIFT_ALPHA
) -> DriftResult:
    """Two-sample KS test of this survey's detector scores against the calibration scores."""
    ref = np.asarray(reference_scores, dtype=float).reshape(-1)
    new = np.asarray(survey_scores, dtype=float).reshape(-1)
    ref, new = ref[np.isfinite(ref)], new[np.isfinite(new)]
    if ref.size < MIN_DRIFT_SCORES or new.size < MIN_DRIFT_SCORES:
        raise ValueError(f"score drift needs at least {MIN_DRIFT_SCORES} scores on each side")
    test = ks_2samp(ref, new)
    p = float(test.pvalue)
    return DriftResult(float(test.statistic), p, bool(p < alpha), int(ref.size), int(new.size))


@dataclass(frozen=True)
class CanaryResult:
    n_injected: int
    n_detected: int
    expected: float
    p_value: float  # P(this few detections or fewer | predicted Pd)
    passed: bool


def canary_check(
    detected: ArrayLike, predicted_pd: ArrayLike, *, alpha: float = CANARY_ALPHA
) -> CanaryResult:
    """Did the detector find injected canary targets about as often as the Pd map predicts?

    Uses a binomial test at the mean predicted Pd (an approximation to the exact
    Poisson-binomial when predicted Pd varies between canaries).
    """
    d = np.asarray(detected, dtype=float).reshape(-1)
    pd = np.asarray(predicted_pd, dtype=float).reshape(-1)
    if d.size == 0 or d.size != pd.size:
        raise ValueError("detected and predicted_pd must be non-empty and the same length")
    if np.any((d != 0) & (d != 1)):
        raise ValueError("detected values must be 0 or 1")
    if not np.all(np.isfinite(pd) & (pd >= 0) & (pd <= 1)):
        raise ValueError("predicted_pd values must be in [0, 1]")
    k, n = int(d.sum()), int(d.size)
    p_value = float(binom.cdf(k, n, float(pd.mean())))
    return CanaryResult(n, k, float(pd.sum()), p_value, bool(p_value >= alpha))


@dataclass(frozen=True)
class ClaimDecision:
    level: str
    reasons: list[str]
    statement: str


def decide_claim_level(
    envelope: Envelope,
    survey: SurveyConditions,
    *,
    drift: DriftResult | None,
    canary: CanaryResult | None,
) -> ClaimDecision:
    hard = hard_gate(envelope, survey)
    if canary is not None and not canary.passed:
        hard.append(
            f"injection canary failed: {canary.n_detected} of {canary.n_injected} detected, "
            f"{canary.expected:.1f} expected (p = {canary.p_value:.2g})"
        )
    soft: list[str] = []
    if not envelope.calibrator_validated:
        soft.append(f"calibrator {envelope.calibrator_id} not yet validated on held-out surveys")
    if canary is None:
        soft.append("no injection canary run for this survey")
    if drift is not None and drift.drift:
        soft.append(f"detector score drift (KS = {drift.statistic:.2f}, p = {drift.p_value:.2g})")
    level = "withdrawn" if hard else "indicative" if soft else "calibrated"
    statement = STATEMENTS[level].format(calibrator_id=envelope.calibrator_id)
    return ClaimDecision(level, hard + soft, statement)
