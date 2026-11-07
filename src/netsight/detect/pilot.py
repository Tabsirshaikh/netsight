"""Tile-size pilot (docs/research/step2/tiling_and_resolution.md, procedure step 4).

Trains D-FINE-S at one tile size on the mine-detection and GhostVision training groups and
scores it on held-out groups. Run once per tile size and compare:

    python -m netsight.detect.pilot --tile 320 --out <dir>
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from netsight.config import data_dir
from netsight.datasets.detection import group_split, read_ghostvision_zip, read_yolo_zip
from netsight.detect.dfine import (
    PRODUCT_CHECKPOINT,
    ImageCache,
    TileDataset,
    collate,
    load_model,
    make_optimizer,
    predict_image,
    warmup_cosine,
)
from netsight.detect.evaluation import (
    AREA_SMALL,
    average_precision,
    froc,
    match_detections,
    recall_at_fp_per_image,
)
from netsight.detect.training_tiles import TrainTile, build_train_tiles
from netsight.governance.licences import default_register_path, load_register
from netsight.models.manifest import build_training_manifest, write_manifest
from netsight.trust.provenance import Ledger

MINE_YEARS = ("2010", "2015", "2017", "2018", "2021")


def build_splits(root: Path) -> dict:
    raw = root / "raw"
    mine = read_yolo_zip([raw / "mine_detection_sss" / f"{y}.zip" for y in MINE_YEARS],
                         "mine_detection_sss", ["MILCO", "NOMBO"])
    gv = read_ghostvision_zip(raw / "ghostvision_crabpot" / "GhostVision_DatasetAndModels.zip")
    m = group_split(mine, test_groups={"2015", "2021"}, val_groups={"2017"})
    shift = [s for s in gv if s.group == "Contact"]  # targets 2.5x smaller: shifted test set
    g = group_split([s for s in gv if s.group != "Contact"],
                    test_groups={"Rec9", "Rec14", "Rec8"}, val_groups={"Rec13", "Rec2"})
    return {
        "train": m["train"] + g["train"],
        "val": {"mine": m["val"], "ghostvision": g["val"]},
        "test": {"mine": m["test"], "ghostvision": g["test"], "ghostvision_shift": shift},
    }


def balanced_tiles(samples, tile_px: int, *, neg_ratio: float, max_tiles: int, seed: int):
    """Equal tile budget per dataset, so a large dataset cannot drown a small one."""
    ids = sorted({s.dataset_id for s in samples})
    out = []
    for k, ds_id in enumerate(ids):
        idx = [i for i, s in enumerate(samples) if s.dataset_id == ds_id]
        sub = [samples[i] for i in idx]
        tiles = build_train_tiles(sub, tile_px, neg_ratio=neg_ratio,
                                  max_tiles=max_tiles // len(ids),
                                  rng=np.random.default_rng(seed * 100 + k))
        out += [TrainTile(idx[t.sample_index], t.tile, t.boxes) for t in tiles]
    return out


def subsample(samples, n: int, rng: np.random.Generator):
    """Up to n images, half with objects, for quick validation during training."""
    pos = [s for s in samples if len(s.boxes)]
    neg = [s for s in samples if not len(s.boxes)]
    k = min(len(pos), n // 2)
    picks = [pos[i] for i in rng.choice(len(pos), k, replace=False)] if k else []
    j = min(len(neg), n - k)
    picks += [neg[i] for i in rng.choice(len(neg), j, replace=False)] if j else []
    return picks


def evaluate(model, processor, samples, tile_px: int, cache: ImageCache, device: str) -> dict:
    preds, gts = [], []
    for s in samples:
        boxes, scores = predict_image(model, processor, cache.get(s), tile_px=tile_px,
                                      device=device)
        preds.append((boxes, scores))
        gts.append(s.boxes)
    m = match_detections(preds, gts)
    return {
        "n_images": len(samples),
        "n_objects": int(m.n_gt),
        "ap50": average_precision(m),
        "ap50_small": average_precision(m, size_range=AREA_SMALL),
        "recall_at_0.5_fp_per_image": recall_at_fp_per_image(m, 0.5)[0],
        "recall_at_1_fp_per_image": recall_at_fp_per_image(m, 1.0)[0],
        "froc": froc(m),
    }


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tile", type=int, required=True, help="tile size in image pixels")
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--max-tiles", type=int, default=4000, help="training tiles per epoch")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--neg-ratio", type=float, default=0.5)
    ap.add_argument("--val-images", type=int, default=120, help="per dataset, per evaluation")
    ap.add_argument("--checkpoint", default=PRODUCT_CHECKPOINT)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    splits = build_splits(data_dir())
    val = {k: subsample(v, args.val_images, rng) for k, v in splits["val"].items()}
    model, processor = load_model(args.checkpoint)
    model.to(device)
    cache = ImageCache(max_images=2048)
    opt = make_optimizer(model, args.lr)
    steps_per_epoch = -(-args.max_tiles // args.batch)
    total = steps_per_epoch * args.epochs
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: warmup_cosine(s, total, warmup=min(300, total // 10)))
    log = open(out / "train_log.jsonl", "a", encoding="utf-8")
    best, history, step = -1.0, [], 0
    for epoch in range(args.epochs):
        tiles = balanced_tiles(splits["train"], args.tile, neg_ratio=args.neg_ratio,
                               max_tiles=args.max_tiles, seed=args.seed + epoch)
        ds = TileDataset(splits["train"], tiles, processor, augment=True, seed=args.seed + epoch,
                         cache=cache)
        loader = DataLoader(ds, batch_size=args.batch, shuffle=True, collate_fn=collate,
                            num_workers=0, drop_last=True)
        model.train()
        t0, losses = time.time(), []
        for pixels, labels in loader:
            labels = [{k: v.to(device) for k, v in lab.items()} for lab in labels]
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                loss = model(pixel_values=pixels.to(device), labels=labels).loss
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite loss at step {step}")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 0.1)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            losses.append(float(loss.detach()))
            step += 1
            if step % 50 == 0:
                rate = len(losses) * args.batch / (time.time() - t0)
                log.write(json.dumps({"epoch": epoch, "step": step, "loss": np.mean(losses[-50:]),
                                      "tiles_per_s": rate}) + "\n")
                log.flush()
        metrics = {k: evaluate(model, processor, v, args.tile, cache, device)
                   for k, v in val.items()}
        score = float(np.nanmean([m["ap50"] for m in metrics.values()]))
        history.append({"epoch": epoch, "train_loss": float(np.mean(losses)),
                        "train_tiles": len(tiles), "val": metrics, "val_mean_ap50": score,
                        "seconds": time.time() - t0})
        log.write(json.dumps(history[-1]) + "\n")
        log.flush()
        if score > best:
            best = score
            model.save_pretrained(out / "model")
            processor.save_pretrained(out / "model")
    from transformers import DFineForObjectDetection

    model = DFineForObjectDetection.from_pretrained(out / "model").to(device)
    test = {k: evaluate(model, processor, v, args.tile, cache, device)
            for k, v in splits["test"].items()}
    config = {**vars(args), "device": device, "net_input": 640, "overlap": 0.25,
              "full_image_pass": True}
    (out / "metrics.json").write_text(json.dumps(
        {"config": config, "best_val_mean_ap50": best, "history": history, "test": test},
        indent=2, default=float), encoding="utf-8")
    manifest = build_training_manifest(
        ["mine_detection_sss", "ghostvision_crabpot"], load_register(default_register_path()),
        model_id=f"dfine-s-pilot-tile{args.tile}", code_version=_git_commit(), config=config)
    write_manifest(manifest, out / "model",
                   ledger=Ledger(data_dir() / "provenance" / "models.jsonl"))
    print(json.dumps({"tile": args.tile, "best_val_mean_ap50": best,
                      "test": {k: {kk: v[kk] for kk in ("ap50", "ap50_small",
                                                       "recall_at_1_fp_per_image")}
                               for k, v in test.items()}}, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
