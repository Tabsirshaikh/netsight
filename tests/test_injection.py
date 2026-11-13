import numpy as np
import pytest

from netsight.trust.injection import (
    background_level,
    free_positions,
    insert_target,
    local_texture,
    parametric_target,
    run_trials,
    template_from_box,
    texture_cuts,
    texture_stratum,
    with_strata,
)


def _seabed(h=200, w=300, level=80, seed=0):
    rng = np.random.default_rng(seed)
    return np.clip(rng.gamma(8, level / 8, size=(h, w)), 0, 255).astype(np.uint8)


def test_background_level_ignores_the_box():
    img = np.full((50, 50), 40, np.uint8)
    img[20:30, 20:30] = 250
    assert background_level(img, (20, 20, 30, 30), ring=5) == 40


def test_block_has_highlight_then_shadow_on_far_side():
    t = parametric_target("block", 10, shadow_px=6, shadow_side="right")
    x0, y0, x1, y1 = (int(v) for v in t.box)
    face = t.relative[y0:y1, x0:x1]
    shadow = t.relative[y0:y1, x1 : x1 + 6]
    assert face.mean() == pytest.approx(2.5)
    assert shadow.mean() == pytest.approx(0.15)
    left = parametric_target("block", 10, shadow_px=6, shadow_side="left")
    lx0 = int(left.box[0])
    assert left.relative[y0:y1, lx0 - 6 : lx0].mean() == pytest.approx(0.15)


def test_flat_patch_has_no_shadow():
    t = parametric_target("flat_patch", 12)
    assert t.relative.min() >= 0.9 - 1e-9


def test_insert_scales_to_local_level_and_returns_object_box():
    rng = np.random.default_rng(1)
    img = np.full((100, 100), 50, np.uint8)
    t = parametric_target("block", 10, shadow_px=0)
    out, box = insert_target(img, t, 30, 40, rng, speckle_looks=0)
    x0, y0, x1, y1 = (int(v) for v in box)
    assert out[y0:y1, x0:x1].mean() == pytest.approx(125, abs=1)  # 2.5 x 50
    assert out[0:20, 0:20].mean() == 50  # untouched elsewhere
    assert img.mean() == 50  # input not modified


def test_transplant_round_trip_keeps_relative_contrast():
    img = np.full((80, 80), 60, np.uint8)
    img[30:40, 30:40] = 180
    t = template_from_box(img, (30, 30, 40, 40))
    dark = np.full((80, 80), 20, np.uint8)
    out, box = insert_target(dark, t, 5, 5, np.random.default_rng(0))
    x0, y0, x1, y1 = (int(v) for v in box)
    assert out[y0:y1, x0:x1].mean() == pytest.approx(60, abs=1)  # 3x the new level of 20


def test_insert_outside_image_is_rejected():
    t = parametric_target("block", 10)
    with pytest.raises(ValueError):
        insert_target(np.zeros((20, 20), np.uint8), t, 15, 15, np.random.default_rng(0))


def test_free_positions_avoid_boxes_and_each_other():
    rng = np.random.default_rng(3)
    t = parametric_target("block", 10)
    avoid = np.array([[0, 0, 150, 200]], float)
    pos = free_positions((200, 300), t, 3, rng, avoid=avoid)
    assert len(pos) == 3
    for x, _ in pos:
        assert x > 150
    boxes = [(x, y, x + t.shape[1], y + t.shape[0]) for x, y in pos]
    for i in range(3):
        for j in range(i + 1, 3):
            a, b = boxes[i], boxes[j]
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]


