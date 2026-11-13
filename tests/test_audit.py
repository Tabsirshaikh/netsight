import numpy as np
import pytest

from netsight.trust.audit import (
    CONTACT_AUDIT_SIZE,
    RECALL_AUDIT_IMAGES,
    Recalibration,
    calibration_check,
    fit_recalibration,
    recall_audit,
    sample_audit,
)


def test_sample_audit_is_random_not_top_scores():
    rng = np.random.default_rng(0)
    scores = np.linspace(0.1, 0.99, 400)
    idx = sample_audit(scores, CONTACT_AUDIT_SIZE, rng)
    assert len(idx) == CONTACT_AUDIT_SIZE == len(set(idx))
    # a top-N pick would take only the last 50; a random pick spans the score range
    assert scores[idx].min() < 0.4 and scores[idx].max() > 0.7


def test_sample_audit_takes_everything_when_few():
    assert sorted(sample_audit(np.array([0.2, 0.5]), 50, np.random.default_rng(0))) == [0, 1]


def test_recalibration_corrects_underconfident_probabilities():
    rng = np.random.default_rng(1)
    true_p = rng.uniform(0.05, 0.95, 4000)
    y = (rng.random(4000) < true_p).astype(float)
    shown = 1 / (1 + np.exp(-(np.log(true_p / (1 - true_p)) - 1.5)))  # too low by 1.5 logits
    audit = rng.choice(4000, 100, replace=False)
    rec = fit_recalibration(shown[audit], y[audit])
    fixed = rec.apply(shown)
    assert abs(fixed.mean() - y.mean()) < abs(shown.mean() - y.mean()) / 2


def test_recalibration_stays_near_identity_with_no_evidence():
    rec = fit_recalibration(np.array([0.3, 0.6]), np.array([0.0, 1.0]))
    assert rec.slope == pytest.approx(1, abs=0.3) and abs(rec.intercept) < 0.3
    assert Recalibration(1.0, 0.0).apply(np.array([0.2]))[0] == pytest.approx(0.2)


def test_calibration_check_flags_a_clear_mismatch_only():
    p = np.full(60, 0.1)
    held = calibration_check(p, np.r_[np.ones(6), np.zeros(54)])
    assert held["consistent"] is True
    off = calibration_check(p, np.r_[np.ones(25), np.zeros(35)])
    assert off["consistent"] is False and off["observed"] == pytest.approx(25 / 60)


def test_recall_audit_flags_significant_drop():
    bad = recall_audit(detected=8, objects=60, validation_recall=0.38)
    assert bad["recall"] == pytest.approx(8 / 60) and bad["below_validation"] is True
    ok = recall_audit(detected=21, objects=60, validation_recall=0.38)
    assert ok["below_validation"] is False
    few = recall_audit(detected=0, objects=4, validation_recall=0.38)
    assert few["below_validation"] is None and "too few" in few["note"]
    assert RECALL_AUDIT_IMAGES == 30
