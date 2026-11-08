"""Synthetic checks for label-free geometry profiling and warnings."""

from math import exp, log, sqrt

import numpy as np
import pytest
from numpy.typing import NDArray

from netsight.trust.geometry_gate import (
    AspectProfile,
    GeometryEnvelope,
    geometry_reasons,
    suggest_resampling,
)

type Boxes = NDArray[np.float64]

BANNED_WORDS = ("guarantee", "certain", "always", "100%")


def synthetic_boxes(
    *,
    aspect: float = 1.0,
    side: float = 30.0,
    n: int = 200,
    seed: int = 0,
) -> Boxes:
    """Generate varied boxes with controlled median aspect and side."""
    rng = np.random.default_rng(seed)
    log_aspects = rng.normal(0.0, 0.04, n)
    log_aspects += log(aspect) - np.median(log_aspects)
    sides = rng.lognormal(0.0, 0.08, n)
    sides *= side / np.median(sides)
    widths = sides * np.exp(log_aspects / 2.0)
    heights = sides * np.exp(-log_aspects / 2.0)
    origins = rng.uniform(0.0, 500.0, size=(n, 2))
    return np.column_stack(
        (origins[:, 0], origins[:, 1], origins[:, 0] + widths, origins[:, 1] + heights)
    )


def checked_reasons(
    profile: AspectProfile,
    envelope: GeometryEnvelope,
    *,
    min_boxes: int = 30,
) -> list[str]:
    """Check forbidden wording for every tested warning."""
    reasons = geometry_reasons(profile, envelope, min_boxes=min_boxes)
    for reason in reasons:
        assert not any(word in reason.lower() for word in BANNED_WORDS)
    return reasons


@pytest.fixture
def envelope() -> GeometryEnvelope:
    """Build a reference envelope from three training-like surveys."""
    profiles = [AspectProfile.from_boxes(synthetic_boxes(seed=seed)) for seed in range(3)]
    result = GeometryEnvelope.from_profiles(profiles)
    assert result.n_surveys == 3
    assert result.log_aspect_range == pytest.approx((-0.08, 0.08))
    assert result.side_px_range == pytest.approx((15.0, 45.0))
    return result


def test_wider_objects(envelope: GeometryEnvelope) -> None:
    profile = AspectProfile.from_boxes(synthetic_boxes(aspect=1.32, seed=10))
    reasons = checked_reasons(profile, envelope)
    assert len(reasons) == 1
    assert "1.32x wider than tall" in reasons[0]
    assert "pixel aspect differs" in reasons[0]
    row_scale, scale = suggest_resampling(profile, envelope)
    assert abs(row_scale - 1.32) < 0.05
    assert scale == 1.0


def test_taller_objects(envelope: GeometryEnvelope) -> None:
    profile = AspectProfile.from_boxes(synthetic_boxes(aspect=0.75, seed=11))
    reasons = checked_reasons(profile, envelope)
    assert len(reasons) == 1
    assert "1.33x taller than wide" in reasons[0]
    assert suggest_resampling(profile, envelope) == pytest.approx((0.75, 1.0))


def test_small_objects(envelope: GeometryEnvelope) -> None:
    profile = AspectProfile.from_boxes(synthetic_boxes(side=12.0, seed=12))
    reasons = checked_reasons(profile, envelope)
    assert len(reasons) == 1
    assert "12.00 px across" in reasons[0]
    assert "pixel size differs" in reasons[0]
    assert suggest_resampling(profile, envelope) == pytest.approx((1.0, sqrt(15.0 * 45.0) / 12.0))


def test_training_like_objects(envelope: GeometryEnvelope) -> None:
    profile = AspectProfile.from_boxes(synthetic_boxes(seed=13))
    assert checked_reasons(profile, envelope) == []
    assert suggest_resampling(profile, envelope) == (1.0, 1.0)


def test_too_few_boxes(envelope: GeometryEnvelope) -> None:
    profile = AspectProfile.from_boxes(synthetic_boxes(n=10, aspect=1.32))
    reasons = checked_reasons(profile, envelope)
    assert len(reasons) == 1
    assert "not estimable" in reasons[0]
    assert "10.00 confident detections (need 30.00)" in reasons[0]
    assert suggest_resampling(profile, envelope) == (1.0, 1.0)


