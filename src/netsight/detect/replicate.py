"""Replication experiment: is our detector pipeline competitive, or is the gap our test protocol?

The mine-detection dataset paper (Pessanha Santos et al. 2024, Data in Brief) reports
"a mean Average Precision (AP) of 75%" for YOLOv4 "using our dataset of 1170 images", i.e.
without a described held-out set. We train two mine-only models with one identical recipe and
score each on its own test set:

- ``random``: random 70/10/20 image split (the usual protocol in papers; survey years mix);
- ``years``: whole survey years held out (2015 and 2021 test, 2017 validation), as NetSight does.

    python -m netsight.detect.replicate --out <runs>/replicate_mine

Note: our detector is class-agnostic (one "object" class); the paper's mAP averages MILCO and
NOMBO. The comparison is indicative, not exact.
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from netsight.datasets.detection import DetectionSample, drop_unreadable, group_split

MINE_YEARS = ("2010", "2015", "2017", "2018", "2021")


def random_image_split(
    samples: Sequence[DetectionSample], *, test_fraction: float, val_fraction: float, seed: int
) -> dict[str, list[DetectionSample]]:
    """Image-level random split that ignores survey groups (the protocol being compared)."""
    order = np.random.default_rng(seed).permutation(len(samples))
    n_test = round(len(samples) * test_fraction)
    n_val = round(len(samples) * val_fraction)
    pick = [samples[i] for i in order]
    return {"test": pick[:n_test], "val": pick[n_test:n_test + n_val],
            "train": pick[n_test + n_val:]}


def train_and_test(split: dict, *, epochs: int, out: Path, seed: int, tile: int = 640,
                   batch: int = 8, lr: float = 2e-4, eval_every: int = 5) -> dict:
    """Same recipe as the pilot runner (kept separate so a running pilot is never touched)."""
    import torch
    from torch.utils.data import DataLoader

    from netsight.config import data_dir
    from netsight.detect.dfine import (
        TileDataset,
        collate,
        load_model,
        make_optimizer,
        warmup_cosine,
    )
    from netsight.detect.pilot import balanced_tiles, evaluate
    from netsight.detect.pixel_cache import PixelCache

    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.backends.cudnn.benchmark = True
    torch.set_float32_matmul_precision("high")
    torch.manual_seed(seed)
    cache = PixelCache(data_dir() / "cache" / "pixels")
    model, processor = load_model()
    model.to(device)
    opt = make_optimizer(model, lr)
    n_tiles = len(balanced_tiles(split["train"], tile, neg_ratio=0.5, max_tiles=8000, seed=seed))
    total = max(1, n_tiles // batch) * epochs
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: warmup_cosine(s, total, warmup=min(300, total // 10)))
    out.mkdir(parents=True, exist_ok=True)
    best, history = -1.0, []
    for epoch in range(epochs):
        tiles = balanced_tiles(split["train"], tile, neg_ratio=0.5, max_tiles=8000,
                               seed=seed + epoch)
        ds = TileDataset(split["train"], tiles, augment=True, seed=seed + epoch, cache=cache)
        loader = DataLoader(ds, batch_size=batch, shuffle=True, collate_fn=collate,
                            num_workers=0, drop_last=True)
        model.train()
        t0, losses = time.time(), []
        for pixels, labels in loader:
            labels = [{k: v.to(device) for k, v in lab.items()} for lab in labels]
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                loss = model(pixel_values=pixels.to(device), labels=labels).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 0.1)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            losses.append(float(loss.detach()))
        row = {"epoch": epoch, "train_loss": float(np.mean(losses)), "seconds": time.time() - t0}
        if (epoch + 1) % eval_every == 0 or epoch == epochs - 1:
            val = evaluate(model, processor, split["val"], tile, cache, device)
            row["val_ap50"] = val["ap50"]
            if val["ap50"] > best:
                best = val["ap50"]
                model.save_pretrained(out / "model")
                processor.save_pretrained(out / "model")
        history.append(row)
        (out / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    from transformers import DFineForObjectDetection

    model = DFineForObjectDetection.from_pretrained(out / "model").to(device)
    test = evaluate(model, processor, split["test"], tile, cache, device)
    result = {"best_val_ap50": best, "test": test, "history": history,
              "n_images": {k: len(v) for k, v in split.items()}}
    (out / "metrics.json").write_text(json.dumps(result, indent=2, default=float),
                                      encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir
    from netsight.datasets.detection import read_yolo_zip

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    raw = data_dir() / "raw" / "mine_detection_sss"
    mine = read_yolo_zip([raw / f"{y}.zip" for y in MINE_YEARS], "mine_detection_sss",
                         ["MILCO", "NOMBO"])
    mine, _ = drop_unreadable(mine, data_dir() / "processed" / "unreadable_images.json")
    splits = {
        "random": random_image_split(mine, test_fraction=0.2, val_fraction=0.1, seed=args.seed),
        "years": group_split(mine, test_groups={"2015", "2021"}, val_groups={"2017"}),
    }
    summary = {}
    for name, split in splits.items():
        r = train_and_test(split, epochs=args.epochs, out=Path(args.out) / name, seed=args.seed)
        summary[name] = {k: r["test"][k] for k in ("ap50", "ap50_small",
                                                     "recall_at_0.5_fp_per_image",
                                                     "recall_at_1_fp_per_image")}
        summary[name]["n_test_images"] = r["n_images"]["test"]
    (Path(args.out) / "summary.json").write_text(json.dumps(summary, indent=2, default=float),
                                                 encoding="utf-8")
    print(json.dumps(summary, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
