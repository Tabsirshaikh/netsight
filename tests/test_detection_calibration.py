"""Hand-computed checks for multidimensional detection calibration."""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from netsight.trust.detection_calibration import detection_ece


def test_without_features_equals_uniform_ece() -> None:
    result = detection_ece([0.2, 0.2, 0.8, 0.8], [0, 1, 1, 1], n_bins=2)

    # Half the rows have gap 0.3 and half have gap 0.2.
    assert result.d_ece == pytest.approx(0.25)
    assert result.n_used == 4
    assert result.n_dropped == 0
    assert result.n_bins_used == 2
    assert result.n_bins_sparse == 0
    assert result.worst_bins[0]["bin"] == (0,)
    assert result.worst_bins[0]["count"] == 2
    assert result.worst_bins[0]["mean_p"] == pytest.approx(0.2)
    assert result.worst_bins[0]["observed_rate"] == pytest.approx(0.5)
    assert result.worst_bins[0]["gap"] == pytest.approx(0.3)


def test_feature_conditioning_reveals_hidden_error() -> None:
    p = [0.5, 0.5, 0.5, 0.5]
    y = [1, 1, 0, 0]
    features = [[0.0], [0.0], [1.0], [1.0]]

    plain = detection_ece(p, y, n_bins=2)
    conditioned = detection_ece(p, y, features, n_bins=2, feature_bins=2)

    assert plain.d_ece == 0.0
    assert conditioned.d_ece == 0.5
    assert conditioned.n_bins_used == 2
    assert {item["bin"] for item in conditioned.worst_bins} == {(1, 0), (1, 1)}


def test_nan_rows_are_dropped_once_and_before_inferring_ranges() -> None:
    result = detection_ece(
        [0.2, np.nan, 0.8, 0.4, np.nan],
        [0, 1, np.nan, 1, np.nan],
        [[0.0], [100.0], [200.0], [np.nan], [np.nan]],
        n_bins=2,
    )

    assert result.n_dropped == 4
    assert result.n_used == 1
    assert result.d_ece == pytest.approx(0.2)
    assert result.worst_bins[0]["bin"] == (0, 0)


def test_sparse_bins_are_excluded_from_denominator() -> None:
    result = detection_ece(
        [0.1, 0.1, 0.6, 0.9],
        [0, 1, 1, 0],
        n_bins=3,
        min_bin_count=2,
    )

    # Only the first bin survives: |0.5 - 0.1| = 0.4.
    assert result.d_ece == pytest.approx(0.4)
    assert result.n_used == 2
    assert result.n_dropped == 0
    assert result.n_bins_used == 1
    assert result.n_bins_sparse == 2
    assert len(result.worst_bins) == 1


def test_all_sparse_returns_nan_without_marking_rows_dropped() -> None:
    result = detection_ece([0.1, 0.9], [0, 1], n_bins=2, min_bin_count=2)

    assert np.isnan(result.d_ece)
    assert result.n_used == 0
    assert result.n_dropped == 0
    assert result.n_bins_used == 0
    assert result.n_bins_sparse == 2
    assert result.worst_bins == []


@pytest.mark.parametrize(
    ("p", "y"),
    [
        ([], []),
        ([np.nan, 0.5], [1, np.nan]),
    ],
)
def test_no_valid_rows(p: list[float], y: list[float]) -> None:
    result = detection_ece(p, y)

    assert np.isnan(result.d_ece)
    assert result.n_used == 0
    assert result.n_dropped == len(p)
    assert result.n_bins_used == 0
    assert result.n_bins_sparse == 0
    assert result.worst_bins == []


def test_worst_bins_rank_weighted_gap_not_gap_alone() -> None:
    result = detection_ece(
        [0.1, 0.4, 0.4, 0.4],
        [1, 0, 0, 0],
        n_bins=10,
    )

    # Bin 4 contributes 3 * 0.4 = 1.2; bin 1 contributes 1 * 0.9 = 0.9.
    assert result.d_ece == pytest.approx(2.1 / 4)
    assert [item["bin"] for item in result.worst_bins] == [(4,), (1,)]
    assert result.worst_bins[0]["gap"] < result.worst_bins[1]["gap"]


def test_worst_bins_are_limited_to_five() -> None:
    p = np.arange(0.05, 0.65, 0.1)
    result = detection_ece(p, np.ones(6), n_bins=10)

    assert result.n_bins_used == 6
    assert len(result.worst_bins) == 5
    assert [item["bin"] for item in result.worst_bins] == [(0,), (1,), (2,), (3,), (4,)]
    assert result.d_ece == pytest.approx(0.7)


