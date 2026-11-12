"""Generate object-only prelabels for human review.

Boxes use continuous pixel-edge coordinates: ``(x0, y0, x1, y1)``.
A mask pixel at row y, column x occupies [x, x+1] by [y, y+1].
Acoustic shadows must not be included in detector or refiner object predictions;
geometry alone cannot distinguish an object from its shadow.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np

type Detector = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]
type Refiner = Callable[[np.ndarray, np.ndarray], np.ndarray]


@dataclass(frozen=True)
class Proposal:
    """One object-only box, with its confidence and refinement provenance."""

    image: str
    box: tuple[float, float, float, float]
    score: float
    refined: bool
    source: str

    def __post_init__(self) -> None:
        _filename(self.image)
        box = _box(self.box)
        if not np.isfinite(self.score) or not 0 <= self.score <= 1:
            raise ValueError("score must be finite and between 0 and 1")
        if not isinstance(self.refined, bool):
            raise ValueError("refined must be boolean")
        expected = "detector+refiner" if self.refined else "detector"
        if self.source != expected:
            raise ValueError(f"source must be {expected!r} for refined={self.refined}")
        object.__setattr__(self, "box", tuple(float(value) for value in box))


def _filename(name: str) -> None:
    if not isinstance(name, str) or not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError("image name must be a nonempty file name, without directories")


def _box(values: object) -> np.ndarray:
    try:
        box = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("box must contain four finite numeric coordinates") from exc
    if box.shape != (4,) or not np.isfinite(box).all():
        raise ValueError("box must contain four finite numeric coordinates")
    if box[0] < 0 or box[1] < 0 or box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("box must have nonnegative coordinates and positive width and height")
    return box


def _image(image: np.ndarray) -> None:
    if (
        not isinstance(image, np.ndarray)
        or image.dtype != np.uint8
        or image.ndim != 2
        or 0 in image.shape
    ):
        raise ValueError("image must be a nonempty greyscale uint8 array of shape (H, W)")


def propose(
    image: np.ndarray,
    name: str,
    detector: Detector,
    *,
    min_score: float = 0.3,
    refiner: Refiner | None = None,
    max_grow: float = 0.25,
) -> list[Proposal]:
    """Filter detections and optionally tighten them to object masks.

    Growth is a fraction of the original width/height on each respective side.
    The clipped window includes pixels intersecting its continuous bounds (floor
    of the lower edges, ceiling of the upper edges). Mask boxes use exclusive
    upper edges. Empty masks and masks below 10% of original area fall back.
    Detector boxes must already lie inside the image.
    """
    _image(image)
    _filename(name)
    if not np.isfinite(min_score) or not 0 <= min_score <= 1:
        raise ValueError("min_score must be finite and between 0 and 1")
    if not np.isfinite(max_grow) or max_grow < 0:
        raise ValueError("max_grow must be finite and nonnegative")

    try:
        raw_boxes, raw_scores = detector(image)
        boxes = np.asarray(raw_boxes, dtype=float)
        scores = np.asarray(raw_scores, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("detector must return numeric boxes (N, 4) and scores (N,)") from exc
    if boxes.ndim != 2 or boxes.shape[1] != 4 or scores.shape != (len(boxes),):
        raise ValueError("detector must return boxes of shape (N, 4) and scores of shape (N,)")
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("detector scores must be finite and between 0 and 1")

    height, width = image.shape
    results = []
    for coordinates, score in zip(boxes, scores, strict=True):
        box = _box(coordinates)
        if box[2] > width or box[3] > height:
            raise ValueError("detector boxes must lie inside the image")
        if score < min_score:
            continue
        chosen = box
        refined = False
        if refiner is not None:
            mask = np.asarray(refiner(image, box.copy()))
            if mask.shape != image.shape or mask.dtype != np.bool_:
                raise ValueError("refiner must return a boolean mask with the image shape")
            dx = (box[2] - box[0]) * max_grow
            dy = (box[3] - box[1]) * max_grow
            left = int(np.floor(max(0, box[0] - dx)))
            top = int(np.floor(max(0, box[1] - dy)))
            right = int(np.ceil(min(width, box[2] + dx)))
            bottom = int(np.ceil(min(height, box[3] + dy)))
            rows, cols = np.nonzero(mask[top:bottom, left:right])
            if rows.size:
                candidate = np.array(
                    [
                        left + cols.min(),
                        top + rows.min(),
                        left + cols.max() + 1,
                        top + rows.max() + 1,
                    ],
                    dtype=float,
                )
                area = (candidate[2] - candidate[0]) * (candidate[3] - candidate[1])
                original_area = (box[2] - box[0]) * (box[3] - box[1])
                if area >= 0.1 * original_area:
                    chosen = candidate
                    refined = True
        results.append(
            Proposal(
                image=name,
                box=tuple(float(value) for value in chosen),
                score=float(score),
                refined=refined,
                source="detector+refiner" if refined else "detector",
            )
        )
    return results


def _records(
    proposals_by_image: Mapping[str, list[Proposal]],
    sizes: Mapping[str, tuple[int, int]],
) -> list[tuple[str, int, int, list[Proposal]]]:
    records = []
    for name in sorted(proposals_by_image):
        _filename(name)
        if name not in sizes:
            raise ValueError(f"missing image size for {name!r}")
        size = sizes[name]
        if len(size) != 2 or any(
            isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v <= 0 for v in size
        ):
            raise ValueError(f"size for {name!r} must be positive integer (width, height)")
        width, height = map(int, size)
        proposals = proposals_by_image[name]
        for proposal in proposals:
            if not isinstance(proposal, Proposal) or proposal.image != name:
                raise ValueError(f"proposal image must match mapping key {name!r}")
            if proposal.box[2] > width or proposal.box[3] > height:
                raise ValueError(f"proposal box lies outside image {name!r}")
        records.append((name, width, height, proposals))
    return records


def _label(label: str) -> None:
    if not isinstance(label, str) or not label.strip():
        raise ValueError("label must be a nonempty string")


def write_cvat_xml(
    path: str | Path,
    proposals_by_image: Mapping[str, list[Proposal]],
    sizes: Mapping[str, tuple[int, int]],
    *,
    label: str = "object",
) -> Path:
    """Write CVAT for images 1.1 XML, including images with no proposals."""
    _label(label)
    records = _records(proposals_by_image, sizes)
    root = ET.Element("annotations")
    ET.SubElement(root, "version").text = "1.1"
    task = ET.SubElement(ET.SubElement(root, "meta"), "task")
    labels = ET.SubElement(task, "labels")
    ET.SubElement(ET.SubElement(labels, "label"), "name").text = label
    for index, (name, width, height, proposals) in enumerate(records):
        element = ET.SubElement(
            root, "image", id=str(index), name=name, width=str(width), height=str(height)
        )
        for proposal in proposals:
            x0, y0, x1, y1 = proposal.box
            box = ET.SubElement(
                element,
                "box",
                label=label,
                source="auto",
                occluded="0",
                xtl=f"{x0:.2f}",
                ytl=f"{y0:.2f}",
                xbr=f"{x1:.2f}",
                ybr=f"{y1:.2f}",
                z_order="0",
            )
            ET.SubElement(box, "attribute", name="score").text = f"{proposal.score:.2f}"
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root)
    ET.ElementTree(root).write(destination, encoding="utf-8", xml_declaration=True)
    return destination


def _output_paths(
    directory: str | Path,
    records: list[tuple[str, int, int, list[Proposal]]],
    suffix: str,
) -> list[Path]:
    paths = [Path(directory) / (Path(name).stem + suffix) for name, _, _, _ in records]
    if len(set(paths)) != len(paths):
        raise ValueError("image names have duplicate stems; output files would collide")
    Path(directory).mkdir(parents=True, exist_ok=True)
    return paths


def write_labelme_json(
    directory: str | Path,
    proposals_by_image: Mapping[str, list[Proposal]],
    sizes: Mapping[str, tuple[int, int]],
    *,
    label: str = "object",
) -> list[Path]:
    """Write LabelMe/X-AnyLabeling rectangle files in sorted image order."""
    _label(label)
    records = _records(proposals_by_image, sizes)
    paths = _output_paths(directory, records, ".json")
    for path, (name, width, height, proposals) in zip(paths, records, strict=True):
        data = {
            "version": "5.4.1",
            "flags": {},
            "shapes": [
                {
                    "label": label,
                    "points": [list(p.box[:2]), list(p.box[2:])],
                    "group_id": None,
                    "description": f"score={p.score:.2f}",
                    "shape_type": "rectangle",
                    "flags": {},
                }
                for p in proposals
            ],
            "imagePath": name,
            "imageData": None,
            "imageHeight": height,
            "imageWidth": width,
        }
        path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return paths


def write_yolo(
    directory: str | Path,
    proposals_by_image: Mapping[str, list[Proposal]],
    sizes: Mapping[str, tuple[int, int]],
    *,
    class_id: int = 0,
) -> list[Path]:
    """Write normalized center/size YOLO boxes, including empty annotation files."""
    if isinstance(class_id, bool) or not isinstance(class_id, int) or class_id < 0:
        raise ValueError("class_id must be a nonnegative integer")
    records = _records(proposals_by_image, sizes)
    paths = _output_paths(directory, records, ".txt")
    for path, (_, width, height, proposals) in zip(paths, records, strict=True):
        lines = []
        for proposal in proposals:
            x0, y0, x1, y1 = proposal.box
            cx, cy = (x0 + x1) / (2 * width), (y0 + y1) / (2 * height)
            w, h = (x1 - x0) / width, (y1 - y0) / height
            lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
        path.write_text("".join(lines), encoding="utf-8")
    return paths


def read_cvat_xml(path: str | Path) -> dict[str, np.ndarray]:
    """Read reviewed CVAT boxes; unannotated images have shape (0, 4)."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError("invalid CVAT XML") from exc
    if root.tag != "annotations":
        raise ValueError("CVAT XML root must be annotations")
    results = {}
    for image in root.findall("image"):
        name = image.get("name", "")
        _filename(name)
        if name in results:
            raise ValueError(f"duplicate CVAT image name {name!r}")
        boxes = []
        for element in image.findall("box"):
            try:
                coordinates = [float(element.attrib[key]) for key in ("xtl", "ytl", "xbr", "ybr")]
            except (KeyError, ValueError) as exc:
                raise ValueError(f"invalid box coordinates for {name!r}") from exc
            boxes.append(_box(coordinates))
        results[name] = np.asarray(boxes, dtype=float).reshape(-1, 4)
    return results


