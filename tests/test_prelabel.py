"""Deterministic, hand-computed prelabel geometry and format checks."""

import json
from xml.etree import ElementTree as ET

import numpy as np
import pytest

from netsight.datasets.prelabel import (
    Proposal,
    propose,
    read_cvat_xml,
    write_cvat_xml,
    write_labelme_json,
    write_yolo,
)


def detector(image):
    """Return a 10 by 10 box and a low-confidence second box."""
    return np.array([[5, 5, 15, 15], [0, 0, 2, 2]]), np.array([0.3, 0.2])


def rectangle_refiner(image, box):
    """Return a 6 by 4 object, with pixel-edge bounds (7, 8, 13, 12)."""
    mask = np.zeros(image.shape, dtype=bool)
    mask[8:12, 7:13] = True
    return mask


def test_score_filter_and_refinement():
    image = np.zeros((20, 20), dtype=np.uint8)
    original = propose(image, "a.png", detector)
    assert original == [Proposal("a.png", (5, 5, 15, 15), 0.3, False, "detector")]
    result = propose(image, "a.png", detector, refiner=rectangle_refiner)
    # Area is 6*4=24, above 10% of the original 10*10=100.
    assert result == [Proposal("a.png", (7, 8, 13, 12), 0.3, True, "detector+refiner")]
    assert propose(image, "a.png", detector, min_score=0.31) == []


@pytest.mark.parametrize("tiny", [False, True])
def test_empty_and_tiny_fall_back(tiny):
    image = np.zeros((20, 20), dtype=np.uint8)

    def refine(image, box):
        mask = np.zeros(image.shape, dtype=bool)
        if tiny:
            mask[8, 8] = True  # Area 1 < 10% * 100 = 10.
        return mask

    result = propose(image, "a.png", detector, refiner=refine)
    assert result == [Proposal("a.png", (5, 5, 15, 15), 0.3, False, "detector")]


def test_growth_window_and_image_clipping():
    image = np.zeros((20, 20), dtype=np.uint8)

    def refine(image, box):
        return np.ones(image.shape, dtype=bool)

    # Growth 0.2 * 10 = 2 on each side gives [3, 3, 17, 17].
    result = propose(image, "a.png", detector, refiner=refine, max_grow=0.2)
    assert result[0].box == (3, 3, 17, 17)
    # Growth 2 * 10 = 20 clips all edges to the 20 by 20 image.
    result = propose(image, "a.png", detector, refiner=refine, max_grow=2)
    assert result[0].box == (0, 0, 20, 20)


def test_mask_outside_window_is_ignored():
    image = np.zeros((20, 20), dtype=np.uint8)

    def refine(image, box):
        mask = np.zeros(image.shape, dtype=bool)
        mask[:3, :3] = True
        return mask

    assert not propose(image, "a.png", detector, refiner=refine, max_grow=0)[0].refined


def test_exact_ten_percent_is_accepted():
    image = np.zeros((20, 20), dtype=np.uint8)

    def refine(image, box):
        mask = np.zeros(image.shape, dtype=bool)
        mask[5:7, 5:10] = True  # 2*5=10, exactly 10% of 100.
        return mask

    result = propose(image, "a.png", detector, refiner=refine)
    assert result[0].box == (5, 5, 10, 7)
    assert result[0].refined


@pytest.fixture
def annotations():
    return (
        {"z.png": [], "a&b.png": [Proposal("a&b.png", (2, 4, 10, 12), 0.87, False, "detector")]},
        {"z.png": (20, 40), "a&b.png": (20, 40)},
    )


