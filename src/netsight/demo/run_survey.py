"""Build a trust-layer evidence pack from one held-out survey."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from netsight.trust.applicability import ClaimDecision
    from netsight.trust.calibrators import BetaCalibrator

type FloatArray = NDArray[np.float64]
type Prediction = tuple[FloatArray, FloatArray]


@dataclass(frozen=True, slots=True)
class SurveyDetections:
    """Selected predictions, groups, and original dump image indices."""

    predictions: list[Prediction]
    groups: list[str]
    image_indices: list[int]
    total_images: int

    @property
    def n_images(self) -> int:
        """Return the number of selected images, including empty images."""
        return len(self.predictions)


def _validation_names(pred_dir: Path) -> list[str]:
    """Read validation set names from the dump manifest."""
    info = json.loads((pred_dir / "info.json").read_text(encoding="utf-8"))
    names = sorted(name for name in info["sets"] if name.startswith("val_"))
    if not names:
        raise ValueError("The dump contains no validation sets.")
    return names


def _load_set(path: Path) -> tuple[list[Prediction], list[FloatArray]]:
    """Load and normalize a prediction dump."""
    from netsight.detect.calibrate_run import load_predictions

    predictions, ground_truth = load_predictions(path)
    if len(predictions) != len(ground_truth):
        raise ValueError(f"Prediction/ground-truth image count mismatch: {path}")
    normalized = [
        (np.asarray(boxes, dtype=np.float64), np.asarray(scores, dtype=np.float64))
        for boxes, scores in predictions
    ]
    return normalized, [np.asarray(boxes, dtype=np.float64) for boxes in ground_truth]


def _groups(path: Path, n_images: int) -> list[str]:
    """Load groups and check their alignment with images."""
    from netsight.detect.calibrate_run import load_groups

    groups = [str(group) for group in load_groups(path)]
    if len(groups) != n_images:
        raise ValueError(f"Group/image count mismatch: {path}")
    return groups


def _flatten(predictions: list[Prediction]) -> Prediction:
    """Pool boxes and scores, preserving alignment."""
    if not predictions:
        return np.empty((0, 4), dtype=np.float64), np.empty(0, dtype=np.float64)
    return (
        np.concatenate([boxes for boxes, _ in predictions], axis=0),
        np.concatenate([scores for _, scores in predictions]),
    )


def fit_calibrator(pred_dir: Path) -> tuple[BetaCalibrator, dict[str, Any]]:
    """Fit pooled validation detections and return calibration metadata."""
    from netsight.detect.evaluation import match_detections
    from netsight.trust.calibrators import BetaCalibrator

    score_parts = []
    label_parts = []
    for name in _validation_names(pred_dir):
        predictions, ground_truth = _load_set(pred_dir / f"{name}.npz")
        matched = match_detections(predictions, ground_truth, iou_threshold=0.5)
        scores = np.asarray(matched.scores, dtype=np.float64)
        labels = np.asarray(matched.is_tp, dtype=bool)
        keep = scores >= 0.05
        score_parts.append(scores[keep])
        label_parts.append(labels[keep])

    scores = np.concatenate(score_parts)
    labels = np.concatenate(label_parts)
    if scores.size == 0 or np.unique(labels).size != 2:
        raise ValueError("Calibration requires both TP and FP validation scores >= 0.05.")
    calibrator = BetaCalibrator().fit(scores, labels)
    metadata = {
        "method": "beta",
        "fitted_on": "pooled validation detections",
        "n_fit": int(scores.size),
        "positives_fit": int(labels.sum()),
    }
    return calibrator, metadata


def survey_detections(pred_dir: Path, set_name: str, group: str | None = None) -> SurveyDetections:
    """Select test images without losing their original dump indices."""
    name = f"test_{set_name}"
    info = json.loads((pred_dir / "info.json").read_text(encoding="utf-8"))
    if name not in info["sets"]:
        raise ValueError(f"Unknown test set: {set_name}")
    path = pred_dir / f"{name}.npz"
    predictions, _ = _load_set(path)
    groups = _groups(path, len(predictions))
    indices = [i for i, value in enumerate(groups) if group is None or value == group]
    if not indices:
        raise ValueError(f"No images selected for set={set_name!r}, group={group!r}.")
    return SurveyDetections(
        predictions=[predictions[i] for i in indices],
        groups=[groups[i] for i in indices],
        image_indices=indices,
        total_images=len(predictions),
    )


def validation_recall(pred_dir: Path, budget: float) -> tuple[float, tuple[float, float]]:
    """Estimate pooled recall using a separate budget threshold per validation set."""
    from netsight.detect.evaluation import match_detections
    from netsight.detect.operating_run import count_threshold
    from netsight.trust.bounds import clopper_pearson

    _check_budget(budget)
    successes = 0
    objects = 0
    for name in _validation_names(pred_dir):
        predictions, ground_truth = _load_set(pred_dir / f"{name}.npz")
        if not predictions:
            continue
        _, scores = _flatten(predictions)
        threshold = count_threshold(scores, len(predictions), budget)
        matched = match_detections(predictions, ground_truth, iou_threshold=0.5)
        selected = np.asarray(matched.scores) >= threshold
        successes += int(np.count_nonzero(np.asarray(matched.is_tp, dtype=bool) & selected))
        objects += int(matched.n_gt)

    if objects == 0:
        raise ValueError("Validation recall requires at least one ground-truth object.")
    lo, hi = clopper_pearson(successes, objects)
    return successes / objects, (float(lo), float(hi))


def geometry_claim(
    pred_dir: Path, survey_boxes: FloatArray, survey_scores: FloatArray
) -> ClaimDecision:
    """Compare survey pixel geometry with validation-group profiles."""
    from netsight.trust.applicability import ClaimDecision
    from netsight.trust.geometry_gate import (
        AspectProfile,
        GeometryEnvelope,
        geometry_reasons,
    )

    profiles = []
    for name in _validation_names(pred_dir):
        path = pred_dir / f"{name}.npz"
        predictions, _ = _load_set(path)
        groups = _groups(path, len(predictions))
        for group in sorted(set(groups)):
            selected = [
                prediction
                for prediction, value in zip(predictions, groups, strict=True)
                if value == group
            ]
            boxes, scores = _flatten(selected)
            profiles.append(AspectProfile.from_boxes(boxes, scores, min_score=0.3))

    envelope = GeometryEnvelope.from_profiles(profiles, min_boxes=30)
    profile = AspectProfile.from_boxes(survey_boxes, survey_scores, min_score=0.3)
    reasons = geometry_reasons(profile, envelope)
    if reasons:
        return ClaimDecision(
            level="indicative",
            reasons=reasons,
            statement=(
                "Probabilities are indicative: this survey's pixel geometry differs "
                "from the validation surveys."
            ),
        )
    return ClaimDecision(
        level="calibrated",
        reasons=reasons,
        statement="Probabilities are calibrated on validation surveys with similar pixel geometry.",
    )


def _check_budget(budget: float) -> None:
    """Reject non-finite or negative budgets."""
    if not np.isfinite(budget) or budget < 0:
        raise ValueError("Budget must be finite and non-negative.")


def _sha256(path: Path) -> str:
    """Hash a file without reading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contacts(
    survey: SurveyDetections,
    set_name: str,
    threshold: float,
    calibrator: BetaCalibrator,
) -> list[Any]:
    """Load selected pixels and produce evidence for flagged detections."""
    from netsight.config import data_dir
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache
    from netsight.evidence import evidence_features
    from netsight.report.evidence_pack import Contact

    samples = build_splits(data_dir())["test"][set_name]
    if len(samples) != survey.total_images:
        raise ValueError("Pixel samples and test dump have different image counts.")
    cache = PixelCache(data_dir() / "cache" / "pixels")
    contacts = []
    entries = zip(survey.image_indices, survey.groups, survey.predictions, strict=True)
    for image_index, group, (boxes, scores) in entries:
        sample = samples[image_index]
        if str(sample.group) != group:
            raise ValueError(f"Pixel sample/dump group mismatch at image {image_index}.")
        flagged_indices = np.flatnonzero(scores >= threshold)
        if flagged_indices.size == 0:
            continue
        image = cache.get(sample)
        probabilities = calibrator.predict(scores[flagged_indices])
        for k, probability in zip(flagged_indices, probabilities, strict=True):
            box = boxes[k].tolist()
            contacts.append(
                Contact(
                    contact_id=f"{group}-{image_index}-{int(k)}",
                    image=str(sample.member),
                    box=box,
                    raw_score=float(scores[k]),
                    probability=float(probability),
                    evidence=evidence_features(image, box).as_dict(),
                    position=None,
                    review=None,
                )
            )
    return contacts


