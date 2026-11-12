import math

import pytest

from netsight.trust.withdrawal_eval import BlockResult, auroc, envelope_distance, summarise


def test_auroc_hand_cases():
    assert auroc([0.9, 0.8, 0.1, 0.2], [True, True, False, False]) == 1.0
    assert auroc([0.1, 0.2, 0.9, 0.8], [True, True, False, False]) == 0.0
    assert auroc([0.5, 0.5], [True, False]) == 0.5
    assert math.isnan(auroc([0.1], [True]))


def test_envelope_distance():
    rng = ((-0.1, 0.1), (10.0, 40.0))
    assert envelope_distance(0.0, 20.0, *rng) == 0.0
    assert envelope_distance(0.3, 20.0, *rng) == pytest.approx(0.2)
    assert envelope_distance(0.0, 80.0, *rng) == pytest.approx(math.log(2))
    assert math.isnan(envelope_distance(float("nan"), 20.0, *rng))


def _b(level, dist, failed):
    return BlockResult("d", "s", 0, 50, 40, level, dist, 0.0, 0.5, 0.4, failed, "")


def test_summary_rates():
    s = summarise(
        [
            _b("indicative", 0.5, True),
            _b("calibrated", 0.0, False),
            _b("calibrated", 0.0, True),
            _b("calibrated", float("nan"), False),
        ]
    )
    assert s["flagged"]["n"] == 1 and s["flagged"]["rate"] == 1.0
    assert s["passed"]["n"] == 3 and s["passed"]["failed"] == 1
    assert s["blocks_with_gate_score"] == 3
    assert s["auroc_distance"] == pytest.approx(0.75)