def test_confidence_endpoints_and_internal_boundary() -> None:
    result = detection_ece([0.0, 0.5, 1.0], [0, 1, 1], n_bins=2)

    assert result.d_ece == pytest.approx(1 / 6)
    by_bin = {item["bin"]: item for item in result.worst_bins}
    assert by_bin[(0,)]["count"] == 1
    assert by_bin[(1,)]["count"] == 2
    assert by_bin[(1,)]["mean_p"] == 0.75


def test_constant_feature_uses_one_bin() -> None:
    result = detection_ece([0.2, 0.2], [0, 1], [[7.0], [7.0]], feature_bins=9)

    assert result.n_bins_used == 1
    assert result.worst_bins[0]["bin"] == (2, 0)
    assert result.d_ece == pytest.approx(0.3)


def test_given_ranges_clip_outliers_into_edge_bins() -> None:
    result = detection_ece(
        [0.5] * 4,
        [1, 1, 0, 0],
        [[-100.0], [0.0], [1.0], [100.0]],
        n_bins=2,
        feature_bins=2,
        feature_ranges=[(0.0, 1.0)],
    )

    assert result.d_ece == 0.5
    assert result.n_used == 4
    assert result.n_dropped == 0
    assert [item["bin"] for item in result.worst_bins] == [(1, 0), (1, 1)]
    assert [item["count"] for item in result.worst_bins] == [2, 2]


def test_multiple_feature_dimensions_form_joint_bins() -> None:
    result = detection_ece(
        [0.5] * 4,
        [0, 1, 1, 0],
        [[0, 0], [0, 1], [1, 0], [1, 1]],
        feature_bins=2,
    )

    assert result.d_ece == 0.5
    assert result.n_bins_used == 4
    assert {item["bin"] for item in result.worst_bins} == {
        (5, 0, 0),
        (5, 0, 1),
        (5, 1, 0),
        (5, 1, 1),
    }


def test_result_is_frozen() -> None:
    result = detection_ece([0.5], [1])

    with pytest.raises(FrozenInstanceError):
        result.d_ece = 0.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"p": [0.5, 0.5], "y": [1]},
        {"p": [[0.5]], "y": [1]},
        {"p": [0.5], "y": [[1]]},
        {"p": [-0.01], "y": [0]},
        {"p": [1.01], "y": [1]},
        {"p": [np.inf], "y": [1]},
        {"p": [-np.inf], "y": [0]},
        {"p": [0.5], "y": [2]},
        {"p": [0.5], "y": [-1]},
        {"p": [0.5], "y": [0.5]},
        {"p": [0.5], "y": [np.inf]},
        {"p": [0.5], "y": [1], "n_bins": 0},
        {"p": [0.5], "y": [1], "n_bins": -1},
        {"p": [0.5], "y": [1], "feature_bins": 0},
        {"p": [0.5], "y": [1], "feature_bins": -1},
        {"p": [0.5], "y": [1], "min_bin_count": 0},
        {"p": [0.5], "y": [1], "min_bin_count": -1},
        {"p": [0.5], "y": [1], "features": [0.0]},
        {"p": [0.5], "y": [1], "features": [[0.0], [1.0]]},
        {"p": [0.5], "y": [1], "features": [[[0.0]]]},
        {"p": [0.5], "y": [1], "feature_ranges": [(0, 1)]},
        {"p": [0.5], "y": [1], "features": [[0]], "feature_ranges": []},
        {
            "p": [0.5],
            "y": [1],
            "features": [[0]],
            "feature_ranges": [(0, 1), (0, 1)],
        },
        {
            "p": [0.5],
            "y": [1],
            "features": [[0]],
            "feature_ranges": [(1, 1)],
        },
        {
            "p": [0.5],
            "y": [1],
            "features": [[0]],
            "feature_ranges": [(2, 1)],
        },
        {
            "p": [0.5],
            "y": [1],
            "features": [[0]],
            "feature_ranges": [(np.nan, 1)],
        },
        {
            "p": [0.5],
            "y": [1],
            "features": [[0]],
            "feature_ranges": [(0, np.inf)],
        },
        {"p": [0.5], "y": [1], "features": [[np.inf]]},
    ],
)
def test_invalid_arguments(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        detection_ece(**kwargs)  # type: ignore[arg-type]


def test_matches_plain_ece_module_on_random_data() -> None:
    from netsight.trust.calibration_metrics import expected_calibration_error

    rng = np.random.default_rng(3)
    p = rng.uniform(0, 1, 2000)
    y = (rng.uniform(0, 1, 2000) < p**1.5).astype(float)
    assert detection_ece(p, y, n_bins=10).d_ece == pytest.approx(
        expected_calibration_error(p, y, n_bins=10), abs=1e-12
    )