def _run(args: argparse.Namespace) -> str:
    """Execute the pipeline and return its final summary."""
    from netsight.detect.operating_run import count_threshold
    from netsight.report.evidence_pack import OperatingSummary, build_pack, write_pack
    from netsight.trust.provenance import Ledger

    _check_budget(args.budget)
    calibrator, calibration = fit_calibrator(args.preds)
    survey = survey_detections(args.preds, args.set_name, args.group)
    boxes, scores = _flatten(survey.predictions)
    threshold = float(count_threshold(scores, survey.n_images, args.budget))
    recall, recall_ci = validation_recall(args.preds, args.budget)
    claim = geometry_claim(args.preds, boxes, scores)
    contacts = _contacts(survey, args.set_name, threshold, calibrator)
    operating = OperatingSummary(
        method="count_threshold",
        threshold=threshold,
        budget_fa_per_unit=args.budget,
        unit="image",
        flagged=len(contacts),
        recall_estimate=recall,
        recall_ci=recall_ci,
        recall_source="validation surveys, same budget rule (not this survey)",
    )
    names = [*_validation_names(args.preds), f"test_{args.set_name}"]
    inputs = {f"{name}.npz": _sha256(args.preds / f"{name}.npz") for name in names}
    manifest = json.loads((args.model / "manifest.json").read_text(encoding="utf-8"))
    survey_id = args.group if args.group is not None else args.set_name
    created = args.created or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    pack = build_pack(
        survey_id=survey_id,
        contacts=contacts,
        claim=claim,
        manifest=manifest,
        operating=operating,
        calibration=calibration,
        created=created,
        inputs=inputs,
    )
    ledger = Ledger(args.ledger) if args.ledger is not None else None
    json_path, _ = write_pack(pack, args.out, ledger=ledger)
    return (
        f"survey={survey_id} images={survey.n_images} flagged={len(contacts)} "
        f"claim={claim.level} pack={json_path}"
    )


def main() -> None:
    """Parse CLI options and print only the final summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preds", type=Path, required=True)
    parser.add_argument("--set", dest="set_name", required=True)
    parser.add_argument("--group")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--budget", type=float, default=1.0)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--created")
    args = parser.parse_args()
    with redirect_stdout(io.StringIO()):
        summary = _run(args)
    print(summary)


if __name__ == "__main__":
    main()
