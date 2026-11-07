"""WP5 on real detector output: freeze a threshold on validation, check it on test.

The threshold is chosen by Learn-then-Test (`netsight.trust.operating_point`) at a false-alarm
budget. Most public datasets have no swath geometry, so the area unit is one image (budget =
false alarms per image); with real navigation the same code runs per km2. Recall counts every
ground-truth object, including the ones the detector never scored.

    python -m netsight.detect.operating_run --val <dump dir> --test <dump dir> --out <file.md>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from netsight.detect.calibrate_run import load_predictions
from netsight.detect.evaluation import match_detections
from netsight.trust.bounds import clopper_pearson
from netsight.trust.operating_point import select_operating_point


def _matched(path: Path):
    preds, gts = load_predictions(path)
    m = match_detections(preds, gts)
    return np.asarray(m.scores, float), np.asarray(m.is_tp, float), int(m.n_gt), len(gts)


def _sets(pred_dir: Path, prefix: str) -> dict:
    info = json.loads((pred_dir / "info.json").read_text(encoding="utf-8"))
    return {
        k[len(prefix) :]: _matched(pred_dir / f"{k}.npz")
        for k in info["sets"]
        if k.startswith(prefix)
    }


def freeze(fit: list[tuple], budget: float, delta: float):
    """Threshold from one or more validation sets, each image one unit of area."""
    scores = np.concatenate([f[0] for f in fit])
    real = np.concatenate([f[1] for f in fit])
    surveys = np.concatenate([np.full(len(f[0]), str(i)) for i, f in enumerate(fit)]).tolist()
    areas = {str(i): float(f[3]) for i, f in enumerate(fit)}
    return select_operating_point(
        scores, real, surveys, areas, budget_fa_per_km2=budget, delta=delta
    )


def check(test: tuple, threshold: float) -> dict:
    scores, real, n_gt, n_images = test
    flagged = scores >= threshold
    tp = int(np.count_nonzero(flagged & (real == 1)))
    fa = int(np.count_nonzero(flagged & (real == 0)))
    lo, hi = clopper_pearson(tp, n_gt) if n_gt else (float("nan"), float("nan"))
    return {
        "fa_per_image": fa / n_images,
        "recall": tp / n_gt if n_gt else float("nan"),
        "recall_ci": (lo, hi),
        "tp": tp,
        "n_gt": n_gt,
        "n_images": n_images,
    }


def count_threshold(scores: np.ndarray, n_images: int, budget: float) -> float:
    """Label-free survey-adaptive threshold: flag at most budget x n_images detections.

    False alarms can never exceed flagged detections, so the false-alarm budget holds on the
    survey itself without labels (conservative: real objects use up part of the budget).
    """
    k = int(np.floor(budget * n_images))
    s = np.sort(scores)[::-1]
    if k <= 0 or not s.size:
        return float("inf")
    if k >= s.size:
        return float(s[-1])
    return float(np.nextafter(s[k], np.inf)) if s[k - 1] == s[k] else float(s[k - 1])


def run(val_dir: Path, test_dir: Path, budgets: list[float], delta: float) -> list[dict]:
    val, test = _sets(val_dir, "val_"), _sets(test_dir, "test_")
    rows = []
    for name, t in sorted(test.items()):
        own = val.get(name.removesuffix("_shift"))
        fits = {"own validation": [own] if own else None, "pooled validation": list(val.values())}
        for label, fit in fits.items():
            if not fit:
                continue
            for b in budgets:
                op = freeze(fit, b, delta)
                res = check(t, op.threshold)
                rows.append(
                    {
                        "test": name,
                        "fit": label,
                        "budget": b,
                        "threshold": op.threshold,
                        "feasible": op.feasible,
                        "val_fa_upper": op.fa_rate_upper,
                        "budget_held": res["fa_per_image"] <= b,
                        **res,
                    }
                )
        for b in budgets:
            res = check(t, count_threshold(t[0], t[3], b))
            rows.append(
                {
                    "test": name,
                    "fit": "label-free count on the test survey",
                    "budget": b,
                    "threshold": count_threshold(t[0], t[3], b),
                    "feasible": True,
                    "val_fa_upper": float("nan"),
                    "budget_held": res["fa_per_image"] <= b,
                    **res,
                }
            )
    return rows


def to_markdown(rows: list[dict], title: str, delta: float) -> str:
    lines = [
        f"# {title}",
        "",
        f"Threshold frozen on validation by Learn-then-Test (delta = {delta}); test numbers "
        "are measured once. Area unit = one image. Recall counts all objects (95% "
        "Clopper-Pearson interval).",
        "",
        "| Test set | Fitted on | Budget FA/image | Threshold | Test FA/image | Budget held "
        "| Test recall | 95% CI |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lo, hi = r["recall_ci"]
        lines.append(
            f"| {r['test']} | {r['fit']} | {r['budget']} | {r['threshold']:.3f} | "
            f"{r['fa_per_image']:.2f} | {'yes' if r['budget_held'] else '**no**'} | "
            f"{r['recall']:.3f} | {lo:.3f}-{hi:.3f} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--val", type=Path, required=True)
    ap.add_argument("--test", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--budgets", default="0.5,1.0")
    ap.add_argument("--delta", type=float, default=0.05)
    ap.add_argument("--title", default="Operating point on held-out surveys")
    args = ap.parse_args(argv)
    rows = run(args.val, args.test, [float(b) for b in args.budgets.split(",")], args.delta)
    args.out.write_text(to_markdown(rows, args.title, args.delta), encoding="utf-8")
    args.out.with_suffix(".json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
