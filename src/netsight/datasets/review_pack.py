"""CVAT review pack: images plus original labels, reviewer-proposed objects and unsure boxes.

Open in CVAT (create a task with the images, then Actions -> Upload annotations -> "CVAT for
images 1.1", annotations.xml). Delete wrong boxes, keep right ones; change "proposed" or "unsure"
to "object" when it is a real object. Export with the same format; read back with
``read_decisions``.

    python -m netsight.datasets.review_pack --set mine --reviews relabel_gemini_mine,relabel_sol_mine \
        --out review_packs/mine_test
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

LABELS = {"original": "#33cc33", "proposed": "#3399ff", "unsure": "#ffcc00", "object": "#ff3366"}
README = """NetSight label review pack
==========================
Boxes:
  original  (green)  - label from the published dataset
  proposed  (blue)   - object an AI reviewer says is real but has no label
  unsure    (yellow) - box the AI reviewer could not decide, or an original label it doubted
What to do: for every blue and yellow box decide - real object? Then change its label to
"object" (or keep "original"); otherwise delete it. Add any object nobody marked as "object".
Box rule (team decision): box the OBJECT only, not its acoustic shadow.
A real object usually shows a bright highlight and a dark shadow behind it (far-range side).
Export: CVAT for images 1.1 -> send annotations.xml back.
"""


def build(set_name: str, reviews: list[Path], out: Path, limit: int = 0) -> dict:
    from PIL import Image

    from netsight.config import data_dir
    from netsight.datasets.relabel import corrected, load_reviews
    from netsight.detect.pilot import build_splits
    from netsight.detect.pixel_cache import PixelCache

    root = data_dir()
    samples = build_splits(root)["test"][set_name]
    px = PixelCache(root / "cache" / "pixels")
    rv = load_reviews(reviews)
    (out / "images").mkdir(parents=True, exist_ok=True)
    ann = ET.Element("annotations")
    ET.SubElement(ann, "version").text = "1.1"
    labels = ET.SubElement(ET.SubElement(ET.SubElement(ann, "meta"), "task"), "labels")
    for name, colour in LABELS.items():
        lab = ET.SubElement(labels, "label")
        ET.SubElement(lab, "name").text = name
        ET.SubElement(lab, "color").text = colour
    counts = {k: 0 for k in LABELS}
    idx = sorted(rv)
    if limit:
        idx = idx[:limit]
    for n, i in enumerate(idx):
        s = samples[i]
        orig = np.asarray(s.boxes, float).reshape(-1, 4)
        gen, ignore, _ = corrected(rv[i], orig, "generous")
        proposed = [b for b in gen if not (len(orig) and np.any(np.all(np.isclose(orig, b), 1)))]
        doubted = [b for b in orig if not np.any(np.all(np.isclose(np.asarray(gen), b), 1))]
        unsure = [b for b in ignore if not (len(orig) and np.any(np.all(np.isclose(orig, b), 1)))]
        name = f"{i:04d}_{Path(str(s.member)).stem[:40]}.png"
        img = np.asarray(px.get(s), np.uint8)
        Image.fromarray(img).save(out / "images" / name)
        el = ET.SubElement(
            ann, "image", id=str(n), name=name, width=str(img.shape[1]), height=str(img.shape[0])
        )
        rows = [("original", b) for b in orig if not any(np.allclose(b, d) for d in doubted)]
        rows += [("unsure", b) for b in doubted] + [("proposed", b) for b in proposed]
        rows += [("unsure", b) for b in unsure]
        for label, b in rows:
            ET.SubElement(
                el,
                "box",
                label=label,
                source="auto",
                occluded="0",
                xtl=f"{b[0]:.2f}",
                ytl=f"{b[1]:.2f}",
                xbr=f"{b[2]:.2f}",
                ybr=f"{b[3]:.2f}",
                z_order="0",
            )
            counts[label] += 1
    ET.indent(ann)
    ET.ElementTree(ann).write(out / "annotations.xml", encoding="utf-8", xml_declaration=True)
    (out / "README.txt").write_text(README, "utf-8")
    return {"images": len(idx), **counts}


def read_decisions(xml_path: Path) -> dict[str, np.ndarray]:
    """Boxes kept as real objects ('original' or 'object') per image file name."""
    out = {}
    for im in ET.parse(xml_path).getroot().iter("image"):
        boxes = [
            [float(b.get(k)) for k in ("xtl", "ytl", "xbr", "ybr")]
            for b in im.iter("box")
            if b.get("label") in ("original", "object")
        ]
        out[im.get("name")] = np.asarray(boxes, float).reshape(-1, 4)
    return out


def main(argv: list[str] | None = None) -> int:
    from netsight.config import data_dir

    p = argparse.ArgumentParser()
    p.add_argument("--set", required=True)
    p.add_argument("--reviews", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int, default=0)
    a = p.parse_args(argv)
    R = data_dir()
    res = build(a.set, [R / "runs" / f for f in a.reviews.split(",")], R / a.out, a.limit)
    print(res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
