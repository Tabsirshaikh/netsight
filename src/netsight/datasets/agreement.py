"""Inter-annotator agreement metrics and YOLO label loaders for bounding boxes."""

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


def _validate_boxes(boxes: np.ndarray, name: str = "boxes") -> np.ndarray:
    """Validate and format a bounding box array to shape (N, 4)."""
    arr = np.asarray(boxes, dtype=float)
    if arr.ndim == 1 and arr.size == 0:
        return arr.reshape(0, 4)
    if arr.ndim != 2 or arr.shape[1] != 4:
        raise ValueError(f"{name} must have shape (N, 4), got {arr.shape}")
    return arr


def match_boxes(
    a: np.ndarray,
    b: np.ndarray,
    iou_threshold: float = 0.5,
) -> list[tuple[int, int, float]]:
    """Greedy one-to-one matching of bounding boxes by IoU descending.

    Ties are broken by ascending index pair (i, j). Only pairs with IoU >= threshold
    are matched.

    Parameters
    ----------
    a : np.ndarray
        Array of shape (N, 4) in xyxy pixel coordinates.
    b : np.ndarray
        Array of shape (M, 4) in xyxy pixel coordinates.
    iou_threshold : float, default=0.5
        Minimum IoU required for a match.

    Returns
    -------
    list[tuple[int, int, float]]
        List of (index_a, index_b, iou) tuples for each matched pair.
    """
    if iou_threshold < 0.0 or iou_threshold > 1.0:
        raise ValueError(f"iou_threshold must be in [0.0, 1.0], got {iou_threshold}")

    boxes_a = _validate_boxes(a, "a")
    boxes_b = _validate_boxes(b, "b")

    n_a = len(boxes_a)
    n_b = len(boxes_b)
    if n_a == 0 or n_b == 0:
        return []

    # Calculate intersection coordinates
    inter_x1 = np.maximum(boxes_a[:, 0, None], boxes_b[None, :, 0])
    inter_y1 = np.maximum(boxes_a[:, 1, None], boxes_b[None, :, 1])
    inter_x2 = np.minimum(boxes_a[:, 2, None], boxes_b[None, :, 2])
    inter_y2 = np.minimum(boxes_a[:, 3, None], boxes_b[None, :, 3])

    inter_w = np.maximum(0.0, inter_x2 - inter_x1)
    inter_h = np.maximum(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = np.maximum(0.0, boxes_a[:, 2] - boxes_a[:, 0]) * np.maximum(
        0.0, boxes_a[:, 3] - boxes_a[:, 1]
    )
    area_b = np.maximum(0.0, boxes_b[:, 2] - boxes_b[:, 0]) * np.maximum(
        0.0, boxes_b[:, 3] - boxes_b[:, 1]
    )

    union = area_a[:, None] + area_b[None, :] - inter_area
    with np.errstate(divide="ignore", invalid="ignore"):
        iou_matrix = np.where(union > 0.0, inter_area / union, 0.0)

    # Collect valid candidates meeting the IoU threshold
    candidates: list[tuple[float, int, int]] = []
    for i in range(n_a):
        for j in range(n_b):
            iou_val = float(iou_matrix[i, j])
            if iou_val >= iou_threshold:
                candidates.append((iou_val, i, j))

    # Sort descending by IoU, ascending by (i, j) for deterministic tie breaking
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))

    used_a: set[int] = set()
    used_b: set[int] = set()
    matches: list[tuple[int, int, float]] = []

    for iou_val, i, j in candidates:
        if i not in used_a and j not in used_b:
            used_a.add(i)
            used_b.add(j)
            matches.append((i, j, iou_val))

    return matches


@dataclass(frozen=True)
class AgreementReport:
    """Inter-annotator agreement statistics."""

    n_images: int
    n_a: int
    n_b: int
    matched: int
    f1: float
    mean_iou_matched: float
    image_presence_kappa: float
    unmatched_a: int
    unmatched_b: int

    def to_dict(self) -> dict[str, Any]:
        """Convert report to a dictionary."""
        return asdict(self)


def _compute_cohens_kappa(has_a: list[bool], has_b: list[bool]) -> float:
    """Compute Cohen's kappa for binary presence across images."""
    n = len(has_a)
    if n == 0:
        return float("nan")

    both_yes = sum(1 for a, b in zip(has_a, has_b, strict=True) if a and b)
    both_no = sum(1 for a, b in zip(has_a, has_b, strict=True) if not a and not b)

    p_o = (both_yes + both_no) / n

    p_yes_a = sum(1 for a in has_a if a) / n
    p_no_a = 1.0 - p_yes_a

    p_yes_b = sum(1 for b in has_b if b) / n
    p_no_b = 1.0 - p_yes_b

    p_e = (p_yes_a * p_yes_b) + (p_no_a * p_no_b)

    if math.isclose(p_e, 1.0, rel_tol=1e-12, abs_tol=1e-12):
        return float("nan")

    return (p_o - p_e) / (1.0 - p_e)


