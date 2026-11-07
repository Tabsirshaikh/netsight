import io
import json
import zipfile

import numpy as np
import pytest

Image = pytest.importorskip("PIL.Image")

from netsight.datasets.detection import (  # noqa: E402 - after the optional PIL import
    group_split,
    image_size,
    load_image,
    read_ghostvision_zip,
    read_yolo_zip,
)


def _jpeg(w, h) -> bytes:
    buf = io.BytesIO()
    Image.new("L", (w, h), 128).save(buf, format="JPEG")
    return buf.getvalue()


def test_image_size_from_header():
    assert image_size(_jpeg(416, 300)) == (416, 300)
    buf = io.BytesIO()
    Image.new("L", (64, 32)).save(buf, format="PNG")
    assert image_size(buf.getvalue()) == (64, 32)


def test_read_yolo_zip_converts_to_pixels(tmp_path):
    z = tmp_path / "2015.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("2015/0001_2015.jpg", _jpeg(1000, 500))
        f.writestr("2015/0001_2015.txt", "0 0.5 0.5 0.1 0.2\n1 0.25 0.25 0.1 0.1\n")
        f.writestr("2015/0002_2015.jpg", _jpeg(1000, 500))
        f.writestr("2015/0002_2015.txt", "")
    samples = read_yolo_zip([z], "mine", ["MILCO", "NOMBO"])
    assert len(samples) == 2
    s = samples[0]
    assert (s.width, s.height, s.group, s.dataset_id) == (1000, 500, "2015", "mine")
    np.testing.assert_allclose(s.boxes, [[450, 200, 550, 300], [200, 100, 300, 150]])
    assert s.labels == ["MILCO", "NOMBO"]
    assert samples[1].boxes.shape == (0, 4) and samples[1].labels == []


def test_read_yolo_zip_rejects_bad_class(tmp_path):
    z = tmp_path / "y.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("a.jpg", _jpeg(10, 10))
        f.writestr("a.txt", "5 0.5 0.5 0.1 0.1\n")
    with pytest.raises(ValueError, match="class"):
        read_yolo_zip([z], "mine", ["MILCO", "NOMBO"])


def test_read_ghostvision_zip(tmp_path):
    z = tmp_path / "gv.zip"
    root = "sss-crab-pot-detection-ds"
    rows = {
        "train": [{"file_name": "Rec7_wcp_ss_port_00035_jpg.rf.x.jpg",
                   "objects": {"bbox": [[10, 20, 30, 40]], "category": ["Crab-Pot"]}}],
        "test": [{"file_name": "Contact_203_sslo_png_jpg.rf.y.jpg",
                  "objects": {"bbox": [], "category": []}}],
    }
    with zipfile.ZipFile(z, "w") as f:
        for split, items in rows.items():
            f.writestr(f"{root}/{split}/metadata.jsonl", "\n".join(json.dumps(r) for r in items))
            for r in items:
                f.writestr(f"{root}/{split}/{r['file_name']}", _jpeg(640, 640))
    samples = read_ghostvision_zip(z)
    by_split = {s.source_split: s for s in samples}
    np.testing.assert_allclose(by_split["train"].boxes, [[10, 20, 40, 60]])
    assert by_split["train"].group == "Rec7" and by_split["train"].labels == ["Crab-Pot"]
    assert by_split["test"].group == "Contact" and by_split["test"].boxes.shape == (0, 4)


def test_load_image_from_zip(tmp_path):
    z = tmp_path / "2015.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("2015/a.jpg", _jpeg(40, 20))
        f.writestr("2015/a.txt", "")
    (s,) = read_yolo_zip([z], "mine", ["MILCO"])
    img = load_image(s)
    assert img.shape == (20, 40) and img.dtype == np.uint8


def test_group_split_keeps_groups_whole_and_is_deterministic(tmp_path):
    z = tmp_path / "g.zip"
    with zipfile.ZipFile(z, "w") as f:
        for g in ("RecA", "RecB", "RecC", "RecD"):
            for i in range(5):
                f.writestr(f"{g}_{i}.jpg", _jpeg(8, 8))
                f.writestr(f"{g}_{i}.txt", "")
    samples = read_yolo_zip([z], "x", ["o"], group_fn=lambda name: name.split("_")[0])
    split = group_split(samples, test_groups={"RecB"}, val_groups={"RecC"})
    assert {s.group for s in split["test"]} == {"RecB"}
    assert {s.group for s in split["val"]} == {"RecC"}
    assert {s.group for s in split["train"]} == {"RecA", "RecD"}
    with pytest.raises(ValueError):
        group_split(samples, test_groups={"RecB"}, val_groups={"RecB"})


