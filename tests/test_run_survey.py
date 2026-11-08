"""Tests for the dump-only survey trust pipeline."""

import json
from pathlib import Path

import numpy as np
import pytest

from netsight.demo.run_survey import (
    fit_calibrator,
    geometry_claim,
    survey_detections,
    validation_recall,
)
from netsight.trust.bounds import clopper_pearson


def _write_set(path: Path) -> None:
    """Write four images with two groups and forty boxes per group."""
    boxes = []
    scores = []
    pred_image = []
    ground_truth = []
    gt_image = []
    for image_index in range(4):
        image_boxes = []
        for detection_index in range(20):
            x = float(detection_index * 20)
            box = [x, 10.0, x + 10.0, 20.0]
            image_boxes.append(box)
            boxes.append(box)
            scores.append(0.99 - 0.03 * detection_index - 0.001 * image_index)
            pred_image.append(image_index)
        # The two highest scores are in images 0 and 1; only image 0 is a TP.
        ground_truth.append(image_boxes[image_index % 2])
        gt_image.append(image_index)
    np.savez(
        path,
        boxes=np.asarray(boxes, dtype=np.float32),
        scores=np.asarray(scores, dtype=np.float32),
        pred_image=np.asarray(pred_image, dtype=np.int64),
        gt=np.asarray(ground_truth, dtype=np.float32),
        gt_image=np.asarray(gt_image, dtype=np.int64),
        n_images=np.asarray(4, dtype=np.int64),
        groups=np.asarray(["survey-a", "survey-a", "survey-b", "survey-b"]),
    )


@pytest.fixture
def pred_dir(tmp_path: Path) -> Path:
    """Create an aligned validation/test prediction dump."""
    (tmp_path / "info.json").write_text(
        json.dumps({"sets": {"val_x": 4, "test_x": 4}}), encoding="utf-8"
    )
    _write_set(tmp_path / "val_x.npz")
    _write_set(tmp_path / "test_x.npz")
    return tmp_path


def test_fit_calibrator(pred_dir: Path) -> None:
    """Fit all eligible validation detections and return bounded probabilities."""
    calibrator, metadata = fit_calibrator(pred_dir)
    assert metadata == {
        "method": "beta",
        "fitted_on": "pooled validation detections",
        "n_fit": 80,
        "positives_fit": 4,
    }
    probabilities = calibrator.predict(np.asarray([0.1, 0.5, 0.95]))
    assert probabilities.shape == (3,)
    assert np.isfinite(probabilities).all()
    assert ((probabilities >= 0) & (probabilities <= 1)).all()


def test_survey_detections_group_filter(pred_dir: Path) -> None:
    """Filtering preserves original image indices and aligned predictions."""
    survey = survey_detections(pred_dir, "x", "survey-b")
    assert survey.n_images == 2
    assert survey.total_images == 4
    assert survey.image_indices == [2, 3]
    assert survey.groups == ["survey-b", "survey-b"]
    assert all(boxes.shape == (20, 4) for boxes, _ in survey.predictions)
    assert survey.predictions[0][1][0] == pytest.approx(0.988)

    complete = survey_detections(pred_dir, "x")
    assert complete.n_images == 4
    assert complete.image_indices == [0, 1, 2, 3]


def test_unknown_group_rejected(pred_dir: Path) -> None:
    """An empty selection is not a usable survey."""
    with pytest.raises(ValueError, match="No images selected"):
        survey_detections(pred_dir, "x", "missing")


def test_validation_recall(pred_dir: Path) -> None:
    """A two-detection budget flags one of four validation objects."""
    recall, interval = validation_recall(pred_dir, budget=0.5)
    assert recall == pytest.approx(1 / 4)
    assert interval == pytest.approx(clopper_pearson(1, 4))


def test_geometry_claim(pred_dir: Path) -> None:
    """Training-like geometry calibrates; a wider distribution is indicative."""
    survey = survey_detections(pred_dir, "x")
    boxes = np.concatenate([boxes for boxes, _ in survey.predictions])
    scores = np.concatenate([scores for _, scores in survey.predictions])

    claim = geometry_claim(pred_dir, boxes, scores)
    assert claim.level == "calibrated"
    assert claim.reasons == []
    assert claim.statement == (
        "Probabilities are calibrated on validation surveys with similar pixel geometry."
    )

    wider = boxes.copy()
    wider[:, 2] = wider[:, 0] + 1.4 * (boxes[:, 2] - boxes[:, 0])
    claim = geometry_claim(pred_dir, wider, scores)
    assert claim.level == "indicative"
    assert claim.reasons
    assert claim.statement == (
        "Probabilities are indicative: this survey's pixel geometry differs "
        "from the validation surveys."
    )
