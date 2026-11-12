"""Labelled detection datasets converted to one sample format.

Boxes are always in ORIGINAL image pixels as [x0, y0, x1, y1]; tiling happens later in code, so
a tile-size change never needs relabelling. Every sample carries a `group` (survey year,
recording) so train/test splits keep whole groups apart: frames from one recording on both
sides of a split inflate test scores.
"""

from __future__ import annotations

import io
import json
import re
import struct
import zipfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import numpy as np

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".pbm", ".pgm")
_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


@dataclass
class DetectionSample:
    dataset_id: str
    zip_path: str
    member: str
    width: int
    height: int
    boxes: np.ndarray  # (n, 4) float, x0 y0 x1 y1 in original pixels
    labels: list[str]
    group: str
    source_split: str | None = None
    extra: dict = field(default_factory=dict)


def _netpbm_size(data: bytes) -> tuple[int, int]:
    """Width and height from a PBM/PGM/PPM header (magic, width, height; '#' comments)."""
    tokens: list[bytes] = []
    for line in data[:512].split(b"\n"):
        tokens += line.split(b"#", 1)[0].split()
        if len(tokens) >= 3:
            return int(tokens[1]), int(tokens[2])
    raise ValueError("truncated netpbm header")


def image_size(data: bytes) -> tuple[int, int]:
    """(width, height) from a JPEG, PNG or netpbm header without decoding the image."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:1] == b"P" and data[1:2] in b"123456" and len(data) > 2:
        return _netpbm_size(data)
    if data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG or PNG image")
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in _SOF:
            h, w = struct.unpack(">HH", data[i + 5 : i + 9])
            return w, h
        i += 2 + struct.unpack(">H", data[i + 2 : i + 4])[0]
    raise ValueError("JPEG without a frame header")


def load_image(sample: DetectionSample) -> np.ndarray:
    """Greyscale uint8 image (sonar intensity) read from its zip member."""
    from PIL import Image  # optional ML dependency, imported only when images are needed

    with zipfile.ZipFile(sample.zip_path) as z:
        data = z.read(sample.member)
    return np.asarray(Image.open(io.BytesIO(data)).convert("L"), dtype=np.uint8)


def _xywh_to_xyxy(b: Sequence[Sequence[float]]) -> np.ndarray:
    a = np.asarray(b, dtype=float).reshape(-1, 4)
    return np.column_stack([a[:, 0], a[:, 1], a[:, 0] + a[:, 2], a[:, 1] + a[:, 3]])


def read_yolo_zip(
    zip_paths: Iterable[str | Path],
    dataset_id: str,
    class_names: Sequence[str],
    *,
    group_fn: Callable[[str], str] | None = None,
) -> list[DetectionSample]:
    """YOLO txt labels (class xc yc w h, normalised) next to each image; group = zip stem."""
    samples = []
    for zp in zip_paths:
        zp = Path(zp)
        with zipfile.ZipFile(zp) as z:
            members = set(z.namelist())
            for name in sorted(members):
                if not name.lower().endswith(IMAGE_SUFFIXES):
                    continue
                w, h = image_size(z.read(name))
                label_name = str(PurePosixPath(name).with_suffix(".txt"))
                if label_name not in members and "/images/" in f"/{label_name}":
                    # YOLO layout with separate folders: .../images/x.png -> .../labels/x.txt
                    swapped = f"/{label_name}".replace("/images/", "/labels/", 1)[1:]
                    label_name = swapped if swapped in members else label_name
                text = z.read(label_name).decode() if label_name in members else ""
                rows = (
                    np.array(text.split(), dtype=float).reshape(-1, 5)
                    if text.strip()
                    else (np.zeros((0, 5)))
                )
                if len(rows) and (rows[:, 0].max() >= len(class_names) or rows[:, 0].min() < 0):
                    raise ValueError(f"{zp.name}:{label_name}: class index outside {class_names}")
                xc, yc, bw, bh = rows[:, 1] * w, rows[:, 2] * h, rows[:, 3] * w, rows[:, 4] * h
                boxes = np.column_stack([xc - bw / 2, yc - bh / 2, xc + bw / 2, yc + bh / 2])
                stem = PurePosixPath(name).name
                samples.append(
                    DetectionSample(
                        dataset_id=dataset_id,
                        zip_path=str(zp),
                        member=name,
                        width=w,
                        height=h,
                        boxes=boxes.reshape(-1, 4),
                        labels=[class_names[int(c)] for c in rows[:, 0]],
                        group=group_fn(stem) if group_fn else zp.stem,
                    )
                )
    return samples


_GV_GROUP = re.compile(r"^(Rec)0*(\d+)|^([A-Za-z]+)")


def ghostvision_group(file_name: str) -> str:
    """Recording id from a GhostVision file name; 'Rec09' and 'Rec9' are the same recording."""
    m = _GV_GROUP.match(file_name)
    if not m:
        return "unknown"
    return f"Rec{int(m.group(2))}" if m.group(1) else m.group(3)


def read_ghostvision_zip(zip_path: str | Path, *, dataset_id: str = "ghostvision_crabpot"):
    """GhostVision v1.0.0: one metadata.jsonl per split with bbox [x, y, w, h] in pixels."""
    zip_path = Path(zip_path)
    samples = []
    with zipfile.ZipFile(zip_path) as z:
        for meta in sorted(n for n in z.namelist() if n.endswith("/metadata.jsonl")):
            folder = meta.rsplit("/", 1)[0]
            split = folder.rsplit("/", 1)[-1]
            for line in z.read(meta).decode().splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                member = f"{folder}/{row['file_name']}"
                w, h = image_size(z.read(member))
                objs = row.get("objects") or {}
                samples.append(
                    DetectionSample(
                        dataset_id=dataset_id,
                        zip_path=str(zip_path),
                        member=member,
                        width=w,
                        height=h,
                        boxes=_xywh_to_xyxy(objs.get("bbox") or []),
                        labels=list(objs.get("category") or []),
                        group=ghostvision_group(row["file_name"]),
                        source_split=split,
                    )
                )
    return samples


_BAND = re.compile(r"SSS_([A-Z]+)_images")


def subpipe_group(file_name: str, *, window_s: float = 60.0) -> str:
    """SubPipe file names are Unix times of the ping block; consecutive waterfalls overlap, so
    group by time window. The same name exists at both frequencies, and lands in one group."""
    stem = PurePosixPath(file_name).stem
    try:
        return f"t{int(float(stem) // window_s)}"
    except ValueError:
        return "unknown"


def read_coco_zip(
    zip_path: str | Path, dataset_id: str, *, group_fn: Callable[[str], str] | None = None
) -> list[DetectionSample]:
    """Every COCO json in the zip; images are read from the sibling 'Image' folder.

    Image sizes from the json are checked against the real image header.
    """
    zip_path = Path(zip_path)
    samples = []
    with zipfile.ZipFile(zip_path) as z:
        members = set(z.namelist())
        for meta in sorted(n for n in members if n.endswith(".json") and "COCO" in n):
            coco = json.loads(z.read(meta))
            root = meta.rsplit("/", 2)[0]
            band_match = _BAND.search(meta)
            band = band_match.group(1) if band_match else None
            cats = {c["id"]: c["name"] for c in coco.get("categories", [])}
            per_image: dict[int, list] = {}
            for a in coco.get("annotations", []):
                per_image.setdefault(a["image_id"], []).append(a)
            for im in coco.get("images", []):
                member = f"{root}/Image/{im['file_name']}"
                if member not in members:
                    continue
                w, h = image_size(z.read(member))
                if (w, h) != (im["width"], im["height"]):
                    raise ValueError(
                        f"{member}: header {w}x{h} != json {im['width']}x{im['height']}"
                    )
                anns = per_image.get(im["id"], [])
                samples.append(
                    DetectionSample(
                        dataset_id=dataset_id,
                        zip_path=str(zip_path),
                        member=member,
                        width=w,
                        height=h,
                        boxes=_xywh_to_xyxy([a["bbox"] for a in anns]),
                        labels=[cats[a["category_id"]] for a in anns],
                        group=group_fn(im["file_name"]) if group_fn else zip_path.stem,
                        extra={"band": band} if band else {},
                    )
                )
    return samples


def group_split(
    samples: Sequence[DetectionSample], *, test_groups: set[str], val_groups: set[str]
) -> dict[str, list[DetectionSample]]:
    """Split by whole groups; everything not named for test or validation is training."""
    if test_groups & val_groups:
        raise ValueError(f"groups in both test and validation: {sorted(test_groups & val_groups)}")
    out: dict[str, list[DetectionSample]] = {"train": [], "val": [], "test": []}
    for s in samples:
        key = "test" if s.group in test_groups else "val" if s.group in val_groups else "train"
        out[key].append(s)
    return out


def ordered_group_split(
    samples: Sequence[DetectionSample],
    *,
    n_val: int,
    n_test: int,
    gap: int = 1,
    key: Callable[[str], object] | None = None,
) -> dict[str, list[DetectionSample]]:
    """Split groups in order (e.g. time): train | gap | val | gap | test.

    For data where neighbouring groups overlap (consecutive waterfall images), the dropped
    `gap` groups keep near-identical images out of both sides of a split boundary.
    """
    groups = sorted({s.group for s in samples}, key=key)
    if n_val + n_test + 2 * gap >= len(groups):
        raise ValueError(
            f"{len(groups)} groups are too few for {n_val} val + {n_test} test "
            f"+ {2 * gap} gap groups and some training"
        )
    test = set(groups[len(groups) - n_test :])
    val_end = len(groups) - n_test - gap
    val = set(groups[val_end - n_val : val_end])
    train = set(groups[: val_end - n_val - gap])
    return {
        "train": [s for s in samples if s.group in train],
        "val": [s for s in samples if s.group in val],
        "test": [s for s in samples if s.group in test],
    }


_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_DMY = re.compile(r"_(\d{2}[A-Z]{3}\d{2})_")


def aquascan_group(file_name: str) -> str:
    """AquaScan-1K session = capture date in the screenshot or recording file name."""
    m = _DATE.search(file_name)
    if m:
        return m.group(0)
    m = _DMY.search(file_name)
    return m.group(1) if m else "other"


def _zip_key(path: str) -> str:
    st = Path(path).stat()
    return f"{st.st_size}:{int(st.st_mtime)}"


def drop_unreadable(
    samples: Sequence[DetectionSample], cache_path: str | Path
) -> tuple[list[DetectionSample], list[DetectionSample]]:
    """(readable, unreadable) samples. Each image is decoded once; results are cached per zip
    and recomputed when the zip changes. Truncated images are dropped, never 'repaired'
    (a partly decoded image is filled with garbage)."""
    from PIL import Image

    cache_path = Path(cache_path)
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    by_zip: dict[str, list[DetectionSample]] = {}
    for s in samples:
        by_zip.setdefault(s.zip_path, []).append(s)
    changed = False
    bad: set[tuple[str, str]] = set()
    for zp, group in by_zip.items():
        entry = cache.get(zp)
        checked = set(entry["checked"]) if entry and entry["key"] == _zip_key(zp) else set()
        known_bad = set(entry["bad"]) if entry and entry["key"] == _zip_key(zp) else set()
        todo = [s for s in group if s.member not in checked]
        if todo:
            with zipfile.ZipFile(zp) as z:
                for s in todo:
                    try:
                        Image.open(io.BytesIO(z.read(s.member))).convert("L").load()
                    except (OSError, SyntaxError, ValueError, struct.error):
                        known_bad.add(s.member)
                    checked.add(s.member)
            cache[zp] = {"key": _zip_key(zp), "checked": sorted(checked), "bad": sorted(known_bad)}
            changed = True
        bad |= {(zp, m) for m in known_bad}
    if changed:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache), encoding="utf-8")
    kept = [s for s in samples if (s.zip_path, s.member) not in bad]
    dropped = [s for s in samples if (s.zip_path, s.member) in bad]
    return kept, dropped


def read_voc_zip(zip_path: str | Path, dataset_id: str) -> list[DetectionSample]:
    """Pascal VOC (Annotations/*.xml + JPEGImages/), with ImageSets/Main/{split}.txt lists.

    VOC pixel indices are 1-based and inclusive; boxes are converted to 0-based edges.
    """
    import xml.etree.ElementTree as ET  # stdlib; parses only zip members, no entity expansion

    zip_path = Path(zip_path)
    samples = []
    with zipfile.ZipFile(zip_path) as z:
        members = set(z.namelist())
        split_of: dict[str, str] = {}
        for name in members:
            m = re.search(r"ImageSets/Main/([A-Za-z]+)\.txt$", name)
            if m:
                for stem in z.read(name).decode().split():
                    split_of.setdefault(stem, m.group(1))
        for xml_name in sorted(n for n in members if "/Annotations/" in n and n.endswith(".xml")):
            root = ET.fromstring(z.read(xml_name))
            folder = xml_name.split("/Annotations/")[0]
            stem = PurePosixPath(xml_name).stem
            member = f"{folder}/JPEGImages/{root.findtext('filename') or stem + '.jpg'}"
            if member not in members:
                continue
            w, h = image_size(z.read(member))
            boxes, labels = [], []
            for obj in root.iter("object"):
                bb = obj.find("bndbox")
                x0, y0, x1, y1 = (float(bb.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax"))
                boxes.append([x0 - 1, y0 - 1, x1, y1])
                labels.append(obj.findtext("name"))
            samples.append(
                DetectionSample(
                    dataset_id=dataset_id,
                    zip_path=str(zip_path),
                    member=member,
                    width=w,
                    height=h,
                    boxes=np.asarray(boxes, dtype=float).reshape(-1, 4),
                    labels=labels,
                    group=split_of.get(stem, "unsplit"),
                    source_split=split_of.get(stem),
                )
            )
    return samples