def test_score_filtering() -> None:
    boxes = np.array([[0, 0, 40, 20], [0, 0, 20, 40], [0, 0, 30, 30]])
    profile = AspectProfile.from_boxes(boxes, [0.3, 0.29, 0.9])
    assert profile.n_boxes == 2
    assert profile.median_log_aspect == pytest.approx(log(2.0) / 2.0)
    assert AspectProfile.from_boxes(boxes).n_boxes == 3
    assert AspectProfile.from_boxes(boxes, [0.3, 0.29, 0.9], min_score=0.8).n_boxes == 1


def test_degenerate_boxes_ignored() -> None:
    boxes = [
        [0, 0, 1.99, 20],
        [0, 0, 20, 1.99],
        [0, 0, 0, 20],
        [10, 0, 0, 20],
        [0, 0, 2, 2],
    ]
    profile = AspectProfile.from_boxes(boxes)
    assert profile.n_boxes == 1
    assert profile.aspect == pytest.approx(1.0)
    assert profile.median_side_px == pytest.approx(2.0)
    assert profile.iqr_log_aspect == 0.0
    assert profile.ci_log_aspect == (0.0, 0.0)


@pytest.mark.parametrize("boxes", [[], np.empty((0, 4)), [[0, 0, 0, 0]]])
def test_empty_profile(boxes: object, envelope: GeometryEnvelope) -> None:
    profile = AspectProfile.from_boxes(np.asarray(boxes, dtype=np.float64))
    assert profile.n_boxes == 0
    assert np.isnan(profile.median_log_aspect)
    assert np.isnan(profile.iqr_log_aspect)
    assert np.isnan(profile.median_side_px)
    assert np.isnan(profile.ci_log_aspect).all()
    assert np.isnan(profile.aspect)
    assert "not estimable" in checked_reasons(profile, envelope)[0]
    assert suggest_resampling(profile, envelope) == (1.0, 1.0)


def test_no_qualifying_profiles() -> None:
    with pytest.raises(ValueError):
        GeometryEnvelope.from_profiles([])
    small = AspectProfile.from_boxes(synthetic_boxes(n=10))
    with pytest.raises(ValueError):
        GeometryEnvelope.from_profiles([small])


def test_bootstrap_is_seeded() -> None:
    boxes = synthetic_boxes(seed=40)
    first = AspectProfile.from_boxes(boxes, seed=71)
    assert first == AspectProfile.from_boxes(boxes, seed=71)
    assert first.ci_log_aspect[0] <= first.median_log_aspect <= first.ci_log_aspect[1]
    assert first.iqr_log_aspect > 0.0


def test_ci_must_be_wholly_outside(envelope: GeometryEnvelope) -> None:
    profile = AspectProfile(200, log(1.32), 0.1, 30.0, (0.0, log(1.5)))
    assert checked_reasons(profile, envelope) == []


def test_both_geometry_reasons(envelope: GeometryEnvelope) -> None:
    profile = AspectProfile.from_boxes(synthetic_boxes(aspect=1.32, side=12.0))
    reasons = checked_reasons(profile, envelope)
    assert len(reasons) == 2
    assert "pixel aspect differs" in reasons[0]
    assert "pixel size differs" in reasons[1]


def test_custom_envelope_and_minimum() -> None:
    profile = AspectProfile.from_boxes(synthetic_boxes(n=10))
    envelope = GeometryEnvelope.from_profiles(
        [profile], margin_log=0.1, side_margin=0.2, min_boxes=10
    )
    assert envelope.log_aspect_range == pytest.approx((-0.1, 0.1))
    assert envelope.side_px_range == pytest.approx((24.0, 36.0))
    assert checked_reasons(profile, envelope, min_boxes=10) == []


def test_aspect_property() -> None:
    profile = AspectProfile.from_boxes(synthetic_boxes(aspect=1.32))
    assert profile.aspect == pytest.approx(exp(profile.median_log_aspect))
    assert profile.aspect == pytest.approx(1.32)
