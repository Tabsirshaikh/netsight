import numpy as np
import pytest

from netsight.trust.fusion import feature_matrix, fit_fusion, log_loss


def test_feature_matrix_missing_is_zero():
    m = feature_matrix([{"a": 1.0, "b": None}, {"a": float("nan"), "b": True}], ["a", "b"])
    np.testing.assert_array_equal(m, [[1.0, 0.0], [0.0, 1.0]])


def test_informative_feature_lowers_held_out_loss():
    rng = np.random.default_rng(0)
    n = 4000
    y = rng.random(n) < 0.3
    score = np.clip(0.5 + 0.15 * (y - 0.5) + rng.normal(0, 0.2, n), 0.01, 0.99)
    useful = y + rng.normal(0, 0.5, n)
    noise = rng.normal(0, 1, n)
    tr, te = slice(0, 3000), slice(3000, None)
    feats = np.column_stack([useful, noise])
    m_both = fit_fusion(score[tr], feats[tr], y[tr], ["useful", "noise"])
    m_score = fit_fusion(score[tr], feats[tr, :0], y[tr], [])
    l_both = log_loss(m_both.predict(score[te], feats[te]), y[te])
    l_score = log_loss(m_score.predict(score[te], feats[te, :0]), y[te])
    assert l_both < l_score - 0.05
    assert abs(m_both.coef[3]) < abs(m_both.coef[2]) / 5  # noise weight small


def test_fusion_needs_both_classes():
    with pytest.raises(ValueError):
        fit_fusion(np.array([0.5, 0.6]), np.zeros((2, 0)), np.array([1, 1]), [])
