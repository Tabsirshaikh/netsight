"""ApertureLab Synthetic Side-Scan Sonar Dataset v1.0 (EdgeTech 4125i, simulated).

250 simulated starboard swaths, square 2.3 cm pixels, seven classes: ghost_net, rope_line,
container, wreck, tire, pipe, natural (rock). Official split per scene (manifest.csv:
200 train / 25 val / 25 test). Licence ALSD-1.0: commercial use with attribution, except the
named excluded parties (see licences/datasets.yaml). Simulated data: no electronic noise.

    python -m netsight.datasets.aperturelab   # pack greyscale PNGs + labels into one zip
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

from netsight.datasets.detection import DetectionSample, _xywh_to_xyxy

ZIP_NAME = "aperturelab_grey.zip"
DATASET_ID = "aperturelab_sss"


def pack(raw_dir: Path) -> Path:
    """Greyscale copies of the PNGs plus coco_all.json and manifest.csv in one zip."""
    from PIL import Image

    out = raw_dir / ZIP_NAME
    coco = json.loads((raw_dir / "coco_all.json").read_text("utf-8"))
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as z:
        z.write(raw_dir / "coco_all.json", "coco_all.json")
        z.write(raw_dir / "manifest.csv", "manifest.csv")
        for im in coco["images"]:
            src = raw_dir / im["file_name"]
            buf = io.BytesIO()
            Image.open(src).convert("L").save(buf, "PNG")
            z.writestr(im["file_name"], buf.getvalue())
    return out


def read_aperturelab_zip(zip_path: str | Path) -> list[DetectionSample]:
    zip_path = Path(zip_path)
    with zipfile.ZipFile(zip_path) as z:
        coco = json.loads(z.read("coco_all.json"))
        split_of = {
            row["scene"]: row["split"]
            for row in csv.DictReader(io.StringIO(z.read("manifest.csv").decode("utf-8")))
        }
    cats = {c["id"]: c["name"] for c in coco["categories"]}
    per_image: dict[int, list] = {}
    for a in coco["annotations"]:
        per_image.setdefault(a["image_id"], []).append(a)
    samples = []
    for im in coco["images"]:
        anns = per_image.get(im["id"], [])
        scene = im.get("scene") or Path(im["file_name"]).stem.split("_drc")[0]
        samples.append(
            DetectionSample(
                dataset_id=DATASET_ID,
                zip_path=str(zip_path),
                member=im["file_name"],
                width=int(im["width"]),
                height=int(im["height"]),
                boxes=_xywh_to_xyxy([a["bbox"] for a in anns]),
                labels=[cats[a["category_id"]] for a in anns],
                group=scene,
                source_split=split_of.get(scene, "train"),
                extra={"pixel_size_m": im.get("pixel_size_m"), "synthetic": True},
            )
        )
    return samples


def main() -> int:
    from netsight.config import data_dir

    print(pack(data_dir() / "raw" / "aperturelab_sss"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
