"""Synthetic checks; line angles run from increasing columns toward rows."""

import numpy as np
import pytest

from netsight.evidence import EvidenceFeatures, evidence_features, evidence_table


def _shadow_scene(sign: int) -> np.ndarray:
    rng = np.random.default_rng(12)
    image = rng.normal(100.0, 5.0, (100, 140))
    image[40:50, 60:70] = 200.0
    if sign == 1:
        image[40:50, 70:90] = 20.0
    else:
        image[40:50, 40:60] = 20.0
    return image


def _assert_finite(features: EvidenceFeatures) -> None:
    for value in features.as_dict().values():
        if isinstance(value, float):
            assert np.isfinite(value)


def test_starboard_shadow_and_height() -> None:
    features = evidence_features(
        _shadow_scene(1),
        (60.0, 40.0, 70.0, 50.0),
        metres_per_px=0.1,
        altitude_m=10.0,
        ground_range_m=30.0,
    )
    assert features.shadow_present
    assert features.shadow_length_px == pytest.approx(20.0, abs=2.0)
    assert features.shadow_contrast > 0.7
    assert features.height_m == pytest.approx(10 * 2 / (30 + 2), rel=0.1)


def test_port_shadow_and_wrong_side() -> None:
    box = (60.0, 40.0, 70.0, 50.0)
    correct = evidence_features(_shadow_scene(-1), box, range_sign=-1)
    wrong = evidence_features(_shadow_scene(1), box, range_sign=-1)
    assert correct.shadow_present
    assert correct.shadow_length_px == pytest.approx(20.0, abs=2.0)
    assert not wrong.shadow_present
    assert wrong.shadow_contrast == 0.0


def test_flat_textured_patch_has_no_shadow() -> None:
    rng = np.random.default_rng(33)
    image = rng.normal(100.0, 3.0, (100, 100))
    features = evidence_features(
        image,
        (35.0, 35.0, 65.0, 65.0),
        altitude_m=10.0,
        metres_per_px=0.1,
        ground_range_m=30.0,
    )
    assert not features.shadow_present
    assert features.height_m is None
    _assert_finite(features)


def test_grating_periodicity() -> None:
    rng = np.random.default_rng(91)
    image = rng.normal(100.0, 2.0, (120, 120))
    yy, xx = np.mgrid[:40, :40]
    image[40:80, 40:80] = 100 + 30 * np.sin(2 * np.pi * xx / 6)
    features = evidence_features(image, (40.0, 40.0, 80.0, 80.0))
    noise = evidence_features(rng.normal(100.0, 2.0, (120, 120)), (40.0, 40.0, 80.0, 80.0))
    assert features.periodicity_ratio > 10
    assert features.periodicity_wavelength_px == pytest.approx(6.0, abs=1.0)
    # A raw maximum/median statistic has a multiple-bin noise floor, not a
    # universal cutoff of 10. Noise must be far below the coherent grating.
    assert noise.periodicity_ratio < 30
    assert noise.periodicity_ratio < features.periodicity_ratio / 100
    assert features.gabor_energy > noise.gabor_energy
    assert yy.shape == xx.shape


def test_line_length_and_orientation() -> None:
    image = np.full((140, 140), 100.0)
    yy, xx = np.mgrid[:60, :60]
    theta = np.deg2rad(30.0)
    # Perpendicular distance defines a two-pixel-wide line. Positive angles
    # descend toward increasing rows as columns increase.
    distance = -(xx - 29.5) * np.sin(theta) + (yy - 29.5) * np.cos(theta)
    image[40:100, 40:100] += 100 * (np.abs(distance) <= 1.0)
    features = evidence_features(image, (40.0, 40.0, 100.0, 100.0))
    assert features.line_length_px > 40
    assert features.line_orientation_deg is not None
    angular_error = abs((features.line_orientation_deg - 30 + 90) % 180 - 90)
    assert angular_error <= 3
    assert features.line_strength > 1


