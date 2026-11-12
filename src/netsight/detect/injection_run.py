"""WP6 experiment: inject targets into held-out test surveys and measure Pd at the survey's own
operating threshold (label-free count threshold, same rule as the reported contacts).

Per test image: one transplanted real object (cut from another image of the same survey, so the
detector never trained on it) and one parametric reference target (block with shadow, or flat
patch), each placed where the detector saw nothing and no labelled object lies. The base
detections come from the existing prediction dump of the same model (same images, same order).

    python -m netsight.detect.injection_run --model runs/research_v0.4/model \
        --dump runs/calib_v0.4 --out runs/injection_v0.4
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

DATASETS = ("mine", "ghostvision", "ghostvision_shift", "aquascan", "subpipe", "sctd")


def _median_size(boxes: list[np.ndarray]) -> float:
    b = np.concatenate([np.asarray(x, float).reshape(-1, 4) for x in boxes] or [np.zeros((0, 4))])
    if not len(b):
        return 24.0
    return float(np.median(np.sqrt((b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1]))))


def _real_recall(preds, gts, groups, thresholds, iou: float) -> dict[str, tuple[int, int]]:
    """Per survey: (real objects detected at the survey threshold, real objects)."""
    from netsight.detect.evaluation import match_detections

    out: dict[str, list[int]] = {}
    for g in sorted(set(groups)):
        idx = [i for i, x in enumerate(groups) if x == g]
        m = match_detections([preds[i] for i in idx], [gts[i] for i in idx], iou_threshold=iou)
        sel = (np.asarray(m.scores) >= thresholds[g]) & np.asarray(m.is_tp, bool)
        out[g] = [int(sel.sum()), int(m.n_gt)]
    return {g: (k, n) for g, (k, n) in out.items()}


def run(
    model_dir: Path,
    dump: Path,
    out: Path,
    *,
    budget: float,
    max_images: int,
    seed: int,
    datasets: tuple[str, ...],
) -> dict:
    import torch
    from transformers import AutoImageProcessor, DFineForObjectDetection

    from netsight.config import data_dir
    from netsight.demo.run_survey import _groups, _load_set
    from netsight.detect.operating_run import count_threshold
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache
    from netsight.detect.tta import predict_image_tta
    from netsight.trust.injection import (
        parametric_target,
        run_trials,
        template_from_box,
        texture_cuts,
        with_strata,
    )
    from netsight.trust.pd_report import pd_table, range_bin, realism_check

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DFineForObjectDetection.from_pretrained(model_dir).to(device).eval()
    processor = AutoImageProcessor.from_pretrained(model_dir)
    root = data_dir()
    splits = build_splits(root)["test"]
    pixels = PixelCache(root / "cache" / "pixels")
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    summary: dict = {
        "model": str(model_dir),
        "budget_fa_per_image": budget,
        "seed": seed,
        "sets": {},
    }

    def predict(image: np.ndarray):
        with torch.inference_mode():
            return predict_image_tta(
                model, processor, image, tile_px=640, device=device, views="none"
            )

    all_rows = []
    for name in datasets:
        path = dump / f"test_{name}.npz"
        if not path.exists():
            continue
        t0 = time.perf_counter()
        preds, gts = _load_set(path)
        groups = _groups(path, len(preds))
        samples = splits[name]
        if len(samples) != len(preds):
            raise ValueError(f"{name}: dump has {len(preds)} images, split has {len(samples)}")
        thresholds = {}
        for g in sorted(set(groups)):
            idx = [i for i, x in enumerate(groups) if x == g]
            scores = np.concatenate([preds[i][1] for i in idx] or [np.zeros(0)])
            thresholds[g] = count_threshold(scores, len(idx), budget)

        # Sources for transplants: labelled objects per survey (box at least 6 px a side).
        sources: dict[str, list[tuple[int, np.ndarray]]] = {}
        for i, (g, gt) in enumerate(zip(groups, gts, strict=True)):
            for b in np.asarray(gt, float).reshape(-1, 4):
                if b[2] - b[0] >= 6 and b[3] - b[1] >= 6:
                    sources.setdefault(g, []).append((i, b))
        size = int(round(max(_median_size(gts), 8)))

        order = rng.permutation(len(preds))[:max_images]
        chosen = sorted(int(i) for i in order)
        images = [np.asarray(pixels.get(samples[i]), np.uint8) for i in chosen]

        def templates(
            k: int,
            r: np.random.Generator,
            chosen=chosen,
            groups=groups,
            sources=sources,
            size=size,
            samples=samples,
            name=name,
        ):
            i = chosen[k]
            out_t = []
            pool = [s for s in sources.get(groups[i], []) if s[0] != i]
            if pool:
                j, box = pool[int(r.integers(len(pool)))]
                src = np.asarray(pixels.get(samples[j]), np.uint8)
                out_t.append(template_from_box(src, box, source=f"{name}:{j}"))
            if r.random() < 0.5:
                side = "right" if r.random() < 0.5 else "left"
                out_t.append(parametric_target("block", size, shadow_px=size, shadow_side=side))
            else:
                out_t.append(parametric_target("flat_patch", size))
            return out_t

        trials = run_trials(
            images,
            [groups[i] for i in chosen],
            [gts[i] for i in chosen],
            [preds[i] for i in chosen],
            templates,
            predict,
            rng=rng,
        )
        cuts = texture_cuts([t.texture for t in trials])
        trials = with_strata(trials, cuts)
        with (out / f"trials_{name}.jsonl").open("w", encoding="utf-8") as f:
            for t in trials:
                f.write(
                    json.dumps({**t.to_dict(), "dataset": name, "threshold": thresholds[t.group]})
                    + "\n"
                )

        real = _real_recall(preds, gts, groups, thresholds, iou=0.3)
        real_k = sum(k for k, _ in real.values())
        real_n = sum(n for _, n in real.values())
        tr = [t for t in trials if t.kind == "transplant"]
        tr_k = sum(t.detected(thresholds[t.group]) for t in tr)
        by_kind = pd_table(trials, thresholds, by=("kind",))
        by_stratum = pd_table(trials, thresholds, by=("kind", "stratum"))
        by_range = pd_table(
            trials,
            thresholds,
            by=("kind", "range"),
            key_fn={"range": range_bin([0, 0.25, 0.5, 0.75, 1.0])},
        )
        summary["sets"][name] = {
            "images": len(chosen),
            "trials": len(trials),
            "parametric_size_px": size,
            "texture_cuts": cuts,
            "thresholds": thresholds,
            "realism_transplant_vs_real": realism_check(tr_k, len(tr), real_k, real_n),
            "pd_by_kind": by_kind,
            "pd_by_kind_stratum": by_stratum,
            "pd_by_kind_range": by_range,
            "seconds": round(time.perf_counter() - t0, 1),
        }
        all_rows.extend({**r, "dataset": name} for r in by_kind)
        print(name, json.dumps(summary["sets"][name]["realism_transplant_vs_real"]), flush=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir

    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--model", default="runs/research_v0.4/model")
    p.add_argument("--dump", default="runs/calib_v0.4")
    p.add_argument("--out", default="runs/injection_v0.4")
    p.add_argument("--budget", type=float, default=1.0)
    p.add_argument("--max-images", type=int, default=150)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--datasets", default=",".join(DATASETS))
    a = p.parse_args(argv)
    root = data_dir()
    run(
        root / a.model,
        root / a.dump,
        root / a.out,
        budget=a.budget,
        max_images=a.max_images,
        seed=a.seed,
        datasets=tuple(a.datasets.split(",")),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
