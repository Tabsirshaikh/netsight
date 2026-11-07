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
from netsight.datasets.detection import (
    aquascan_group,
    drop_unreadable,
    group_split,
    ordered_group_split,
    read_coco_zip,
    read_ghostvision_zip,
    read_voc_zip,
    read_yolo_zip,
    subpipe_group,
)
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
from netsight.detect.pixel_cache import PixelCache
from netsight.detect.training_tiles import EarlyStopper, balanced_tiles  # noqa: F401 (re-export)
from netsight.governance.licences import default_register_path, load_register
from netsight.models.manifest import build_training_manifest, write_manifest
from netsight.trust.provenance import Ledger

MINE_YEARS = ("2010", "2015", "2017", "2018", "2021")
DATASET_IDS = {"mine": "mine_detection_sss", "ghostvision": "ghostvision_crabpot",
               "aquascan": "aquascan_1k", "subpipe": "subpipe_mini2", "sctd": "sctd"}


def build_splits(root: Path) -> dict:
    raw = root / "raw"
    cache = root / "processed" / "unreadable_images.json"
    dropped: list = []

    def readable(samples):
        kept, bad = drop_unreadable(samples, cache)
        dropped.extend(f"{s.dataset_id}:{s.member}" for s in bad)
        return kept

    mine = readable(read_yolo_zip([raw / "mine_detection_sss" / f"{y}.zip" for y in MINE_YEARS],
                         "mine_detection_sss", ["MILCO", "NOMBO"]))
    gv = readable(read_ghostvision_zip(
        raw / "ghostvision_crabpot" / "GhostVision_DatasetAndModels.zip"))
    m = group_split(mine, test_groups={"2015", "2021"}, val_groups={"2017"})
    shift = [s for s in gv if s.group == "Contact"]  # targets 2.5x smaller: shifted test set
    g = group_split([s for s in gv if s.group != "Contact"],
                    test_groups={"Rec9", "Rec14", "Rec8"}, val_groups={"Rec13", "Rec2"})
    aq = readable(read_yolo_zip([raw / "aquascan_1k" / "AquaScan-1K.zip"], "aquascan_1k", ["Human"],
                       group_fn=aquascan_group))
    a = group_split(aq, test_groups={"2025-11-23", "13SEP25"},
                    val_groups={"2025-06-29", "2025-06-15"})
    sp = readable(read_coco_zip(raw / "subpipe_mini2" / "SubPipeMini2.zip", "subpipe_mini2",
                       group_fn=subpipe_group))
    p = ordered_group_split(sp, n_val=2, n_test=3, gap=1,
                            key=lambda grp: int(grp[1:]) if grp[1:].isdigit() else -1)
    sctd_zip = raw / "research_only" / "sctd" / "SCTD2.0_VOC2007.zip"
    sc = readable(read_voc_zip(sctd_zip, "sctd")) if sctd_zip.exists() else []
    trainval = sorted((s for s in sc if s.source_split != "test"), key=lambda s: s.member)
    sc_val = trainval[::10]  # SCTD has no recording groups: official test + 10% val
    sc_train = [s for s in trainval if s not in sc_val]
    sc_test = [s for s in sc if s.source_split == "test"]
    return {
        "train": m["train"] + g["train"] + a["train"] + p["train"] + sc_train,
        "val": {"mine": m["val"], "ghostvision": g["val"], "aquascan": a["val"],
                "subpipe": p["val"], "sctd": sc_val},
        "test": {"mine": m["test"], "ghostvision": g["test"], "ghostvision_shift": shift,
                 "aquascan": a["test"], "subpipe": p["test"], "sctd": sc_test},
        "dropped_unreadable": dropped,
    }


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
    loose = match_detections(preds, gts, iou_threshold=0.3)  # elongated objects: ambiguous extent
    return {
        "n_images": len(samples),
        "n_objects": int(m.n_gt),
        "ap50": average_precision(m),
        "ap30": average_precision(loose),
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
    ap.add_argument("--val-images", type=int, default=250, help="per dataset, per evaluation")
    ap.add_argument("--patience", type=int, default=3,
                    help="stop after this many validations without improvement (0: never)")
    ap.add_argument("--min-share", type=float, default=0.15,
                    help="minimum share of each epoch's tiles per dataset")
    ap.add_argument("--max-repeat", type=int, default=4,
                    help="max times a small dataset's tiles are repeated to reach --min-share")
    ap.add_argument("--checkpoint", default=PRODUCT_CHECKPOINT)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--datasets", default="mine,ghostvision", help="comma-separated")
    ap.add_argument("--model-id", default=None, help="name recorded in the model label")
    ap.add_argument("--workers", type=int, default=4, help="DataLoader worker processes")
    ap.add_argument("--eval-every", type=int, default=2, help="validate every N epochs")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.backends.cudnn.benchmark = True  # fixed 640x640 input: pick the fastest conv kernels
    torch.set_float32_matmul_precision("high")  # TF32 for the ops autocast leaves in fp32
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    chosen = [d.strip() for d in args.datasets.split(",") if d.strip()]
    unknown = sorted(set(chosen) - set(DATASET_IDS))
    if not chosen or unknown:
        raise SystemExit(f"--datasets must name some of {sorted(DATASET_IDS)}")
    keep = {DATASET_IDS[d] for d in chosen}
    splits = build_splits(data_dir())
    splits["train"] = [s for s in splits["train"] if s.dataset_id in keep]
    for part in ("val", "test"):
        splits[part] = {k: v for k, v in splits[part].items() if k.split("_")[0] in chosen}
    val = {k: subsample(v, args.val_images, rng) for k, v in splits["val"].items()}
    model, processor = load_model(args.checkpoint)
    model.to(device)
    pixel_dir = data_dir() / "cache" / "pixels"
    use_pixels = (pixel_dir / "index.json").exists()  # decoded once: no per-tile decoding
    cache = PixelCache(pixel_dir) if use_pixels else ImageCache(max_images=2048)
    opt = make_optimizer(model, args.lr)
    share = {"min_share": args.min_share, "max_repeat": args.max_repeat}
    # size the LR schedule from the tiles actually available, not from the --max-tiles cap
    n_tiles = len(balanced_tiles(splits["train"], args.tile, neg_ratio=args.neg_ratio,
                                 max_tiles=args.max_tiles, seed=args.seed, **share))
    steps_per_epoch = max(1, n_tiles // args.batch)
    total = steps_per_epoch * args.epochs
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: warmup_cosine(s, total, warmup=min(300, total // 10)))
    log = open(out / "train_log.jsonl", "a", encoding="utf-8")
    best, history, step = -1.0, [], 0
    stopper = EarlyStopper(args.patience) if args.patience > 0 else None
    for epoch in range(args.epochs):
        tiles = balanced_tiles(splits["train"], args.tile, neg_ratio=args.neg_ratio,
                               max_tiles=args.max_tiles, seed=args.seed + epoch, **share)
        ds = TileDataset(splits["train"], tiles, augment=True, seed=args.seed + epoch,
                         cache=PixelCache(pixel_dir) if use_pixels else ImageCache(256))
        loader = DataLoader(ds, batch_size=args.batch, shuffle=True, collate_fn=collate,
                            num_workers=args.workers, pin_memory=device == "cuda",
                            prefetch_factor=4 if args.workers else None,
                            persistent_workers=False, drop_last=True)
        model.train()
        t0, losses = time.time(), []
        for pixels, labels in loader:
            labels = [{k: v.to(device, non_blocking=True) for k, v in lab.items()}
                      for lab in labels]
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                loss = model(pixel_values=pixels.to(device, non_blocking=True), labels=labels).loss
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
        last = epoch == args.epochs - 1
        if (epoch + 1) % args.eval_every and not last:
            history.append({"epoch": epoch, "train_loss": float(np.mean(losses)),
                            "train_tiles": len(tiles), "seconds": time.time() - t0})
            log.write(json.dumps(history[-1]) + "\n")
            log.flush()
            continue
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
        if stopper is not None and stopper.update(score):
            log.write(json.dumps({"early_stop_epoch": epoch, "best_val_mean_ap50": best}) + "\n")
            log.flush()
            break
    from transformers import DFineForObjectDetection

    model = DFineForObjectDetection.from_pretrained(out / "model").to(device)
    test = {k: evaluate(model, processor, v, args.tile, cache, device)
            for k, v in splits["test"].items()}
    config = {**vars(args), "device": device, "net_input": 640, "overlap": 0.25,
              "full_image_pass": True}
    (out / "metrics.json").write_text(json.dumps(
        {"config": config, "best_val_mean_ap50": best, "history": history, "test": test,
         "dropped_unreadable_images": splits["dropped_unreadable"]},
        indent=2, default=float), encoding="utf-8")
    manifest = build_training_manifest(
        sorted(keep), load_register(default_register_path()),
        model_id=args.model_id
        or f"dfine-s-pilot-{'+'.join(chosen)}-tile{args.tile}-seed{args.seed}",
        code_version=_git_commit(), config=config)
    write_manifest(manifest, out / "model",
                   ledger=Ledger(data_dir() / "provenance" / "models.jsonl"))
    print(json.dumps({"tile": args.tile, "best_val_mean_ap50": best,
                      "test": {k: {kk: v[kk] for kk in ("ap50", "ap50_small",
                                                       "recall_at_1_fp_per_image")}
                               for k, v in test.items()}}, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
