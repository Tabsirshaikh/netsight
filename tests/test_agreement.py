"""Tests for inter-annotator agreement metrics."""

import math
from pathlib import Path

import numpy as np
import pytest

from netsight.datasets.agreement import (
    AgreementReport,
    agreement,
    compare_dirs,
    load_yolo_dir,
    match_boxes,
)


def test_cohens_kappa_hand_computed_2x2():
    """Cohen's kappa for 10 images with contingency table [[4, 1], [1, 4]].

    Hand computation:
    A=No, B=No: 4 images
    A=No, B=Yes: 1 image
    A=Yes, B=No: 1 image
    A=Yes, B=Yes: 4 images
    Total N = 10
    Observed agreement p_o = (4 + 4) / 10 = 0.8
    P(A=Yes) = 5/10 = 0.5, P(A=No) = 0.5
    P(B=Yes) = 5/10 = 0.5, P(B=No) = 0.5
    Expected agreement p_e = 0.5*0.5 + 0.5*0.5 = 0.5
    Kappa = (0.8 - 0.5) / (1.0 - 0.5) = 0.3 / 0.5 = 0.6.
    """
    empty = np.empty((0, 4), dtype=float)
    one_box = np.array([[10.0, 10.0, 30.0, 30.0]], dtype=float)

    annot_a: list[np.ndarray] = []
    annot_b: list[np.ndarray] = []

    # 4 images: A=No, B=No
    for _ in range(4):
        annot_a.append(empty)
        annot_b.append(empty)
    # 1 image: A=No, B=Yes
    annot_a.append(empty)
    annot_b.append(one_box)
    # 1 image: A=Yes, B=No
    annot_a.append(one_box)
    annot_b.append(empty)
    # 4 images: A=Yes, B=Yes
    for _ in range(4):
        annot_a.append(one_box)
        annot_b.append(one_box)

    report = agreement(annot_a, annot_b, iou_threshold=0.5)
    assert report.n_images == 10
    assert math.isclose(report.image_presence_kappa, 0.6, abs_tol=1e-12)


def test_match_boxes_and_f1_hand_computed():
    """Hand-computed test for match_boxes and F1 score.

    Boxes A:
    Box 0: [0, 0, 10, 10] (area 100)
    Box 1: [20, 20, 40, 40] (area 400)
    Box 2: [50, 50, 60, 60] (area 100)

    Boxes B:
    Box 0: [0, 0, 10, 10] -> IoU with A[0] is 1.0 (matched)
    Box 1: [20, 20, 30, 40] -> intersect with A[1] is [20, 20, 30, 40], area 200.
           Area B[1] = 10 * 20 = 200.
           Union = 400 + 200 - 200 = 400. IoU = 200/400 = 0.5.
    Box 2: [100, 100, 110, 110] -> IoU with all is 0.0.

    With iou_threshold = 0.5:
    A[0] matches B[0] (IoU 1.0)
    A[1] matches B[1] (IoU 0.5)
    Total matched = 2.
    A has 3 boxes, B has 3 boxes.
    F1 = 2 * 2 / (3 + 3) = 4 / 6 = 2 / 3 = 0.6666666666666666.
    Mean IoU = (1.0 + 0.5) / 2 = 0.75.
    """
    a = np.array(
        [
            [0.0, 0.0, 10.0, 10.0],
            [20.0, 20.0, 40.0, 40.0],
            [50.0, 50.0, 60.0, 60.0],
        ]
    )
    b = np.array(
        [
            [0.0, 0.0, 10.0, 10.0],
            [20.0, 20.0, 30.0, 40.0],
            [100.0, 100.0, 110.0, 110.0],
        ]
    )

    matches = match_boxes(a, b, iou_threshold=0.5)
    assert len(matches) == 2
    assert matches[0] == (0, 0, 1.0)
    assert matches[1] == (1, 1, 0.5)

    report = agreement([a], [b], iou_threshold=0.5)
    assert report.n_images == 1
    assert report.n_a == 3
    assert report.n_b == 3
    assert report.matched == 2
    assert report.unmatched_a == 1
    assert report.unmatched_b == 1
    assert math.isclose(report.f1, 2.0 / 3.0, rel_tol=1e-12)
    assert math.isclose(report.mean_iou_matched, 0.75, rel_tol=1e-12)