def test_cvat_round_trip(tmp_path, annotations):
    proposals, sizes = annotations
    path = write_cvat_xml(tmp_path / "cvat.xml", proposals, sizes)
    root = ET.parse(path).getroot()
    assert root.findtext("version") == "1.1"
    assert root.findtext("meta/task/labels/label/name") == "object"
    images = root.findall("image")
    assert [element.get("name") for element in images] == ["a&b.png", "z.png"]
    assert images[0].attrib == {"id": "0", "name": "a&b.png", "width": "20", "height": "40"}
    box = images[0].find("box")
    assert box.attrib == {
        "label": "object",
        "source": "auto",
        "occluded": "0",
        "xtl": "2.00",
        "ytl": "4.00",
        "xbr": "10.00",
        "ybr": "12.00",
        "z_order": "0",
    }
    assert box.find("attribute").attrib == {"name": "score"}
    assert box.findtext("attribute") == "0.87"
    reviewed = read_cvat_xml(path)
    np.testing.assert_array_equal(reviewed["a&b.png"], [[2, 4, 10, 12]])
    assert reviewed["z.png"].shape == (0, 4)


def test_labelme_fields(tmp_path, annotations):
    proposals, sizes = annotations
    paths = write_labelme_json(tmp_path, proposals, sizes)
    assert [p.name for p in paths] == ["a&b.json", "z.json"]
    data = json.loads(paths[0].read_text())
    assert data == {
        "version": "5.4.1",
        "flags": {},
        "shapes": [
            {
                "label": "object",
                "points": [[2, 4], [10, 12]],
                "group_id": None,
                "description": "score=0.87",
                "shape_type": "rectangle",
                "flags": {},
            }
        ],
        "imagePath": "a&b.png",
        "imageData": None,
        "imageHeight": 40,
        "imageWidth": 20,
    }
    assert json.loads(paths[1].read_text())["shapes"] == []


def test_yolo_normalisation(tmp_path, annotations):
    proposals, sizes = annotations
    paths = write_yolo(tmp_path, proposals, sizes, class_id=2)
    # Center (6,8) / (20,40) = (.3,.2); size (8,8)/(20,40) = (.4,.2).
    assert paths[0].read_text() == "2 0.300000 0.200000 0.400000 0.200000\n"
    assert paths[1].read_bytes() == b""


@pytest.mark.parametrize(
    "kwargs",
    [{"min_score": -0.1}, {"min_score": np.nan}, {"max_grow": -1}],
)
def test_invalid_options(kwargs):
    with pytest.raises(ValueError):
        propose(np.zeros((20, 20), dtype=np.uint8), "a.png", detector, **kwargs)


def test_invalid_inputs():
    with pytest.raises(ValueError, match="uint8"):
        propose(np.zeros((20, 20)), "a.png", detector)
    with pytest.raises(ValueError, match="shape"):
        propose(
            np.zeros((20, 20), dtype=np.uint8),
            "a.png",
            lambda image: (np.zeros((2, 3)), np.ones(2)),
        )
    with pytest.raises(ValueError, match="boolean mask"):
        propose(
            np.zeros((20, 20), dtype=np.uint8),
            "a.png",
            detector,
            refiner=lambda image, box: np.zeros(image.shape),
        )
    with pytest.raises(ValueError, match="finite"):
        Proposal("a.png", (0, 0, np.nan, 2), 0.5, False, "detector")


def test_missing_size_and_colliding_outputs(tmp_path, annotations):
    proposals, sizes = annotations
    with pytest.raises(ValueError, match="missing image size"):
        write_yolo(tmp_path, proposals, {})
    with pytest.raises(ValueError, match="duplicate stems"):
        write_labelme_json(
            tmp_path, {"a.png": [], "a.jpg": []}, {"a.png": (10, 10), "a.jpg": (10, 10)}
        )
    with pytest.raises(ValueError, match="nonnegative integer"):
        write_yolo(tmp_path, proposals, sizes, class_id=-1)


def test_empty_detector():
    result = propose(
        np.zeros((2, 2), dtype=np.uint8),
        "empty.png",
        lambda image: (np.empty((0, 4)), np.empty(0)),
    )
    assert result == []