def test_ripple_deviation() -> None:
    rng = np.random.default_rng(14)
    _, xx = np.mgrid[:200, :200]
    image = 100 + 20 * np.sin(2 * np.pi * xx / 8)
    image[120:150, 120:150] = rng.normal(100.0, 15.0, (30, 30))
    patch = evidence_features(image, (120.0, 120.0, 150.0, 150.0))
    clean = evidence_features(image, (35.0, 35.0, 65.0, 65.0))
    assert clean.ripple_coherence_ring > 0.9
    assert patch.ripple_deviation > 2 * clean.ripple_deviation
    assert patch.ripple_coherence_box < patch.ripple_coherence_ring


def test_anomaly_and_insufficient_context() -> None:
    rng = np.random.default_rng(2024)
    image = rng.normal(100.0, 3.0, (180, 180))
    image[75:95, 75:95] = rng.normal(180.0, 20.0, (20, 20))
    unusual = evidence_features(image, (75.0, 75.0, 95.0, 95.0), seed=71)
    ordinary = evidence_features(image, (25.0, 25.0, 45.0, 45.0), seed=71)
    assert unusual.anomaly_valid
    assert ordinary.anomaly_valid
    assert unusual.anomaly_score > 3 * ordinary.anomaly_score
    large = evidence_features(image, (1.0, 1.0, 179.0, 179.0))
    assert not large.anomaly_valid
    assert large.anomaly_score == 0.0
    repeated = evidence_features(image, (75.0, 75.0, 95.0, 95.0), seed=71)
    assert repeated == unusual


@pytest.mark.parametrize("level", [0.0, 100.0])
def test_constant_image(level: float) -> None:
    image = np.full((70, 80), level)
    features = evidence_features(image, (20.0, 20.0, 40.0, 40.0))
    _assert_finite(features)
    assert not features.shadow_present
    assert features.height_m is None
    assert features.periodicity_ratio == 0.0
    assert features.anomaly_score == 0.0
    assert features.line_orientation_deg is None


def test_clipped_small_and_uint8_boxes() -> None:
    rng = np.random.default_rng(42)
    image = rng.integers(80, 120, size=(80, 90), dtype=np.uint8)
    clipped = evidence_features(image, (-8.5, -4.0, 20.0, 25.0))
    _assert_finite(clipped)
    assert clipped == evidence_features(image.astype(np.float64), (0.0, 0.0, 20.0, 25.0))
    assert evidence_features(image, (10.0, 10.0, 12.0, 12.0)) == EvidenceFeatures()
    assert evidence_features(image, (-10.0, -10.0, 2.0, 2.0)) == EvidenceFeatures()
    assert evidence_features(image, (100.0, 100.0, 110.0, 110.0)) == EvidenceFeatures()
    _assert_finite(evidence_features(image, (0.0, 0.0, 90.0, 80.0)))


def test_table_and_public_dictionary() -> None:
    image = np.full((40, 40), 100, dtype=np.uint8)
    boxes = [(5.0, 5.0, 15.0, 15.0), (20.0, 20.0, 22.0, 22.0)]
    rows = evidence_table(image, boxes, seed=7, range_sign=-1)
    assert [row["box_index"] for row in rows] == [0, 1]
    assert rows[0]["shadow_present"] is False
    assert rows[1]["anomaly_valid"] is False
    assert set(rows[0]) == set(EvidenceFeatures().as_dict()) | {"box_index"}
    features = EvidenceFeatures()
    dictionary = features.as_dict()
    dictionary["shadow_present"] = True
    assert not features.shadow_present


def test_shadow_on_a_minority_of_rows_is_still_found() -> None:
    rng = np.random.default_rng(3)
    image = rng.normal(100, 5, (120, 160))
    image[50:70, 60:80] = 200
    image[50:58, 80:95] = 20  # shadow behind 8 of 20 rows (40%)
    features = evidence_features(image, (60.0, 50.0, 80.0, 70.0))
    assert features.shadow_present
    assert abs(features.shadow_length_px - 15) <= 2