def agreement(
    annot_a: Sequence[np.ndarray],
    annot_b: Sequence[np.ndarray],
    iou_threshold: float = 0.5,
) -> AgreementReport:
    """Compute inter-annotator agreement metrics across paired image annotations.

    Parameters
    ----------
    annot_a : Sequence[np.ndarray]
        List of bounding box arrays (N_i, 4) for annotator A.
    annot_b : Sequence[np.ndarray]
        List of bounding box arrays (M_i, 4) for annotator B.
    iou_threshold : float, default=0.5
        IoU threshold for box matching.

    Returns
    -------
    AgreementReport
        Calculated agreement metrics.
    """
    if len(annot_a) != len(annot_b):
        raise ValueError(
            f"Length mismatch: annot_a has {len(annot_a)} items, annot_b has {len(annot_b)} items"
        )

    n_images = len(annot_a)
    total_a = 0
    total_b = 0
    total_matched = 0
    sum_iou = 0.0

    has_a: list[bool] = []
    has_b: list[bool] = []

    for boxes_a, boxes_b in zip(annot_a, annot_b, strict=True):
        arr_a = _validate_boxes(boxes_a, "annot_a item")
        arr_b = _validate_boxes(boxes_b, "annot_b item")

        n_a = len(arr_a)
        n_b = len(arr_b)
        total_a += n_a
        total_b += n_b

        has_a.append(n_a > 0)
        has_b.append(n_b > 0)

        matches = match_boxes(arr_a, arr_b, iou_threshold=iou_threshold)
        total_matched += len(matches)
        sum_iou += sum(iou for _, _, iou in matches)

    if total_a + total_b == 0:
        f1 = 1.0
    else:
        f1 = (2.0 * total_matched) / (total_a + total_b)

    mean_iou = sum_iou / total_matched if total_matched > 0 else float("nan")
    kappa = _compute_cohens_kappa(has_a, has_b)

    return AgreementReport(
        n_images=n_images,
        n_a=total_a,
        n_b=total_b,
        matched=total_matched,
        f1=f1,
        mean_iou_matched=mean_iou,
        image_presence_kappa=kappa,
        unmatched_a=total_a - total_matched,
        unmatched_b=total_b - total_matched,
    )


def load_yolo_dir(
    label_dir: str | Path,
    image_sizes: Mapping[str, tuple[int, int]],
) -> dict[str, np.ndarray]:
    """Load YOLO format labels from a directory for given image stems.

    Parameters
    ----------
    label_dir : str | Path
        Directory containing YOLO .txt label files.
    image_sizes : Mapping[str, tuple[int, int]]
        Mapping from image stem to (width, height) pixel dimensions.

    Returns
    -------
    dict[str, np.ndarray]
        Mapping from image stem to (N, 4) xyxy pixel boxes.
    """
    directory = Path(label_dir)
    result: dict[str, np.ndarray] = {}

    for stem, (width, height) in image_sizes.items():
        if width <= 0 or height <= 0:
            raise ValueError(
                f"Image dimensions must be positive, got ({width}, {height}) for {stem}"
            )

        txt_file = directory / f"{stem}.txt"
        if not txt_file.is_file():
            result[stem] = np.empty((0, 4), dtype=float)
            continue

        boxes: list[list[float]] = []
        with txt_file.open("r", encoding="utf-8") as f:
            for line_no, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 5:
                    raise ValueError(
                        f"Malformed YOLO line {line_no} in {txt_file}: expected at least 5 tokens"
                    )
                try:
                    cx = float(parts[1])
                    cy = float(parts[2])
                    w = float(parts[3])
                    h = float(parts[4])
                except ValueError as err:
                    raise ValueError(
                        f"Invalid numeric value on line {line_no} in {txt_file}"
                    ) from err

                x1 = (cx - w / 2.0) * width
                y1 = (cy - h / 2.0) * height
                x2 = (cx + w / 2.0) * width
                y2 = (cy + h / 2.0) * height
                boxes.append([x1, y1, x2, y2])

        if boxes:
            result[stem] = np.array(boxes, dtype=float)
        else:
            result[stem] = np.empty((0, 4), dtype=float)

    return result


def compare_dirs(
    dir_a: str | Path,
    dir_b: str | Path,
    image_sizes: Mapping[str, tuple[int, int]],
    iou_threshold: float = 0.5,
) -> AgreementReport:
    """Compare annotations from two YOLO directories over sorted stems.

    Parameters
    ----------
    dir_a : str | Path
        Directory with annotations from annotator A.
    dir_b : str | Path
        Directory with annotations from annotator B.
    image_sizes : Mapping[str, tuple[int, int]]
        Mapping from image stem to (width, height) pixel dimensions.
    iou_threshold : float, default=0.5
        IoU threshold for box matching.

    Returns
    -------
    AgreementReport
        Calculated agreement report.
    """
    stems = sorted(image_sizes.keys())
    labels_a = load_yolo_dir(dir_a, image_sizes)
    labels_b = load_yolo_dir(dir_b, image_sizes)

    annot_a = [labels_a[s] for s in stems]
    annot_b = [labels_b[s] for s in stems]

    return agreement(annot_a, annot_b, iou_threshold=iou_threshold)
