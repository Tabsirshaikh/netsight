"""LLM-assisted label review: a vision model judges numbered candidate boxes, blind to their source.

Candidates = the existing labels plus confident detector proposals that no label covers. The
model sees (1) the whole image with numbered boxes and (2) zoomed crops of each candidate, and
returns per candidate: object / not_object / unsure, whether the box includes the acoustic
shadow, an object-only box, and any missed objects. It is never told which boxes are labels.

    python -m netsight.datasets.llm_review --set mine --images 10 --out runs/llm_review_mine
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import time
import urllib.request
from pathlib import Path

import numpy as np

MODEL = os.environ.get("REVIEW_MODEL", "cx/gpt-6-astra-medium")
URL = os.environ.get("OMNIROUTE_BASE_URL", "http://127.0.0.1:20128/v1") + "/chat/completions"

TARGETS = {
    "mine": "mine-like objects: compact man-made objects (cylinders, cones, spheres, boxes, "
    "drums) lying on the seabed",
    "ghostvision": "crab pots / traps: small compact man-made boxes or cages on the seabed",
    "ghostvision_shift": "crab pots / traps: small compact man-made boxes or cages on the seabed",
}

PROMPT = """You are an expert side-scan sonar analyst reviewing object labels.
Image 1 is a side-scan sonar image ({w} x {h} pixels, coordinates in that pixel frame) with
numbered yellow candidate boxes. Image 2 shows a zoomed crop of each candidate with its number.
Objects of interest: {target}.
In side-scan, a real object usually shows a bright highlight (the side facing the sonar) and a
dark acoustic shadow behind it on the far-range side. Seabed texture, rocks, sand ripples, fish,
water-column noise, nadir and image artefacts are NOT objects of interest.

For EVERY numbered candidate decide:
- verdict: "object" (an object of interest), "not_object", or "unsure"
- includes_shadow: true if the box covers a dark shadow region beyond the object itself
- object_box: [x0, y0, x1, y1] tightly around the object itself, shadow EXCLUDED, in the
  pixel frame of image 1 (give it for verdict "object" or "unsure"; null otherwise)
Then list objects of interest that NO candidate covers, with their object_box.

