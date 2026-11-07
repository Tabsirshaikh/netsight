"""Tests for whole-survey bootstrap intervals."""

import numpy as np
import pytest
from numpy.typing import NDArray

from netsight.trust.bootstrap import survey_bootstrap


def mean(values: NDArray[np.float64]) -> float:
    """Return the mean of values."""
    return float(np.mean(values))


def test_full_data_estimate() -> None:
    groups = np.repeat(["a", "b", "c"], [2, 3, 4])
    values = np.repeat([1.0, 4.0, 10.0], [2, 3, 4])
    result = survey_bootstrap(mean, groups, values, n_boot=300, rng=np.random.default_rng(0))
    assert result.estimate == pytest.approx(6)
    assert result.n_groups == 3
    assert result.n_boot_used == 300
    assert result.n_boot_nan == 0
    assert result.low <= result.estimate <= result.high


def test_identical_surveys_collapse_interval() -> None:
    groups = np.repeat(["a", "b", "c"], 3)
    values = np.tile([1.0, 2.0, 3.0], 3)
    result = survey_bootstrap(mean, groups, values, n_boot=100, rng=np.random.default_rng(1))
    assert result.estimate == 2
    assert result.low == result.estimate == result.high


def test_whole_survey_rows_travel_together() -> None:
    sizes = np.array([2, 3, 4])
    groups = np.repeat(np.arange(3), sizes)
    row_ids = np.arange(groups.size)

    def intact(ids: NDArray[np.int64], rows: NDArray[np.int64]) -> float:
        for survey, size in enumerate(sizes):
            selected = rows[ids == survey]
            assert selected.size % size == 0
            expected = row_ids[groups == survey]
            counts = [np.count_nonzero(selected == row) for row in expected]
            assert len(set(counts)) == 1
        return float(rows.size)

    result = survey_bootstrap(
        intact, groups, groups, row_ids, n_boot=100, rng=np.random.default_rng(2)
    )
    assert result.estimate == 9
    assert result.n_boot_used == 100


def test_reproducibility() -> None:
    groups = np.repeat(["a", "b", "c"], 4)
    values = np.arange(12, dtype=float)
    first = survey_bootstrap(mean, groups, values, n_boot=200, rng=np.random.default_rng(3))
    second = survey_bootstrap(mean, groups, values, n_boot=200, rng=np.random.default_rng(3))
    assert first == second


def test_nan_replicates_counted() -> None:
    def sometimes_nan(values: NDArray[np.float64]) -> float:
        return np.nan if np.all(values == values[0]) else mean(values)

    result = survey_bootstrap(
        sometimes_nan,
        ["a", "b", "c"],
        [0.0, 1.0, 2.0],
        n_boot=300,
        rng=np.random.default_rng(4),
    )
    assert result.estimate == 1
    assert 0 < result.n_boot_nan < 300
    assert result.n_boot_used + result.n_boot_nan == 300
    assert np.isfinite(result.low)
    assert np.isfinite(result.high)


def test_all_nan_replicates() -> None:
    result = survey_bootstrap(
        lambda _: float("nan"),
        ["a", "b"],
        [1, 2],
        n_boot=20,
        rng=np.random.default_rng(5),
    )
    assert result.n_boot_used == 0
    assert result.n_boot_nan == 20
    assert np.isnan(result.low)
    assert np.isnan(result.high)


@pytest.mark.parametrize(
    ("groups", "values", "n_boot"),
    [
        (["a", "a"], [1, 2], 10),
        (["a", "b"], [1], 10),
        (["a", "b"], [1, 2], 0),
        ([["a", "b"]], [1, 2], 10),
    ],
)
def test_invalid_inputs(
    groups: list[str] | list[list[str]], values: list[int], n_boot: int
) -> None:
    with pytest.raises(ValueError):
        survey_bootstrap(mean, groups, values, n_boot=n_boot, rng=np.random.default_rng(6))


def test_invalid_alpha() -> None:
    with pytest.raises(ValueError, match="alpha"):
        survey_bootstrap(mean, ["a", "b"], [1, 2], alpha=1, rng=np.random.default_rng(7))
