"""Run the WP7 gate measurement on a prediction dump (CPU only).

python -m netsight.detect.withdrawal_run --dump runs/calib_v0.4 --out runs/withdrawal_v0.4.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ENVELOPE_OF = {"ghostvision_shift": "ghostvision"}


def run(dump: Path, budget: float = 1.0) -> dict:
    from netsight.demo.run_survey import (
        _flatten,
        _groups,
        _load_set,
        fit_calibrator,
        geometry_claim,
        validation_recall,
    )
    from netsight.detect.evaluation import match_detections
    from netsight.detect.operating_run import count_threshold
    from netsight.trust.calibration_metrics import expected_calibration_error
    from netsight.trust.geometry_gate import AspectProfile, GeometryEnvelope
    from netsight.trust.withdrawal_eval import (
        BLOCK_IMAGES,
        ECE_LIMIT,
        MIN_BLOCK_DETECTIONS,
        BlockResult,
        envelope_distance,
        summarise,
    )

    calibrator, _ = fit_calibrator(dump)
    info = json.loads((dump / "info.json").read_text(encoding="utf-8"))
    blocks: list[BlockResult] = []
    for set_name in sorted(info["sets"]):
        if not set_name.startswith("test_"):
            continue
        dataset = set_name.removeprefix("test_")
        env_set = ENVELOPE_OF.get(dataset, dataset)
        if f"val_{env_set}" not in info["sets"]:
            continue
        preds, gts = _load_set(dump / f"{set_name}.npz")
        groups = _groups(dump / f"{set_name}.npz", len(preds))
        rec, (rec_lo, _) = validation_recall(dump, budget, env_set)
        # Envelope of the same kind of data, as in the dashboard (validation groups).
        profiles = []
        vpreds, _ = _load_set(dump / f"val_{env_set}.npz")
        vgroups = _groups(dump / f"val_{env_set}.npz", len(vpreds))
        for g in sorted(set(vgroups)):
            b, s = _flatten([p for p, x in zip(vpreds, vgroups, strict=True) if x == g])
            profiles.append(AspectProfile.from_boxes(b, s, min_score=0.3))
        envelope = GeometryEnvelope.from_profiles(profiles, min_boxes=30)
        for g in sorted(set(groups)):
            idx = [i for i, x in enumerate(groups) if x == g]
            for start in range(0, len(idx), BLOCK_IMAGES):
                part = idx[start : start + BLOCK_IMAGES]
                if len(part) < BLOCK_IMAGES // 2:
                    continue
                bp, bg = [preds[i] for i in part], [gts[i] for i in part]
                boxes, scores = _flatten(bp)
                claim = geometry_claim(dump, boxes, scores, env_set)
                prof = AspectProfile.from_boxes(boxes, scores, min_score=0.3)
                dist = (
                    envelope_distance(
                        prof.median_log_aspect,
                        prof.median_side_px,
                        envelope.log_aspect_range,
                        envelope.side_px_range,
                    )
                    if prof.n_boxes >= 30
                    else float("nan")
                )
                m = match_detections(bp, bg, iou_threshold=0.5)
                ms = np.asarray(m.scores, float)
                tp = np.asarray(m.is_tp, bool)
                keep = ms >= 0.05
                ece = (
                    expected_calibration_error(calibrator.predict(ms[keep]), tp[keep])
                    if keep.sum() >= MIN_BLOCK_DETECTIONS
                    else float("nan")
                )
                thr = count_threshold(scores, len(part), budget)
                recall = float((tp & (ms >= thr)).sum() / m.n_gt) if m.n_gt else float("nan")
                reasons = []
                if np.isfinite(ece) and ece > ECE_LIMIT:
                    reasons.append(f"ECE {ece:.3f} > {ECE_LIMIT}")
                if np.isfinite(recall) and m.n_gt >= 10 and recall < rec_lo:
                    reasons.append(f"recall {recall:.2f} < validation floor {rec_lo:.2f}")
                blocks.append(
                    BlockResult(
                        dataset=dataset,
                        survey=str(g),
                        block=start // BLOCK_IMAGES,
                        n_images=len(part),
                        n_detections=int(keep.sum()),
                        gate_level=claim.level,
                        gate_distance=dist,
                        ece=float(ece),
                        recall=recall,
                        recall_floor=float(rec_lo),
                        failed=bool(reasons),
                        failure="; ".join(reasons),
                    )
                )
    return {"summary": summarise(blocks), "blocks": [b.to_dict() for b in blocks]}


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir

    p = argparse.ArgumentParser()
    p.add_argument("--dump", default="runs/calib_v0.4")
    p.add_argument("--out", default="runs/withdrawal_v0.4.json")
    p.add_argument("--budget", type=float, default=1.0)
    a = p.parse_args(argv)
    res = run(data_dir() / a.dump, a.budget)
    (data_dir() / a.out).write_text(json.dumps(res, indent=2, default=float), encoding="utf-8")
    print(json.dumps(res["summary"], indent=2))
    for b in res["blocks"]:
        print(
            b["dataset"],
            b["survey"],
            b["block"],
            b["gate_level"],
            round(b["gate_distance"], 3),
            round(b["ece"], 3),
            round(b["recall"], 2),
            b["failure"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