def test_read_yolo_zip_with_separate_labels_folder(tmp_path):
    # AquaScan-1K layout: <root>/images/x.png and <root>/labels/x.txt
    z = tmp_path / "aq.zip"
    buf = io.BytesIO()
    Image.new("L", (200, 100)).save(buf, format="PNG")
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("AquaScan-1K/images/a-Screenshot_2025-08-10_23.00.36.png", buf.getvalue())
        f.writestr("AquaScan-1K/labels/a-Screenshot_2025-08-10_23.00.36.txt", "0 0.5 0.5 0.1 0.2\n")
    (s,) = read_yolo_zip([z], "aquascan_1k", ["Human"])
    np.testing.assert_allclose(s.boxes, [[90, 40, 110, 60]])
    assert s.labels == ["Human"]


def _pgm(w, h) -> bytes:
    buf = io.BytesIO()
    Image.new("L", (w, h), 90).save(buf, format="PPM")  # greyscale -> binary PGM ("P5")
    return buf.getvalue()


def test_image_size_netpbm():
    assert image_size(_pgm(250, 50)) == (250, 50)
    assert image_size(b"P5\n# comment\n640 480\n255\n" + bytes(10)) == (640, 480)


def test_read_coco_zip_groups_twin_frequencies_together(tmp_path):
    from netsight.datasets.detection import read_coco_zip, subpipe_group

    z = tmp_path / "sp.zip"
    base = "SubPipeMiniSSS/DATA"
    with zipfile.ZipFile(z, "w") as f:
        for band, w in (("HF", 500), ("LF", 250)):
            coco = {
                "images": [{"id": 1, "file_name": "1693569954.939.pbm", "width": w, "height": 50},
                           {"id": 2, "file_name": "1693570100.000.pbm", "width": w, "height": 50}],
                "annotations": [{"id": 1, "image_id": 1, "category_id": 1,
                                 "bbox": [10, 5, 20, 40]}],
                "categories": [{"id": 1, "name": "Pipeline"}],
            }
            f.writestr(f"{base}/SSS_{band}_images/COCO_Annotation/coco_format.json",
                       json.dumps(coco))
            for im in coco["images"]:
                f.writestr(f"{base}/SSS_{band}_images/Image/{im['file_name']}", _pgm(w, 50))
    samples = read_coco_zip(z, "subpipe_mini2", group_fn=subpipe_group)
    assert len(samples) == 4
    first = [s for s in samples if s.member.endswith("1693569954.939.pbm")]
    assert {s.group for s in first} == {subpipe_group("1693569954.939.pbm")}  # HF + LF twins
    with_box = [s for s in samples if len(s.boxes)]
    np.testing.assert_allclose(with_box[0].boxes, [[10, 5, 30, 45]])
    assert with_box[0].labels == ["Pipeline"] and with_box[0].extra["band"] in ("HF", "LF")
    assert subpipe_group("1693569954.939.pbm") != subpipe_group("1693570100.000.pbm")


def test_ordered_split_leaves_gaps_between_parts(tmp_path):
    from netsight.datasets.detection import ordered_group_split

    z = tmp_path / "o.zip"
    with zipfile.ZipFile(z, "w") as f:
        for g in range(10):
            f.writestr(f"g{g}_0.jpg", _jpeg(8, 8))
            f.writestr(f"g{g}_0.txt", "")
    samples = read_yolo_zip([z], "x", ["o"], group_fn=lambda n: n.split("_")[0])
    split = ordered_group_split(samples, n_val=2, n_test=3, gap=1,
                                key=lambda g: int(g[1:]))
    groups = {k: sorted({s.group for s in v}, key=lambda g: int(g[1:])) for k, v in split.items()}
    assert groups["test"] == ["g7", "g8", "g9"]
    assert groups["val"] == ["g4", "g5"]          # g6 is the gap before test
    assert groups["train"] == ["g0", "g1", "g2"]  # g3 is the gap before val
    with pytest.raises(ValueError):
        ordered_group_split(samples, n_val=5, n_test=5, gap=1)