def test_identical_sets_perfect_score():
    """Identical sets must yield F1 = 1.0 and mean IoU = 1.0."""
    boxes = np.array(
        [
            [10.0, 20.0, 30.0, 40.0],
            [50.0, 60.0, 80.0, 90.0],
        ]
    )
    report = agreement([boxes, boxes], [boxes, boxes], iou_threshold=0.5)
    assert report.n_images == 2
    assert report.n_a == 4
    assert report.n_b == 4
    assert report.matched == 4
    assert report.unmatched_a == 0
    assert report.unmatched_b == 0
    assert report.f1 == 1.0
    assert report.mean_iou_matched == 1.0
    assert math.isnan(report.image_presence_kappa)  # every image has boxes: kappa undefined

    rep_dict = report.to_dict()
    assert isinstance(rep_dict, dict)
    assert rep_dict["f1"] == 1.0


def test_empty_annotations_and_nan_values():
    """Both annotators having no boxes yields F1 = 1.0 and mean_iou = NaN."""
    empty = np.empty((0, 4), dtype=float)
    report = agreement([empty, empty], [empty, empty])
    assert report.n_images == 2
    assert report.n_a == 0
    assert report.n_b == 0
    assert report.matched == 0
    assert report.f1 == 1.0
    assert math.isnan(report.mean_iou_matched)
    # Both annotators always have 0 boxes: expected agreement p_e = 1.0 -> kappa is NaN
    assert math.isnan(report.image_presence_kappa)


def test_length_mismatch_raises_error():
    """Mismatched sequence lengths should raise ValueError."""
    empty = np.empty((0, 4), dtype=float)
    with pytest.raises(ValueError, match="Length mismatch"):
        agreement([empty], [empty, empty])


def test_bad_box_shape_raises_error():
    """Arrays with incorrect dimensions or shape should raise ValueError."""
    with pytest.raises(ValueError, match="must have shape"):
        match_boxes(np.array([1.0, 2.0, 3.0]), np.empty((0, 4)))

    with pytest.raises(ValueError, match="must have shape"):
        agreement([np.ones((2, 5))], [np.ones((2, 4))])


def test_yolo_round_trip(tmp_path: Path):
    """Test load_yolo_dir and compare_dirs with files written to tmp_path."""
    dir_a = tmp_path / "annotator_a"
    dir_b = tmp_path / "annotator_b"
    dir_a.mkdir()
    dir_b.mkdir()

    # Image 0: size 200x100
    # YOLO box: cls=0, cx=0.5, cy=0.5, w=0.4, h=0.2
    # x1 = (0.5 - 0.2) * 200 = 60, x2 = (0.5 + 0.2) * 200 = 140
    # y1 = (0.5 - 0.1) * 100 = 40, y2 = (0.5 + 0.1) * 100 = 60
    (dir_a / "img0.txt").write_text("0 0.5 0.5 0.4 0.2\n", encoding="utf-8")
    (dir_b / "img0.txt").write_text("0 0.5 0.5 0.4 0.2\n", encoding="utf-8")

    # Image 1: size 100x100
    # Annotator A has a box, B has no file (missing)
    (dir_a / "img1.txt").write_text("1 0.25 0.25 0.5 0.5\n", encoding="utf-8")

    image_sizes = {
        "img0": (200, 100),
        "img1": (100, 100),
    }

    labels_a = load_yolo_dir(dir_a, image_sizes)
    labels_b = load_yolo_dir(dir_b, image_sizes)

    expected_img0 = np.array([[60.0, 40.0, 140.0, 60.0]])
    np.testing.assert_allclose(labels_a["img0"], expected_img0)
    np.testing.assert_allclose(labels_b["img0"], expected_img0)

    # Missing file for img1 in B should result in (0, 4) array
    assert labels_b["img1"].shape == (0, 4)
    assert len(labels_a["img1"]) == 1

    report = compare_dirs(dir_a, dir_b, image_sizes, iou_threshold=0.5)
    assert isinstance(report, AgreementReport)
    assert report.n_images == 2
    assert report.n_a == 2
    assert report.n_b == 1
    assert report.matched == 1
    assert report.unmatched_a == 1
    assert report.unmatched_b == 0
    assert math.isclose(report.f1, 2.0 * 1 / (2 + 1), rel_tol=1e-12)
    assert math.isclose(report.mean_iou_matched, 1.0, rel_tol=1e-12)
    # img0: A=yes, B=yes
    # img1: A=yes, B=no
    # A: [yes, yes] -> p_yes = 1, p_no = 0
    # B: [yes, no]  -> p_yes = 0.5, p_no = 0.5
    # p_o = 1/2 = 0.5
    # p_e = 1.0 * 0.5 + 0.0 * 0.5 = 0.5
    # kappa = (0.5 - 0.5) / (1 - 0.5) = 0.0
    assert math.isclose(report.image_presence_kappa, 0.0, abs_tol=1e-12)
