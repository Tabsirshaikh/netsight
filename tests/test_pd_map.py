"""Tests for trial aggregation and detection-probability maps."""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from netsight.trust.bounds import one_sided_lower
from netsight.trust.pd_map import aggregate_trials, combine_passes, pd_grid


def test_trial_threshold_and_exact_bound() -> None:
    cells = aggregate_trials(
        np.zeros(29),
        np.zeros(29),
        np.ones(29, dtype=bool),
        cell_size_m=1.0,
        alpha=0.05,
    )
    assert len(cells) == 1
    cell = cells[0]
    assert cell.n_trials == 29
    assert cell.n_detected == 29
    assert cell.pd_mean == 1.0
    assert cell.status == "ok"
    assert cell.confidence == 0.95
    assert cell.pd_lower == one_sided_lower(29, 29, alpha=0.05)
    assert cell.pd_lower >= 0.90

    smaller = aggregate_trials(
        np.zeros(28),
        np.zeros(28),
        np.ones(28),
        cell_size_m=1.0,
        alpha=0.05,
    )
    assert smaller[0].status == "insufficient_trials"


def test_defaults_and_frozen_cell() -> None:
    cell = aggregate_trials([0], [0], [1], cell_size_m=1.0)[0]
    assert cell.stratum == "all"
    assert cell.confidence == 0.90
    assert cell.pd_lower == one_sided_lower(1, 1, alpha=0.10)
    with pytest.raises(FrozenInstanceError):
        cell.ix = 3


def test_cell_indexing_and_origin() -> None:
    cells = aggregate_trials([-0.1, 0.0], [-0.1, 0.0], [1, 0], cell_size_m=1.0)
    assert [(cell.ix, cell.iy) for cell in cells] == [(-1, -1), (0, 0)]

    shifted = aggregate_trials(
        [-0.1, 0.0],
        [-0.1, 0.0],
        [1, 0],
        cell_size_m=1.0,
        origin=(1.0, -1.0),
    )
    assert [(cell.ix, cell.iy) for cell in shifted] == [(-2, 0), (-1, 1)]


def test_strata_have_separate_counts() -> None:
    cells = aggregate_trials(
        [0, 0, 0],
        [0, 0, 0],
        [1, 0, 1],
        cell_size_m=1.0,
        strata=["cube_1m", "cube_1m", "net_bundle"],
        min_trials=2,
    )
    assert len(cells) == 2
    cube, net = cells
    assert (cube.stratum, cube.n_trials, cube.n_detected) == ("cube_1m", 2, 1)
    assert cube.pd_mean == 0.5
    assert cube.status == "ok"
    assert (net.stratum, net.n_trials, net.n_detected) == ("net_bundle", 1, 1)
    assert net.status == "insufficient_trials"


def test_zero_detections() -> None:
    cell = aggregate_trials([0, 0], [0, 0], [0, False], cell_size_m=1.0)[0]
    assert cell.n_detected == 0
    assert cell.pd_mean == 0.0
    assert cell.pd_lower == 0.0


def test_sorting_order() -> None:
    cells = aggregate_trials(
        [2, 1, -1, 0, 3],
        [0, 1, 1, -1, -2],
        [1, 1, 0, 1, 0],
        cell_size_m=1.0,
        strata=["b", "a", "a", "a", "b"],
    )
    assert [(cell.stratum, cell.iy, cell.ix) for cell in cells] == [
        ("a", -1, 0),
        ("a", 1, -1),
        ("a", 1, 1),
        ("b", -2, 3),
        ("b", 0, 2),
    ]


def test_empty_trials() -> None:
    assert aggregate_trials([], [], [], cell_size_m=1.0) == []


def test_combine_passes() -> None:
    assert combine_passes([0.6, 0.5]) == (0.6, 0.8)
    assert combine_passes([np.nan, 0.6, np.nan, 0.5]) == (0.6, 0.8)
    assert combine_passes([0.0]) == (0.0, 0.0)
    assert combine_passes([0.3, 1.0]) == (1.0, 1.0)
    assert combine_passes(iter([0.5])) == (0.5, 0.5)


@pytest.mark.parametrize("pds", [[], [np.nan], [np.nan, np.nan]])
def test_combine_passes_without_valid_values(pds: list[float]) -> None:
    low, high = combine_passes(pds)
    assert np.isnan(low)
    assert np.isnan(high)


