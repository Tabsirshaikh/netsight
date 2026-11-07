"""Probability calibration for detector scores."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, ClassVar, Self

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import isotonic_regression, minimize, minimize_scalar
from scipy.special import expit, logit

FloatArray = NDArray[np.float64]
EPS = 1e-6


def _validate(
    scores: ArrayLike,
    y: ArrayLike | None,
    covariates: ArrayLike | None,
    *,
    fitting: bool,
    allow_covariates: bool,
    min_samples: int,
    n_covariates: int | None = None,
) -> tuple[FloatArray, FloatArray | None, FloatArray, NDArray[np.bool_]]:
    """Validate inputs and identify rows with complete observations."""
    try:
        s = np.asarray(scores, dtype=np.float64)
        target = None if y is None else np.asarray(y, dtype=np.float64)
        z = (
            np.empty((s.size, 0), dtype=np.float64)
            if covariates is None
            else np.asarray(covariates, dtype=np.float64)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Inputs must be numeric arrays.") from exc

    if s.ndim != 1:
        raise ValueError("scores must be one-dimensional.")
    if np.any(np.isinf(s)) or np.any((s < 0) | (s > 1)):
        raise ValueError("Non-NaN scores must be finite and in [0, 1].")
    if not allow_covariates and covariates is not None:
        raise ValueError("This calibrator does not allow covariates.")
    if z.ndim != 2 or z.shape[0] != s.size:
        raise ValueError("covariates must have shape (n_scores, k).")
    if np.any(np.isinf(z)):
        raise ValueError("covariates must not contain infinity.")
    if n_covariates is not None and z.shape[1] != n_covariates:
        raise ValueError("Covariate column count must match fit.")

    usable = ~np.isnan(s) & ~np.isnan(z).any(axis=1)
    if fitting:
        if not isinstance(min_samples, int) or min_samples < 1:
            raise ValueError("min_samples must be a positive integer.")
        if target is None or target.ndim != 1 or target.shape != s.shape:
            raise ValueError("y must be one-dimensional and aligned with scores.")
        if np.any(~(np.isnan(target) | (target == 0) | (target == 1))):
            raise ValueError("Non-NaN y values must be 0 or 1.")
        usable &= ~np.isnan(target)
        if np.count_nonzero(usable) < min_samples:
            raise ValueError(f"Fitting requires at least {min_samples} usable pairs.")
        if np.unique(target[usable]).size != 2:
            raise ValueError("Fitting requires both classes among usable pairs.")
        return s[usable], target[usable], z[usable], usable
    return s, target, z, usable


class Calibrator(ABC):
    """Base class for fitted probability calibrators."""

    kind: ClassVar[str]
    allow_covariates: ClassVar[bool] = True

    def __init__(self, min_samples: int = 30) -> None:
        self.min_samples = min_samples
        self._fitted = False
        self._parameters = np.empty(0, dtype=np.float64)
        self._knots = np.empty(0, dtype=np.float64)
        self._means = np.empty(0, dtype=np.float64)
        self._stds = np.empty(0, dtype=np.float64)
        self.n_fit = 0
        self.n_positive = 0

    def fit(
        self,
        scores: ArrayLike,
        y: ArrayLike,
        covariates: ArrayLike | None = None,
    ) -> Self:
        """Fit using complete score, outcome, and covariate rows."""
        s, target, z, _ = _validate(
            scores,
            y,
            covariates,
            fitting=True,
            allow_covariates=self.allow_covariates,
            min_samples=self.min_samples,
        )
        assert target is not None
        self._fitted = False
        self._means = z.mean(axis=0)
        self._stds = z.std(axis=0)
        self._stds[self._stds == 0] = 1
        self._fit(s, target, (z - self._means) / self._stds)
        self.n_fit = int(s.size)
        self.n_positive = int(target.sum())
        self._fitted = True
        return self

    def predict(self, scores: ArrayLike, covariates: ArrayLike | None = None) -> FloatArray:
        """Return calibrated probabilities, retaining missing rows as NaN."""
        if not self._fitted:
            raise RuntimeError("Calibrator must be fitted before prediction.")
        s, _, z, usable = _validate(
            scores,
            None,
            covariates,
            fitting=False,
            allow_covariates=self.allow_covariates,
            min_samples=self.min_samples,
            n_covariates=self._means.size,
        )
        result = np.full(s.shape, np.nan, dtype=np.float64)
        if usable.any():
            standardized = (z[usable] - self._means) / self._stds
            result[usable] = np.clip(self._predict(s[usable], standardized), 0, 1)
        return result

    def to_dict(self) -> dict[str, Any]:
        """Export a fitted model as JSON-compatible values."""
        if not self._fitted:
            raise RuntimeError("Calibrator must be fitted before serialization.")
        state: dict[str, Any] = {
            "kind": self.kind,
            "version": 1,
            "min_samples": self.min_samples,
            "n_fit": self.n_fit,
            "n_positive": self.n_positive,
            "parameters": self._parameters.tolist(),
            "knots": self._knots.tolist(),
            "covariate_means": self._means.tolist(),
            "covariate_stds": self._stds.tolist(),
        }
        if isinstance(self, _LogisticCalibrator):
            state["l2"] = self.l2
        return state

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Calibrator":
        """Restore a model exported by to_dict."""
        registry = {
            TemperatureScaling.kind: TemperatureScaling,
            PlattCalibrator.kind: PlattCalibrator,
            BetaCalibrator.kind: BetaCalibrator,
            IsotonicCalibrator.kind: IsotonicCalibrator,
        }
        if d.get("version") != 1 or d.get("kind") not in registry:
            raise ValueError("Unsupported calibrator kind or version.")
        model_type = registry[d["kind"]]
        if issubclass(model_type, _LogisticCalibrator):
            model = model_type(min_samples=int(d["min_samples"]), l2=float(d["l2"]))
        else:
            model = model_type(min_samples=int(d["min_samples"]))
        model._parameters = np.array(d["parameters"], dtype=np.float64)
        model._knots = np.array(d["knots"], dtype=np.float64)
        model._means = np.array(d["covariate_means"], dtype=np.float64)
        model._stds = np.array(d["covariate_stds"], dtype=np.float64)
        model.n_fit = int(d["n_fit"])
        model.n_positive = int(d["n_positive"])
        model._fitted = True
        return model

    @abstractmethod
    def _fit(self, scores: FloatArray, y: FloatArray, z: FloatArray) -> None:
        """Estimate model-specific parameters."""

    @abstractmethod
    def _predict(self, scores: FloatArray, z: FloatArray) -> FloatArray:
        """Evaluate model-specific probabilities."""


class TemperatureScaling(Calibrator):
    """Fit a single positive temperature without an intercept."""

    kind = "temperature"
    allow_covariates = False

    @property
    def T(self) -> float:
        """Return the fitted temperature."""
        if not self._fitted:
            raise RuntimeError("Calibrator is not fitted.")
        return float(self._parameters[0])

    def _fit(self, scores: FloatArray, y: FloatArray, z: FloatArray) -> None:
        logits = logit(np.clip(scores, EPS, 1 - EPS))

        def objective(log_temperature: float) -> float:
            eta = logits / np.exp(log_temperature)
            return float(np.mean(np.logaddexp(0, eta) - y * eta))

        result = minimize_scalar(
            objective,
            bounds=(-5, 5),
            method="bounded",
            options={"xatol": 1e-10},
        )
        if not result.success:
            raise RuntimeError(f"Temperature optimization failed: {result.message}")
        self._parameters = np.array([np.exp(result.x)], dtype=np.float64)

    def _predict(self, scores: FloatArray, z: FloatArray) -> FloatArray:
        return expit(logit(np.clip(scores, EPS, 1 - EPS)) / self._parameters[0])


class _LogisticCalibrator(Calibrator):
    """Shared penalized logistic fitting machinery."""

    def __init__(self, min_samples: int = 30, l2: float = 1e-4) -> None:
        super().__init__(min_samples=min_samples)
        if not np.isfinite(l2) or l2 < 0:
            raise ValueError("l2 must be finite and non-negative.")
        self.l2 = float(l2)

    @abstractmethod
    def _design(self, scores: FloatArray, z: FloatArray) -> FloatArray:
        """Construct the design matrix, with intercept last."""

    def _fit(self, scores: FloatArray, y: FloatArray, z: FloatArray) -> None:
        design = self._design(scores, z)
        initial = np.zeros(design.shape[1], dtype=np.float64)
        penalty = np.full(initial.size, self.l2)
        penalty[-1] = 0

        def objective(parameters: FloatArray) -> tuple[float, FloatArray]:
            eta = design @ parameters
            loss = np.mean(np.logaddexp(0, eta) - y * eta)
            loss += np.dot(penalty, parameters**2)
            gradient = design.T @ (expit(eta) - y) / y.size
            gradient += 2 * penalty * parameters
            return float(loss), gradient

        bounds = [(None, None)] * initial.size
        if isinstance(self, BetaCalibrator):
            bounds[:2] = [(0, None), (0, None)]
            initial[:2] = 1
        else:
            initial[0] = 1
        result = minimize(
            objective,
            initial,
            method="L-BFGS-B",
            jac=True,
            bounds=bounds,
            options={"ftol": 1e-13, "gtol": 1e-9, "maxiter": 2000},
        )
        if not result.success or not np.all(np.isfinite(result.x)):
            raise RuntimeError(f"Logistic optimization failed: {result.message}")
        self._parameters = np.asarray(result.x, dtype=np.float64)

    def _predict(self, scores: FloatArray, z: FloatArray) -> FloatArray:
        return expit(self._design(scores, z) @ self._parameters)


class PlattCalibrator(_LogisticCalibrator):
    """Logistic calibration of score logits and optional covariates."""

    kind = "platt"

    @property
    def a(self) -> float:
        """Return the fitted logit coefficient."""
        if not self._fitted:
            raise RuntimeError("Calibrator is not fitted.")
        return float(self._parameters[0])

    @property
    def b(self) -> float:
        """Return the fitted intercept."""
        if not self._fitted:
            raise RuntimeError("Calibrator is not fitted.")
        return float(self._parameters[-1])

    def _design(self, scores: FloatArray, z: FloatArray) -> FloatArray:
        return np.column_stack((logit(np.clip(scores, EPS, 1 - EPS)), z, np.ones(scores.size)))


class BetaCalibrator(_LogisticCalibrator):
    """Monotone abm beta calibration with optional covariates."""

    kind = "beta"

    @property
    def a(self) -> float:
        """Return the fitted log-score coefficient."""
        if not self._fitted:
            raise RuntimeError("Calibrator is not fitted.")
        return float(self._parameters[0])

    @property
    def b(self) -> float:
        """Return the fitted negative-log-complement coefficient."""
        if not self._fitted:
            raise RuntimeError("Calibrator is not fitted.")
        return float(self._parameters[1])

    @property
    def c(self) -> float:
        """Return the fitted intercept."""
        if not self._fitted:
            raise RuntimeError("Calibrator is not fitted.")
        return float(self._parameters[-1])

    def _design(self, scores: FloatArray, z: FloatArray) -> FloatArray:
        clipped = np.clip(scores, EPS, 1 - EPS)
        return np.column_stack((np.log(clipped), -np.log1p(-clipped), z, np.ones(scores.size)))


class IsotonicCalibrator(Calibrator):
    """Weighted isotonic calibration with interpolation between block means."""

    kind = "isotonic"
    allow_covariates = False

    def __init__(self, min_samples: int = 1000) -> None:
        super().__init__(min_samples=min_samples)

    def _fit(self, scores: FloatArray, y: FloatArray, z: FloatArray) -> None:
        unique, inverse, counts = np.unique(scores, return_inverse=True, return_counts=True)
        positives = np.bincount(inverse, weights=y, minlength=unique.size)
        fitted = isotonic_regression(positives / counts, weights=counts, increasing=True)
        starts = fitted.blocks[:-1]
        block_counts = np.add.reduceat(counts, starts)
        self._knots = np.add.reduceat(unique * counts, starts) / block_counts
        self._parameters = np.asarray(fitted.x[starts], dtype=np.float64)

    def _predict(self, scores: FloatArray, z: FloatArray) -> FloatArray:
        return np.interp(scores, self._knots, self._parameters)
