"""Tests for probability calibrators."""

import json

import numpy as np
import pytest
from numpy.typing import NDArray
from scipy.special import expit

from netsight.trust.calibrators import (
    BetaCalibrator,
    Calibrator,
    IsotonicCalibrator,
    PlattCalibrator,
    TemperatureScaling,
)


def log_loss(y: NDArray[np.float64], p: NDArray[np.float64]) -> float:
    """Compute binary log loss."""
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log1p(-p)))


def test_platt_parameter_recovery() -> None:
    rng = np.random.default_rng(0)
    logits = rng.normal(0, 1.5, 20_000)
    y = rng.binomial(1, expit(2 * logits - 0.5))
    model = PlattCalibrator().fit(expit(logits), y)
    assert model.a == pytest.approx(2, abs=0.1)
    assert model.b == pytest.approx(-0.5, abs=0.1)


def test_informative_covariate_improves_held_out_loss() -> None:
    rng = np.random.default_rng(1)
    logits = rng.normal(size=20_000)
    covariates = rng.normal(size=(20_000, 1))
    y = rng.binomial(1, expit(logits + 2 * covariates[:, 0] - 0.3))
    scores = expit(logits)
    split = 12_000
    baseline = PlattCalibrator().fit(scores[:split], y[:split])
    augmented = PlattCalibrator().fit(scores[:split], y[:split], covariates[:split])
    base_loss = log_loss(y[split:], baseline.predict(scores[split:]))
    augmented_loss = log_loss(y[split:], augmented.predict(scores[split:], covariates[split:]))
    assert augmented_loss < base_loss - 0.1


def test_beta_parameter_recovery() -> None:
    rng = np.random.default_rng(2)
    scores = rng.uniform(0.001, 0.999, 100_000)
    p = expit(1.5 * np.log(scores) - 0.7 * np.log1p(-scores) + 0.2)
    y = rng.binomial(1, p)
    model = BetaCalibrator().fit(scores, y)
    assert model.a >= 0
    assert model.b >= 0
    assert model.a == pytest.approx(1.5, abs=0.15)
    assert model.b == pytest.approx(0.7, abs=0.15)
    assert model.c == pytest.approx(0.2, abs=0.15)


def test_temperature_recovery() -> None:
    rng = np.random.default_rng(3)
    true_logits = rng.normal(size=60_000)
    scores = expit(3 * true_logits)
    y = rng.binomial(1, expit(true_logits))
    model = TemperatureScaling().fit(scores, y)
    assert model.T == pytest.approx(3, abs=0.2)


def test_isotonic_ties_block_means_and_monotonicity() -> None:
    model = IsotonicCalibrator(min_samples=4).fit([0.1, 0.1, 0.8, 0.8], [0, 1, 1, 1])
    np.testing.assert_allclose(model.predict([0.1, 0.8]), [0.5, 1])
    predictions = model.predict(np.linspace(0, 1, 101))
    assert np.all(np.diff(predictions) >= 0)
    assert predictions[0] == 0.5
    assert predictions[-1] == 1

    pooled = IsotonicCalibrator(min_samples=4).fit([0.1, 0.2, 0.8, 0.9], [1, 0, 1, 1])
    np.testing.assert_allclose(pooled.predict([0.15, 0.85]), [0.5, 1])


@pytest.mark.parametrize(
    "model_type",
    [TemperatureScaling, PlattCalibrator, BetaCalibrator, IsotonicCalibrator],
)
def test_round_trip(model_type: type[Calibrator]) -> None:
    rng = np.random.default_rng(4)
    scores = rng.uniform(size=1500)
    covariates = rng.normal(size=(1500, 2))
    covariates[:, 1] = 5
    y = rng.binomial(1, scores)
    z = covariates if model_type in (PlattCalibrator, BetaCalibrator) else None
    model = model_type().fit(scores, y, z)
    state = json.loads(json.dumps(model.to_dict(), allow_nan=False))
    restored = Calibrator.from_dict(state)
    assert state["version"] == 1
    assert state["n_fit"] == 1500
    assert state["n_positive"] == int(y.sum())
    np.testing.assert_allclose(
        restored.predict(scores, z), model.predict(scores, z), atol=1e-12, rtol=0
    )


@pytest.mark.parametrize(
    "model_type",
    [TemperatureScaling, PlattCalibrator, BetaCalibrator, IsotonicCalibrator],
)
def test_common_errors(model_type: type[Calibrator]) -> None:
    model = model_type()
    with pytest.raises(RuntimeError, match="fitted"):
        model.predict([0.5])
    with pytest.raises(ValueError, match="usable pairs"):
        model.fit([0.2, 0.8], [0, 1])
    with pytest.raises(ValueError, match="both classes"):
        model.fit(np.full(1200, 0.5), np.ones(1200))
    with pytest.raises(ValueError, match="0 or 1"):
        model.fit(np.full(1200, 0.5), np.full(1200, 2))


@pytest.mark.parametrize("model_type", [TemperatureScaling, IsotonicCalibrator])
def test_covariates_forbidden(model_type: type[Calibrator]) -> None:
    model = model_type(min_samples=4)
    scores = [0.1, 0.3, 0.7, 0.9]
    with pytest.raises(ValueError, match="does not allow"):
        model.fit(scores, [0, 0, 1, 1], np.ones((4, 1)))
    model.fit(scores, [0, 0, 1, 1])
    with pytest.raises(ValueError, match="does not allow"):
        model.predict(scores, np.ones((4, 1)))


def test_covariate_count_and_missing_prediction_rows() -> None:
    model = PlattCalibrator(min_samples=4).fit([0.1, 0.3, 0.7, 0.9], [0, 0, 1, 1], np.ones((4, 1)))
    with pytest.raises(ValueError, match="column count"):
        model.predict([0.5])
    with pytest.raises(ValueError, match="column count"):
        model.predict([0.5], [[1, 2]])
    predicted = model.predict([0.2, 0.5], [[np.nan], [1]])
    assert np.isnan(predicted[0])
    assert np.isfinite(predicted[1])


@pytest.mark.parametrize(
    "model_type",
    [TemperatureScaling, PlattCalibrator, BetaCalibrator, IsotonicCalibrator],
)
def test_nan_pairs_are_dropped(model_type: type[Calibrator]) -> None:
    scores = np.array([0.1, 0.3, 0.7, 0.9, np.nan, 0.4])
    y = np.array([0, 0, 1, 1, 1, np.nan])
    model = model_type(min_samples=4).fit(scores, y)
    reference = model_type(min_samples=4).fit(scores[:4], y[:4])
    assert model.n_fit == 4
    assert model.n_positive == 2
    predictions = model.predict([0.2, np.nan, 0.8])
    assert np.isnan(predictions[1])
    np.testing.assert_allclose(predictions[[0, 2]], reference.predict([0.2, 0.8]), atol=1e-12)


def test_nan_covariates_dropped_and_invalid_inputs_rejected() -> None:
    model = PlattCalibrator(min_samples=4).fit(
        [0.1, 0.3, 0.7, 0.9, 0.5],
        [0, 0, 1, 1, 0],
        [[1], [1], [1], [1], [np.nan]],
    )
    assert model.n_fit == 4
    for scores in ([0.1, 1.1], [0.1, np.inf], [[0.1, 0.9]]):
        with pytest.raises(ValueError):
            PlattCalibrator(min_samples=2).fit(scores, [0, 1])
    with pytest.raises(ValueError, match="0 or 1"):
        PlattCalibrator(min_samples=2).fit([0.1, np.nan], [0, 2])