@pytest.mark.parametrize("value", [1.2, -0.1, np.inf, -np.inf])
def test_combine_passes_invalid_probability(value: float) -> None:
    with pytest.raises(ValueError):
        combine_passes([np.nan, value])


def test_pd_grid() -> None:
    cells = aggregate_trials(
        [4, 4, 5, 6, 4, 6, 100],
        [-2, -2, -2, -2, -1, -1, 100],
        [1, 0, 1, 0, 1, 1, 1],
        cell_size_m=1.0,
        strata=["target"] * 6 + ["other"],
    )
    grid, offset = pd_grid(cells, "target")
    assert grid.shape == (2, 3)
    assert grid.dtype == np.dtype(np.float64)
    assert offset == (4, -2)
    assert np.isnan(grid[1, 1])
    assert np.count_nonzero(np.isnan(grid)) == 1
    for cell in cells:
        if cell.stratum == "target":
            assert grid[cell.iy + 2, cell.ix - 4] == cell.pd_lower

    counts, counts_offset = pd_grid(cells, "target", field="n_trials")
    assert counts_offset == offset
    np.testing.assert_allclose(counts, [[2.0, 1.0, 1.0], [1.0, np.nan, 1.0]], equal_nan=True)

    means, _ = pd_grid(cells, "target", field="pd_mean")
    np.testing.assert_allclose(means, [[0.5, 1.0, 0.0], [1.0, np.nan, 1.0]], equal_nan=True)

    with pytest.raises(ValueError):
        pd_grid(cells, "missing")
    with pytest.raises(ValueError):
        pd_grid(cells, "target", field="unknown")
    with pytest.raises(ValueError):
        pd_grid([], "target")


@pytest.mark.parametrize(
    ("x", "y", "detected"),
    [
        ([0, 1], [0], [1]),
        ([0], [0, 1], [1]),
        ([0], [0], [1, 0]),
    ],
)
def test_mismatched_lengths(x: list[int], y: list[int], detected: list[int]) -> None:
    with pytest.raises(ValueError):
        aggregate_trials(x, y, detected, cell_size_m=1.0)


@pytest.mark.parametrize("strata", [[], ["a", "b"]])
def test_mismatched_strata(strata: list[str]) -> None:
    with pytest.raises(ValueError):
        aggregate_trials([0], [0], [1], cell_size_m=1.0, strata=strata)


@pytest.mark.parametrize("size", [0.0, -1.0, np.nan, np.inf, -np.inf])
def test_invalid_cell_size(size: float) -> None:
    with pytest.raises(ValueError):
        aggregate_trials([0], [0], [1], cell_size_m=size)


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.1, np.nan, np.inf, -np.inf])
def test_invalid_alpha(alpha: float) -> None:
    with pytest.raises(ValueError):
        aggregate_trials([0], [0], [1], cell_size_m=1.0, alpha=alpha)


@pytest.mark.parametrize("min_trials", [0, -1])
def test_invalid_min_trials(min_trials: int) -> None:
    with pytest.raises(ValueError):
        aggregate_trials([0], [0], [1], cell_size_m=1.0, min_trials=min_trials)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("axis", ["x", "y"])
def test_nonfinite_coordinates(value: float, axis: str) -> None:
    x = [value] if axis == "x" else [0.0]
    y = [value] if axis == "y" else [0.0]
    with pytest.raises(ValueError):
        aggregate_trials(x, y, [1], cell_size_m=1.0)


@pytest.mark.parametrize("value", [-1.0, 2.0, 0.5, np.nan, np.inf, -np.inf])
def test_invalid_detected(value: float) -> None:
    with pytest.raises(ValueError):
        aggregate_trials([0], [0], [value], cell_size_m=1.0)


def test_multidimensional_inputs_rejected() -> None:
    with pytest.raises(ValueError):
        aggregate_trials([[0]], [0], [1], cell_size_m=1.0)
    with pytest.raises(ValueError):
        aggregate_trials([0], [[0]], [1], cell_size_m=1.0)
    with pytest.raises(ValueError):
        aggregate_trials([0], [0], [[1]], cell_size_m=1.0)


def test_nonfinite_origin_rejected() -> None:
    with pytest.raises(ValueError):
        aggregate_trials([0], [0], [1], cell_size_m=1.0, origin=(np.nan, 0.0))
