import numpy as np
import pytest

from netsight.trust.applicability import (
    CanaryResult,
    Envelope,
    SurveyConditions,
    canary_check,
    decide_claim_level,
    hard_gate,
    score_drift,
)


def _cond(**kw) -> SurveyConditions:
    base = dict(
        sensor_type="side_scan",
        model="EdgeTech 4125",
        frequency_khz=400.0,
        range_m=50.0,
        resolution_m=0.05,
        processing_chain="netsight-normalise-0.1",
    )
    base.update(kw)
    return SurveyConditions(**base)


@pytest.fixture
def envelope() -> Envelope:
    surveys = [_cond(), _cond(frequency_khz=450.0, range_m=75.0, resolution_m=0.08)]
    return Envelope.from_surveys(surveys, calibrator_id="cal-001", calibrator_validated=True)


def test_envelope_from_surveys(envelope):
    assert envelope.models == frozenset({"EdgeTech 4125"})
    assert envelope.frequency_khz == (400.0, 450.0)
    assert envelope.range_m == (50.0, 75.0)
    assert envelope.resolution_m == (0.05, 0.08)


def test_envelope_needs_surveys():
    with pytest.raises(ValueError):
        Envelope.from_surveys([], calibrator_id="c", calibrator_validated=True)


def test_inside_envelope_passes_hard_gate(envelope):
    # within the 10% tolerance of the seen ranges
    assert hard_gate(envelope, _cond(frequency_khz=470.0, range_m=60.0)) == []


@pytest.mark.parametrize(
    ("change", "word"),
    [
        ({"model": "Klein 4900"}, "model"),
        ({"sensor_type": "multibeam_backscatter"}, "sensor type"),
        ({"frequency_khz": 900.0}, "frequency"),
        ({"frequency_khz": None}, "frequency"),
        ({"range_m": 200.0}, "range"),
        ({"resolution_m": 0.5}, "resolution"),
        ({"processing_chain": "vendor-x"}, "processing"),
    ],
)
def test_hard_gate_failures_name_the_reason(envelope, change, word):
    reasons = hard_gate(envelope, _cond(**change))
    assert reasons and any(word in r for r in reasons)


def test_score_drift_flags_shifted_distribution():
    rng = np.random.default_rng(0)
    ref = rng.beta(2, 5, 500)
    same = rng.beta(2, 5, 500)
    shifted = rng.beta(5, 2, 500)
    assert score_drift(ref, same).drift is False
    result = score_drift(ref, shifted)
    assert result.drift is True and result.p_value < 0.01


def test_score_drift_needs_enough_scores():
    with pytest.raises(ValueError):
        score_drift(np.linspace(0, 1, 5), np.linspace(0, 1, 500))


def test_canary_failure_when_far_below_predicted_pd():
    detected = [True] * 10 + [False] * 10
    result = canary_check(detected, predicted_pd=[0.9] * 20)
    assert result.passed is False and result.expected == pytest.approx(18.0)
    assert result.p_value < 0.01


def test_canary_passes_when_consistent():
    detected = [True] * 18 + [False] * 2
    assert canary_check(detected, predicted_pd=[0.9] * 20).passed is True


def test_canary_input_errors():
    with pytest.raises(ValueError):
        canary_check([True, False], predicted_pd=[0.9])
    with pytest.raises(ValueError):
        canary_check([], predicted_pd=[])
    with pytest.raises(ValueError):
        canary_check([True], predicted_pd=[1.5])


def _ok_canary() -> CanaryResult:
    return canary_check([True] * 18 + [False] * 2, predicted_pd=[0.9] * 20)


def test_claim_calibrated_when_everything_checks_out(envelope):
    d = decide_claim_level(envelope, _cond(), drift=None, canary=_ok_canary())
    assert d.level == "calibrated" and d.reasons == []


def test_claim_withdrawn_outside_envelope(envelope):
    d = decide_claim_level(envelope, _cond(model="Klein 4900"), drift=None, canary=_ok_canary())
    assert d.level == "withdrawn" and "model" in d.reasons[0]


def test_claim_withdrawn_when_canary_fails(envelope):
    bad = canary_check([True] * 10 + [False] * 10, predicted_pd=[0.9] * 20)
    d = decide_claim_level(envelope, _cond(), drift=None, canary=bad)
    assert d.level == "withdrawn" and any("canary" in r for r in d.reasons)


def test_claim_indicative_without_canary(envelope):
    d = decide_claim_level(envelope, _cond(), drift=None, canary=None)
    assert d.level == "indicative" and any("canary" in r for r in d.reasons)


def test_claim_indicative_on_drift(envelope):
    rng = np.random.default_rng(1)
    drift = score_drift(rng.beta(2, 5, 500), rng.beta(5, 2, 500))
    d = decide_claim_level(envelope, _cond(), drift=drift, canary=_ok_canary())
    assert d.level == "indicative" and any("drift" in r for r in d.reasons)


def test_claim_indicative_when_calibrator_not_validated():
    env = Envelope.from_surveys([_cond()], calibrator_id="c", calibrator_validated=False)
    d = decide_claim_level(env, _cond(), drift=None, canary=_ok_canary())
    assert d.level == "indicative" and any("not yet validated" in r for r in d.reasons)


def test_claim_statement_wording(envelope):
    d = decide_claim_level(envelope, _cond(model="Klein 4900"), drift=None, canary=None)
    assert "candidate list only" in d.statement


def test_claim_statements_pass_the_wording_guard():
    from netsight.trust.applicability import STATEMENTS
    from netsight.trust.wording import check_wording

    for text in STATEMENTS.values():
        assert check_wording(text) == []
