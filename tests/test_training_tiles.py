import numpy as np
import pytest

from netsight.datasets.detection import DetectionSample
from netsight.detect.tiling import Tile
from netsight.detect.training_tiles import build_train_tiles, keep_boxes


def _sample(w, h, boxes, i=0):
    arr = np.asarray(boxes, float).reshape(-1, 4)
    return DetectionSample("d", "z.zip", f"img{i}.jpg", w, h, arr, ["o"] * len(boxes), "g")


TILE = Tile(0, 0, 100, 100, 0)


def test_keep_boxes_rules():
    boxes = np.array([
        [10, 10, 30, 30],     # inside: kept
        [90, 10, 110, 30],    # half inside (visible 0.5): kept
        [95, 10, 115, 30],    # quarter inside, small visible part: cut, not kept
        [60, 0, 160, 80],     # 40% inside but visible part 40x80 px >= 32: kept
        [200, 200, 210, 210], # outside: ignored
    ])
    local, kept, cut = keep_boxes(boxes, TILE)
    assert kept.tolist() == [0, 1, 3]
    assert cut.tolist() == [2]
    np.testing.assert_allclose(local[1], [90, 10, 100, 30])


def test_positive_tiles_with_a_cut_object_are_excluded():
    rng = np.random.default_rng(0)
    # 200x100 image, tiles 100 wide with 0 overlap -> tiles [0,100) and [100,200)
    s = _sample(200, 100, [[20, 20, 40, 40], [95, 50, 115, 70]])
    tiles = build_train_tiles([s], 100, overlap=0.0, neg_ratio=0.0, rng=rng)
    # tile 0 contains box 0 but cuts box 1 (5 px of 20 inside): excluded
    # tile 1 contains 75% of box 1: kept as a positive
    assert [t.tile.x0 for t in tiles] == [100]
    np.testing.assert_allclose(tiles[0].boxes, [[0, 50, 15, 70]])


def test_negative_sampling_ratio_and_determinism():
    samples = [_sample(400, 100, [[10, 10, 30, 30]], i) for i in range(5)]
    a = build_train_tiles(samples, 100, overlap=0.0, neg_ratio=1.0, rng=np.random.default_rng(1))
    b = build_train_tiles(samples, 100, overlap=0.0, neg_ratio=1.0, rng=np.random.default_rng(1))
    pos = [t for t in a if len(t.boxes)]
    neg = [t for t in a if not len(t.boxes)]
    assert len(pos) == 5 and len(neg) == 5  # 15 empty tiles available, ratio 1 -> 5
    assert [(t.sample_index, t.tile.x0) for t in a] == [(t.sample_index, t.tile.x0) for t in b]


def test_images_without_objects_give_negatives_only():
    tiles = build_train_tiles([_sample(100, 100, [])], 100, neg_ratio=1.0,
                              rng=np.random.default_rng(0), min_negatives=1)
    assert len(tiles) == 1 and tiles[0].boxes.shape == (0, 4)


def test_max_tiles_keeps_the_positive_share():
    samples = [_sample(400, 100, [[10, 10, 30, 30]], i) for i in range(20)]
    tiles = build_train_tiles(samples, 100, overlap=0.0, neg_ratio=1.0, max_tiles=10,
                              rng=np.random.default_rng(2))
    assert len(tiles) == 10
    assert sum(1 for t in tiles if len(t.boxes)) == 5


def test_small_image_gives_one_tile_covering_it():
    s = _sample(60, 40, [[10, 10, 20, 20]])
    (t,) = build_train_tiles([s], 100, neg_ratio=0.0, rng=np.random.default_rng(0))
    assert (t.tile.x1, t.tile.y1) == (60, 40)


def test_bad_arguments():
    with pytest.raises(ValueError):
        build_train_tiles([], 0, rng=np.random.default_rng(0))
    with pytest.raises(ValueError):
        build_train_tiles([], 100, neg_ratio=-1, rng=np.random.default_rng(0))


def _ds(dataset_id, n, w=400):
    return [DetectionSample(dataset_id, "z.zip", f"{dataset_id}{i}.jpg", w, 100,
                            np.array([[10.0, 10.0, 40.0, 40.0]]), ["o"], "g")
            for i in range(n)]


def test_balanced_tiles_gives_small_datasets_a_minimum_share():
    from netsight.detect.training_tiles import balanced_tiles

    samples = _ds("big", 200) + _ds("small", 10)
    tiles = balanced_tiles(samples, 100, neg_ratio=0.0, max_tiles=400, seed=0, min_share=0.15,
                           max_repeat=4)
    by = {"big": 0, "small": 0}
    for t in tiles:
        by[samples[t.sample_index].dataset_id] += 1
    assert by["big"] == 200  # capped at max_tiles // 2 datasets
    # small has 10 positive tiles; 15% share needs ~36 -> repeated, capped at 4x = 40
    assert 30 <= by["small"] <= 40
    assert by["small"] / len(tiles) >= 0.14


def test_balanced_tiles_repeat_is_capped():
    from netsight.detect.training_tiles import balanced_tiles

    samples = _ds("big", 400) + _ds("tiny", 2)
    tiles = balanced_tiles(samples, 100, neg_ratio=0.0, max_tiles=800, seed=0, min_share=0.5,
                           max_repeat=3)
    assert sum(1 for t in tiles if samples[t.sample_index].dataset_id == "tiny") == 6


def test_early_stopper_waits_for_patience():
    from netsight.detect.training_tiles import EarlyStopper

    stop = EarlyStopper(patience=2)
    assert stop.update(0.30) is False and stop.best == 0.30
    assert stop.update(0.35) is False and stop.best == 0.35  # improvement resets the count
    assert stop.update(0.34) is False                        # 1 without improvement
    assert stop.update(0.33) is True                         # 2 -> stop