def hf_sam_refiner(model_id: str = "facebook/sam-vit-base", device: str = "cpu") -> Refiner:
    """Load optional Apache-2.0 SAM weights and return a box-prompt refiner."""
    try:
        import torch
        from transformers import SamModel, SamProcessor
    except ImportError as exc:
        raise RuntimeError(
            "SAM refinement requires torch and transformers with SAM support"
        ) from exc

    processor = SamProcessor.from_pretrained(model_id)
    model = SamModel.from_pretrained(model_id).to(device).eval()

    def refine(image: np.ndarray, box: np.ndarray) -> np.ndarray:
        _image(image)
        prompt = _box(box)
        rgb = np.repeat(image[:, :, None], 3, axis=2)
        inputs = processor(images=rgb, input_boxes=[[prompt.tolist()]], return_tensors="pt").to(
            device
        )
        with torch.inference_mode():
            outputs = model(**inputs)
        masks = processor.image_processor.post_process_masks(
            outputs.pred_masks.cpu(),
            inputs["original_sizes"].cpu(),
            inputs["reshaped_input_sizes"].cpu(),
        )[0]
        best = int(outputs.iou_scores[0, 0].argmax().item())
        return masks[0, best].numpy().astype(bool)

    return refine


def main(argv: Sequence[str] | None = None) -> int:
    """Run D-FINE prelabelling with optional SAM refinement."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images_dir", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--refine", action="store_true")
    parser.add_argument("--min-score", type=float, default=0.3)
    args = parser.parse_args(argv)
    if not args.images_dir.is_dir():
        raise ValueError("IMAGES_DIR must be an existing directory")
    if not np.isfinite(args.min_score) or not 0 <= args.min_score <= 1:
        raise ValueError("min-score must be between 0 and 1")
    try:
        import torch
        from PIL import Image
        from transformers import AutoImageProcessor, DFineForObjectDetection

        from netsight.detect.tta import predict_image_tta
    except ImportError as exc:
        raise RuntimeError(
            "CLI requires Pillow, torch, transformers and netsight.detect.tta"
        ) from exc

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DFineForObjectDetection.from_pretrained(str(args.model)).to(device).eval()
    processor = AutoImageProcessor.from_pretrained(str(args.model))

    def detector(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        with torch.inference_mode():
            return predict_image_tta(
                model, processor, image, tile_px=640, device=device, views="none"
            )

    refiner = hf_sam_refiner(device=device) if args.refine else None
    proposals_by_image = {}
    sizes = {}
    extensions = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    for path in sorted(args.images_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        with Image.open(path) as source:
            image = np.array(source.convert("L"), dtype=np.uint8)
        height, width = image.shape
        sizes[path.name] = (width, height)
        proposals_by_image[path.name] = propose(
            image, path.name, detector, min_score=args.min_score, refiner=refiner
        )
    write_cvat_xml(args.out_dir / "cvat.xml", proposals_by_image, sizes)
    write_labelme_json(args.out_dir / "labelme", proposals_by_image, sizes)
    write_yolo(args.out_dir / "yolo", proposals_by_image, sizes)
    (args.out_dir / "README.txt").write_text(
        "Review every proposal: accept, adjust or reject.\n"
        "BOX CONVENTION: object only, acoustic shadow excluded.\n"
        "These are automatic suggestions, not reviewed ground truth.\n"
        "LabelMe imagePath is the original file name; copy or link the source images "
        "beside the JSON files before opening them.\n"
        "YOLO class 0 is object. Coordinates are normalized center x/y and width/height.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
