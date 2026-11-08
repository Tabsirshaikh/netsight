"""AI4Shipwrecks (Univ. Michigan, Deep Blue 10.7302/dmf4-x492) -> YOLO zip for the detector.

Side-scan strips (EdgeTech 2205, ~0.1 m/pixel) with binary shipwreck masks, split by wreck site
(12 training sites, 13 test sites). Each mask becomes boxes: small gaps are closed so one wreck's
fragments become one box, then connected components above a minimum area are boxed.

    python -m netsight.datasets.ai4shipwrecks --src <AI4Shipwrecks folder> --out <zip>
"""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

SITE = re.compile(r"^(.*)_\d+$")


def site_of(stem: str) -> str:
    """Wreck site of an image: the file name without its extension and trailing _NN."""
    m = SITE.match(Path(stem).stem)
    return m.group(1) if m else stem


def mask_to_boxes(mask: np.ndarray, *, close_px: int = 25, min_area_px: int = 300) -> np.ndarray:
    """(n, 4) x0 y0 x1 y1 boxes around the labelled regions of a binary mask."""
    m = np.asarray(mask) > 0
    if not m.any():
        return np.zeros((0, 4))
    if close_px > 0:
        m = ndimage.binary_closing(m, structure=np.ones((close_px, close_px)), iterations=1) | m
    labels, n = ndimage.label(m)
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(labels), start=1):
        if sl is None or np.count_nonzero(labels[sl] == i) < min_area_px:
            continue
        boxes.append([sl[1].start, sl[0].start, sl[1].stop, sl[0].stop])
    return np.asarray(boxes, dtype=float).reshape(-1, 4)


def to_yolo_lines(boxes: np.ndarray, width: int, height: int) -> str:
    rows = []
    for x0, y0, x1, y1 in boxes:
        rows.append(
            f"0 {(x0 + x1) / 2 / width:.6f} {(y0 + y1) / 2 / height:.6f} "
            f"{(x1 - x0) / width:.6f} {(y1 - y0) / height:.6f}"
        )
    return "\n".join(rows) + ("\n" if rows else "")


def convert(src: Path, out_zip: Path) -> dict[str, int]:
    counts = {"images": 0, "boxes": 0, "empty": 0}
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_STORED) as z:
        for split in ("train", "test"):
            for img_path in sorted((src / split / "images").glob("*.png")):
                mask = np.array(Image.open(src / split / "labels" / img_path.name))
                with Image.open(img_path) as im:
                    w, h = im.size
                boxes = mask_to_boxes(mask)
                z.write(img_path, f"{split}/images/{img_path.name}")
                z.writestr(f"{split}/labels/{img_path.stem}.txt", to_yolo_lines(boxes, w, h))
                counts["images"] += 1
                counts["boxes"] += len(boxes)
                counts["empty"] += int(len(boxes) == 0)
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    print(convert(args.src, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