Answer with JSON only:
{{"candidates": [{{"id": 1, "verdict": "...", "includes_shadow": true, "object_box": [..]}}],
  "missed": [{{"object_box": [..], "note": "..."}}]}}"""


def _png(img) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def render(image: np.ndarray, boxes: np.ndarray):
    """Overview with numbered boxes (upscaled to >= 900 px) and a numbered crop mosaic."""
    from PIL import Image, ImageDraw

    h, w = image.shape
    scale = max(1.0, 900 / max(h, w))
    over = Image.fromarray(image).convert("RGB").resize((int(w * scale), int(h * scale)))
    d = ImageDraw.Draw(over)
    for k, b in enumerate(boxes, 1):
        x0, y0, x1, y1 = (v * scale for v in b)
        d.rectangle([x0, y0, x1, y1], outline=(255, 230, 0), width=2)
        d.text((x0, max(y0 - 11, 0)), str(k), fill=(255, 230, 0))
    tiles = []
    for k, b in enumerate(boxes, 1):
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        half = max(b[2] - b[0], b[3] - b[1], 24) * 1.5
        x0, y0 = int(max(cx - half, 0)), int(max(cy - half, 0))
        x1, y1 = int(min(cx + half, w)), int(min(cy + half, h))
        crop = Image.fromarray(image[y0:y1, x0:x1]).convert("RGB").resize((180, 180))
        cd = ImageDraw.Draw(crop)
        sx, sy = 180 / max(x1 - x0, 1), 180 / max(y1 - y0, 1)
        cd.rectangle(
            [(b[0] - x0) * sx, (b[1] - y0) * sy, (b[2] - x0) * sx, (b[3] - y0) * sy],
            outline=(255, 230, 0),
            width=1,
        )
        cd.rectangle([0, 0, 26, 14], fill=(0, 0, 0))
        cd.text((3, 1), str(k), fill=(255, 230, 0))
        tiles.append(crop)
    cols = 6
    rows = max(1, (len(tiles) + cols - 1) // cols)
    mosaic = Image.new("RGB", (cols * 180, rows * 180))
    for k, t in enumerate(tiles):
        mosaic.paste(t, ((k % cols) * 180, (k // cols) * 180))
    return over, mosaic


def ask(over, mosaic, w: int, h: int, target: str) -> dict:
    body = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT.format(w=w, h=h, target=target)},
                    {"type": "image_url", "image_url": {"url": _png(over)}},
                    {"type": "image_url", "image_url": {"url": _png(mosaic)}},
                ],
            }
        ],
    }
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                URL,
                json.dumps(body).encode(),
                {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + os.environ["OMNIROUTE_API_KEY"],
                },
            )
            resp = json.load(urllib.request.urlopen(req, timeout=900))
            txt = resp["choices"][0]["message"]["content"]
            m = re.search(r"\{.*\}", txt, re.S)
            out = json.loads(m.group(0)) if m else {"error": txt[:500]}
            out["_usage"] = resp.get("usage")
            return out
        except Exception as exc:  # noqa: BLE001 - retry any transport/parse failure
            err = str(exc)
            time.sleep(10 * (attempt + 1))
    return {"error": err}


def candidates(boxes, scores, gt, min_score: float = 0.3, max_n: int = 24):
    """Labels first, then confident proposals not covered by a label (NMS among themselves)."""
    from netsight.detect.error_breakdown import _iou

    gt = np.asarray(gt, float).reshape(-1, 4)
    b = np.asarray(boxes, float).reshape(-1, 4)
    s = np.asarray(scores, float).reshape(-1)
    keep = []
    for i in np.argsort(-s):
        if s[i] < min_score:
            break
        if len(gt) and _iou(b[i : i + 1], gt).max() >= 0.3:
            continue
        if keep and _iou(b[i : i + 1], b[keep]).max() >= 0.3:
            continue
        keep.append(int(i))
    cand = np.concatenate([gt, b[keep]])[:max_n]
    source = (["label"] * len(gt) + ["model"] * len(keep))[:max_n]
    return cand, source


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir
    from netsight.demo.run_survey import _load_set
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache

    p = argparse.ArgumentParser()
    p.add_argument("--set", default=None, help="test set name")
    p.add_argument(
        "--train-dataset", default=None, help="dataset_id: review its training images instead"
    )
    p.add_argument("--images", type=int, default=10)
    p.add_argument("--dump", default="runs/calib_v0.4")
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--reverse", action="store_true", help="extra worker: start from the end")
    p.add_argument("--indices", default=None, help="JSON list of image indices to review")
    p.add_argument("--worker", default="", help="suffix of this worker's review file")
    a = p.parse_args(argv)
    root = data_dir()
    splits = build_splits(root)
    px = PixelCache(root / "cache" / "pixels")
    if a.train_dataset:
        samples = [x for x in splits["train"] if x.dataset_id == a.train_dataset]
        preds, gts = _load_set(root / a.dump / f"train_{a.train_dataset}.npz")
        a.set = {"mine_detection_sss": "mine", "ghostvision_crabpot": "ghostvision"}.get(
            a.train_dataset, a.train_dataset
        )
    else:
        samples = splits["test"][a.set]
        preds, gts = _load_set(root / a.dump / f"test_{a.set}.npz")
    out = root / a.out
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    with_labels = [i for i, g in enumerate(gts) if len(np.asarray(g).reshape(-1, 4))]
    if a.images <= 0:  # every image with at least one candidate (labels or confident proposals)
        with_labels = [i for i in range(len(gts)) if len(candidates(*preds[i], gts[i])[0])]
        a.images = len(with_labels)
    done = set()
    if (out / "review.jsonl").exists():  # resume: skip images already reviewed
        done = {json.loads(x)["index"] for x in (out / "review.jsonl").open(encoding="utf-8")}
    pick = sorted(
        int(i) for i in rng.choice(with_labels, min(a.images, len(with_labels)), replace=False)
    )
    results = []
    if a.indices:
        pick = sorted(int(i) for i in json.loads(Path(a.indices).read_text("utf-8")))
    if a.reverse:
        pick = pick[::-1]
    for i in pick:
        done |= {
            json.loads(x)["index"]
            for f in out.glob("review*.jsonl")
            for x in f.open(encoding="utf-8")
        }
        if i in done:
            continue
        img = np.asarray(px.get(samples[i]), np.uint8)
        cand, source = candidates(*preds[i], gts[i])
        over, mosaic = render(img, cand)
        over.save(out / f"{i:04d}_overview.png")
        mosaic.save(out / f"{i:04d}_crops.png")
        ans = ask(over, mosaic, img.shape[1], img.shape[0], TARGETS[a.set])
        rec = {
            "index": i,
            "member": samples[i].member,
            "group": samples[i].group,
            "candidates": cand.round(1).tolist(),
            "source": source,
            "answer": ans,
        }
        results.append(rec)
        with (out / f"review{a.worker}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(i, len(cand), "candidates", "error" if "error" in ans else "ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
