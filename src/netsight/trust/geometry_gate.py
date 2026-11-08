"""Label-free checks for survey pixel geometry using confident detections."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import exp, isfinite, sqrt

import numpy as np
from numpy.typing import ArrayLike

type Range = tuple[float, float]


@dataclass(frozen=True)
class AspectProfile:
    """Summarize confident detection geometry in one survey."""

    n_boxes: int
    median_log_aspect: float
    iqr_log_aspect: float
    median_side_px: float
    ci_log_aspect: Range

    @classmethod
    def from_boxes(
        cls,
        boxes: ArrayLike,
        scores: ArrayLike | None = None,
        *,
        min_score: float = 0.3,
        seed: int = 0,
    ) -> AspectProfile:
        """Profile usable boxes with a seeded, percentile bootstrap CI."""
        coordinates = np.asarray(boxes, dtype=np.float64)
        if coordinates.shape == (0,):
            coordinates = coordinates.reshape(0, 4)
        if coordinates.ndim != 2 or coordinates.shape[1] != 4:
            raise ValueError("boxes must have shape (n, 4)")

        with np.errstate(invalid="ignore", over="ignore"):
            widths = coordinates[:, 2] - coordinates[:, 0]
            heights = coordinates[:, 3] - coordinates[:, 1]
        usable = (
            np.isfinite(coordinates).all(axis=1)
            & np.isfinite(widths)
            & np.isfinite(heights)
            & (widths >= 2.0)
            & (heights >= 2.0)
        )
        if scores is not None:
            confidence = np.asarray(scores, dtype=np.float64)
            if confidence.shape != (len(coordinates),):
                raise ValueError("scores must have shape (n,)")
            usable &= np.isfinite(confidence) & (confidence >= min_score)

        widths = widths[usable]
        heights = heights[usable]
        n_boxes = len(widths)
        if n_boxes == 0:
            nan = float("nan")
            return cls(0, nan, nan, nan, (nan, nan))

        log_widths = np.log(widths)
        log_heights = np.log(heights)
        log_aspects = log_widths - log_heights
        sides = np.exp((log_widths + log_heights) / 2.0)
        quartiles = np.quantile(log_aspects, [0.25, 0.75])

        rng = np.random.default_rng(seed)
        bootstrap_medians = np.empty(1000, dtype=np.float64)
        for index in range(1000):
            sample = rng.integers(0, n_boxes, size=n_boxes)
            bootstrap_medians[index] = np.median(log_aspects[sample])
        ci = np.quantile(bootstrap_medians, [0.025, 0.975])

        return cls(
            n_boxes=n_boxes,
            median_log_aspect=float(np.median(log_aspects)),
            iqr_log_aspect=float(quartiles[1] - quartiles[0]),
            median_side_px=float(np.median(sides)),
            ci_log_aspect=(float(ci[0]), float(ci[1])),
        )

    @property
    def aspect(self) -> float:
        """Return the median aspect ratio in linear units."""
        return exp(self.median_log_aspect)


@dataclass(frozen=True)
class GeometryEnvelope:
    """Describe training-survey aspect and object-size ranges."""

    log_aspect_range: Range
    side_px_range: Range
    n_surveys: int

    @classmethod
    def from_profiles(
        cls,
        profiles: Sequence[AspectProfile],
        *,
        margin_log: float = 0.08,
        side_margin: float = 0.5,
        min_boxes: int = 30,
    ) -> GeometryEnvelope:
        """Build an envelope from surveys with enough usable boxes."""
        qualifying = [profile for profile in profiles if profile.n_boxes >= min_boxes]
        if not qualifying:
            raise ValueError("no profiles have enough usable boxes")

        aspects = [profile.median_log_aspect for profile in qualifying]
        sides = [profile.median_side_px for profile in qualifying]
        return cls(
            log_aspect_range=(min(aspects) - margin_log, max(aspects) + margin_log),
            side_px_range=(
                min(sides) * (1.0 - side_margin),
                max(sides) * (1.0 + side_margin),
            ),
            n_surveys=len(qualifying),
        )


def geometry_reasons(
    profile: AspectProfile,
    envelope: GeometryEnvelope,
    *,
    min_boxes: int = 30,
) -> list[str]:
    """Return soft applicability warnings, not detection-quality claims."""
    if profile.n_boxes < min_boxes:
        return [
            f"pixel geometry not estimable: only {profile.n_boxes:.2f} "
            f"confident detections (need {min_boxes:.2f})"
        ]

    reasons: list[str] = []
    aspect_low, aspect_high = envelope.log_aspect_range
    ci_low, ci_high = profile.ci_log_aspect
    if ci_high < aspect_low or ci_low > aspect_high:
        aspect = profile.aspect
        if aspect < 1.0:
            appearance = f"{1.0 / aspect:.2f}x taller than wide"
        else:
            appearance = f"{aspect:.2f}x wider than tall"
        row_scale = exp(profile.median_log_aspect - (aspect_low + aspect_high) / 2.0)
        reasons.append(
            f"objects appear {appearance} "
            f"(training surveys {exp(aspect_low):.2f}-{exp(aspect_high):.2f}x): "
            f"pixel aspect differs; resample rows by {row_scale:.2f} before detection"
        )

    side_low, side_high = envelope.side_px_range
    side = profile.median_side_px
    if side < side_low or side > side_high:
        scale = sqrt(side_low * side_high) / side
        reasons.append(
            f"objects appear {side:.2f} px across "
            f"(training surveys {side_low:.2f}-{side_high:.2f} px): "
            f"pixel size differs; rescale by {scale:.2f}"
        )
    return reasons


def suggest_resampling(
    profile: AspectProfile,
    envelope: GeometryEnvelope,
) -> tuple[float, float]:
    """Suggest independent aspect and size corrections for estimable profiles."""
    if (
        profile.n_boxes < 30
        or not isfinite(profile.median_log_aspect)
        or not isfinite(profile.median_side_px)
        or profile.median_side_px <= 0.0
    ):
        return 1.0, 1.0

    aspect_low, aspect_high = envelope.log_aspect_range
    row_scale = 1.0
    if not aspect_low <= profile.median_log_aspect <= aspect_high:
        row_scale = exp(profile.median_log_aspect - (aspect_low + aspect_high) / 2.0)

    side_low, side_high = envelope.side_px_range
    scale = 1.0
    if not side_low <= profile.median_side_px <= side_high:
        scale = sqrt(side_low * side_high) / profile.median_side_px
    return row_scale, scale
