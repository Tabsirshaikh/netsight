"""Exercise survey geometry correction with connected-component detections."""

import numpy as np
import pytest
from scipy.ndimage import find_objects, label, zoom

from netsight.detect.adaptive_resample import (
    boxes_to_original,
    factors_from_spacing,
    resample_image,
    spacing_from_metadata,
    two_pass_predict,
)
from netsight.trust.geometry_gate import AspectProfile, GeometryEnvelope


class BlobPredictor:
    """Detect bright connected components without a learned model."""

    def __init__(self) -> None:
        self.calls = 0
        self.outputs: list[tuple[np.ndarray, np.ndarray]] = []

    def __call__(self, image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        self.calls += 1
        components, _ = label(image > 127)
        boxes = []
        for region in find_objects(components):
            if region is None:
                continue
            rows, columns = region
            boxes.append((columns.start, rows.start, columns.stop, rows.stop))
        result = (
            np.asarray(boxes, dtype=np.float64).reshape(-1, 4),
            np.full(len(boxes), 0.9),
        )
        self.outputs.append(result)
        return result


def training_image() -> np.ndarray:
    """Make 36 separated square blobs."""
    image = np.zeros((160, 160), dtype=np.uint8)
    for y in range(12, 156, 24):
        for x in range(12, 156, 24):
            image[y : y + 8, x : x + 8] = 255
    return image


@pytest.fixture
def training_survey() -> list[np.ndarray]:
    """Return a survey with enough detections for geometry estimation."""
    return [training_image(), training_image()]


@pytest.fixture
def envelope(training_survey: list[np.ndarray]) -> GeometryEnvelope:
    """Build the envelope through the public geometry API."""
    predictor = BlobPredictor()
    profiles = []
    for image in training_survey:
        boxes, scores = predictor(image)
        profiles.append(AspectProfile.from_boxes(boxes, scores, seed=0))
    return GeometryEnvelope.from_profiles(profiles)


def matched_iou(actual: np.ndarray, expected: np.ndarray) -> np.ndarray:
    """Return best expected-box IoU for every actual box."""
    low = np.maximum(actual[:, None, :2], expected[None, :, :2])
    high = np.minimum(actual[:, None, 2:], expected[None, :, 2:])
    intersection = np.prod(np.maximum(high - low, 0), axis=2)
    actual_area = np.prod(actual[:, 2:] - actual[:, :2], axis=1)
    expected_area = np.prod(expected[:, 2:] - expected[:, :2], axis=1)
    union = actual_area[:, None] + expected_area[None, :] - intersection
    return (intersection / union).max(axis=1)


def test_spacing_from_metadata() -> None:
    assert spacing_from_metadata(
        range_m=50.0,
        samples_per_side=500,
        ping_rate_hz=10.0,
        speed_mps=2.0,
    ) == pytest.approx((0.2, 0.1))


@pytest.mark.parametrize("bad", [0.0, -1.0, np.inf, -np.inf, np.nan])
@pytest.mark.parametrize("name", ["range_m", "samples_per_side", "ping_rate_hz", "speed_mps"])
def test_invalid_metadata(name: str, bad: float) -> None:
    values = {
        "range_m": 50.0,
        "samples_per_side": 500,
        "ping_rate_hz": 10.0,
        "speed_mps": 2.0,
    }
    values[name] = bad
    with pytest.raises(ValueError, match="positive and finite"):
        spacing_from_metadata(**values)


def test_factors_from_spacing() -> None:
    assert factors_from_spacing(0.2, 0.1, target_m=0.1) == (2.0, 1.0)
    assert factors_from_spacing(100.0, 1.0, target_m=100.0) == (4.0, 0.25)
    assert factors_from_spacing(0.01, 1.0, target_m=0.01) == (0.25, 4.0)


@pytest.mark.parametrize("bad", [0.0, -1.0, np.inf, np.nan])
@pytest.mark.parametrize("index", [0, 1, 2])
def test_invalid_spacing(bad: float, index: int) -> None:
    values = [0.2, 0.1, 0.1]
    values[index] = bad
    with pytest.raises(ValueError, match="positive and finite"):
        factors_from_spacing(values[0], values[1], target_m=values[2])


def test_resample_image() -> None:
    image = np.arange(80, dtype=np.uint8).reshape(8, 10)
    assert resample_image(image, 1.0, 1.0) is image
    result = resample_image(image, 1.5, 2.0)
    assert result.shape == (24, 20)
    assert result.dtype == image.dtype
    assert result.min() >= image.min()
    assert result.max() <= image.max()


def test_boxes_round_trip() -> None:
    original = np.array([[2, 3, 10, 11], [20, 30, 28, 38]])
    row_scale, scale = 1.4, 1.5
    resampled = original * np.array([scale, row_scale * scale] * 2)
    np.testing.assert_allclose(boxes_to_original(resampled, row_scale, scale), original)
    assert boxes_to_original(np.empty((0, 4)), row_scale, scale).shape == (0, 4)


def test_training_survey_needs_no_correction(
    training_survey: list[np.ndarray],
    envelope: GeometryEnvelope,
) -> None:
    predictor = BlobPredictor()
    predictions, correction = two_pass_predict(predictor, training_survey, envelope)
    assert correction.source == "none"
    assert (correction.row_scale, correction.scale) == (1.0, 1.0)
    assert correction.reasons_before == []
    assert correction.reasons_after is None
    assert correction.n_boxes_first_pass == 72
    assert predictor.calls == len(training_survey)
    for prediction, first_pass in zip(predictions, predictor.outputs, strict=True):
        assert prediction is first_pass


def test_stretched_survey_is_corrected(
    training_survey: list[np.ndarray],
    envelope: GeometryEnvelope,
) -> None:
    survey = [zoom(image, (1.0, 1.4), order=0) for image in training_survey]
    predictor = BlobPredictor()
    predictions, correction = two_pass_predict(predictor, survey, envelope)
    assert correction.source == "estimated"
    assert abs(correction.row_scale - 1.4) < 0.1
    assert correction.reasons_before
    assert correction.reasons_after == []
    assert predictor.calls == 2 * len(survey)
    reference = BlobPredictor()
    for image, (boxes, scores) in zip(survey, predictions, strict=True):
        expected, _ = reference(image)
        assert len(boxes) == len(expected)
        assert np.all(matched_iou(boxes, expected) > 0.7)
        np.testing.assert_allclose(scores, 0.9)
    for (_, scores), (_, measured_scores) in zip(
        predictions, predictor.outputs[len(survey) :], strict=True
    ):
        assert scores is measured_scores


def test_metadata_path(
    training_survey: list[np.ndarray],
    envelope: GeometryEnvelope,
) -> None:
    predictor = BlobPredictor()
    predictions, correction = two_pass_predict(
        predictor,
        training_survey,
        envelope,
        spacing=(0.2, 0.1),
        target_m=0.1,
    )
    assert correction.source == "metadata"
    assert (correction.row_scale, correction.scale) == (2.0, 1.0)
    assert correction.n_boxes_first_pass == 0
    assert predictor.calls == len(training_survey)
    for (boxes, scores), (measured, measured_scores) in zip(
        predictions, predictor.outputs, strict=True
    ):
        np.testing.assert_allclose(boxes, boxes_to_original(measured, 2.0, 1.0))
        assert scores is measured_scores


def test_insufficient_detections(envelope: GeometryEnvelope) -> None:
    image = np.zeros((64, 64), dtype=np.uint8)
    image[12:20, 12:23] = 255
    predictor = BlobPredictor()
    predictions, correction = two_pass_predict(predictor, [image], envelope, min_boxes=30)
    assert correction.source == "none"
    assert correction.n_boxes_first_pass == 1
    assert predictor.calls == 1
    assert predictions[0] is predictor.outputs[0]


def test_empty_survey(envelope: GeometryEnvelope) -> None:
    predictor = BlobPredictor()
    predictions, correction = two_pass_predict(predictor, [], envelope)
    assert predictions == []
    assert correction.source == "none"
    assert correction.n_boxes_first_pass == 0
    assert predictor.calls == 0