def test_texture_strata():
    cuts = texture_cuts([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    assert texture_stratum(0.05, cuts) == "smooth"
    assert texture_stratum(0.35, cuts) == "medium"
    assert texture_stratum(0.9, cuts) == "rough"
    assert texture_stratum(float("nan"), cuts) == "unknown"
    assert local_texture(np.full((40, 40), 9, np.uint8), (10, 10, 20, 20)) == 0.0


def _bright_spot_detector(image):
    """Toy detector: one box per 8x8 block whose mean exceeds 150, score = mean / 255."""
    boxes, scores = [], []
    for y in range(0, image.shape[0] - 7, 4):
        for x in range(0, image.shape[1] - 7, 4):
            m = image[y : y + 8, x : x + 8].mean()
            if m > 150:
                boxes.append((x, y, x + 8, y + 8))
                scores.append(m / 255)
    return np.array(boxes, float).reshape(-1, 4), np.array(scores, float)


def test_run_trials_strong_target_detected_weak_not():
    rng = np.random.default_rng(0)
    images = [_seabed(seed=s) for s in range(4)]
    labelled = [np.zeros((0, 4))] * 4
    base = [_bright_spot_detector(im) for im in images]

    def strong(i, r):
        return [parametric_target("block", 8, highlight=3.0)]

    def weak(i, r):
        return [parametric_target("block", 8, highlight=1.1)]

    hits = run_trials(images, ["s"] * 4, labelled, base, strong, _bright_spot_detector, rng=rng)
    misses = run_trials(images, ["s"] * 4, labelled, base, weak, _bright_spot_detector, rng=rng)
    assert len(hits) == 4 and all(t.detected(0.5) for t in hits)
    assert len(misses) == 4 and not any(t.detected(0.5) for t in misses)
    strat = with_strata(hits, (0.1, 0.5))
    assert all(t.stratum in ("smooth", "medium", "rough") for t in strat)


def test_run_trials_never_credits_existing_detection():
    """A target pasted next to a pre-existing bright object must not borrow its detection."""
    img = _seabed(h=60, w=60)
    img[0:60, 0:60] = 80
    img[20:28, 20:28] = 250  # existing object, labelled
    labelled = [np.array([[20, 20, 28, 28]], float)]
    base = [_bright_spot_detector(img)]
    trials = run_trials(
        [img],
        ["s"],
        labelled,
        base,
        lambda i, r: [parametric_target("block", 8, highlight=1.0)],
        _bright_spot_detector,
        rng=np.random.default_rng(5),
    )
    assert all(t.score == 0.0 for t in trials)


def test_run_trials_alignment_checked():
    with pytest.raises(ValueError):
        run_trials(
            [np.zeros((5, 5))],
            [],
            [],
            [],
            lambda i, r: [],
            _bright_spot_detector,
            rng=np.random.default_rng(0),
        )


def test_completeness_map_grid_and_bounds():
    from netsight.trust.injection import completeness_map

    rng = np.random.default_rng(2)
    img = _seabed(h=120, w=180)
    cells = completeness_map(
        [img],
        [_bright_spot_detector(img)],
        _bright_spot_detector,
        0.5,
        library=[parametric_target("block", 8, highlight=3.0)],
        rng=rng,
        passes=3,
        per_pass=4,
        grid=(2, 3),
        min_trials=1,
    )
    assert len(cells) == 6
    assert sum(c.n_trials for c in cells) > 0
    for c in cells:
        if c.n_trials:
            assert 0 <= c.pd_lower <= c.pd <= 1
        else:
            assert np.isnan(c.pd)


def test_targets_never_placed_off_seabed():
    from netsight.trust.injection import seabed_mask

    img = _seabed(h=200, w=300)
    img[:, 120:180] = 5  # dark water column at nadir
    mask = seabed_mask(img)
    assert not mask[:, 140:160].any() and mask[:, :100].all()
    rng = np.random.default_rng(4)
    t = parametric_target("block", 10)
    for x, _ in free_positions((200, 300), t, 20, rng, avoid=np.zeros((0, 4)), allowed=mask):
        assert x + t.shape[1] <= 120 or x >= 180


def test_completeness_cells_carry_searched_fraction_and_area_pd():
    from netsight.trust.injection import completeness_map

    img = _seabed(h=120, w=180)
    searched_off = np.zeros(img.shape, bool)
    searched_off[:, :60] = True  # left third of the image was not searched
    cells = completeness_map(
        [img],
        [_bright_spot_detector(img)],
        _bright_spot_detector,
        0.5,
        library=[parametric_target("block", 8, highlight=3.0)],
        rng=np.random.default_rng(2),
        passes=3,
        per_pass=4,
        grid=(2, 3),
        min_trials=1,
        not_searched=[searched_off],
    )
    left = [c for c in cells if c.col == 0]
    assert all(c.status == "not_searched" and c.searched_fraction == 0 for c in left)
    assert all(c.pd_lower_area == 0 for c in left)
    for c in cells:
        if c.col > 0 and c.status == "ok":
            assert c.searched_fraction == 1 and c.pd_lower_area == c.pd_lower
