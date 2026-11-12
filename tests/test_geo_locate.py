"""Hand-calculated geometry and uncertainty checks for contact location."""

from dataclasses import FrozenInstanceError
from math import log, sqrt

import numpy as np
import pytest

from netsight.geo.locate import NAV_SIGMA_M, ellipse_coverage, locate_contact, to_local_en


def locate(**overrides):
    """Supply a valid projected contact unless a test overrides an input."""
    inputs = {
        "ping_x": 100.0,
        "ping_y": 200.0,
        "coord_kind": "projected",
        "nav_source": "sensor",
        "heading_deg": 0.0,
        "side": "stbd",
        "ground_range_m": 10.0,
    }
    inputs.update(overrides)
    return locate_contact(**inputs)


@pytest.mark.parametrize(
    ("heading", "side", "along", "expected"),
    [
        (0.0, "stbd", 0.0, (110.0, 200.0)),
        (90.0, "port", 0.0, (100.0, 210.0)),
        (0.0, "port", 3.0, (90.0, 203.0)),
        (90.0, "stbd", -2.0, (98.0, 190.0)),
        (360.0, "stbd", 0.0, (110.0, 200.0)),
    ],
)
def test_projected_geometry(heading, side, along, expected):
    position = locate(heading_deg=heading, side=side, along_offset_m=along)
    assert (position.x, position.y) == pytest.approx(expected)
    assert not position.withdrawn
    assert position.reason is None
    assert position.method == "flat-seabed ground range, first-order covariance"


def test_latlon_geometry_and_round_trip():
    equator = locate(ping_x=3.0, ping_y=0.0, coord_kind="latlon")
    north = locate(ping_x=3.0, ping_y=60.0, coord_kind="latlon", along_offset_m=5.0)
    assert equator.x == pytest.approx(3.0 + 10.0 / 111320.0)
    assert equator.y == pytest.approx(0.0, abs=1e-12)
    assert north.x == pytest.approx(3.0 + 20.0 / 111320.0)
    assert north.y == pytest.approx(60.0 + 5.0 / 111320.0)
    assert north.x - 3.0 == pytest.approx(2 * (equator.x - 3.0))
    assert to_local_en(north.x, north.y, "latlon", 3.0, 60.0) == pytest.approx((10.0, 5.0))


def test_to_local_en_scalars_arrays_and_missing_values():
    assert to_local_en(12.0, 17.0, "projected", 10.0, 20.0) == (2.0, -3.0)
    east, north = to_local_en(
        np.array([1.0, 2.0, np.nan]), np.array([60.0, 61.0, np.nan]), "latlon", 1.0, 60.0
    )
    np.testing.assert_allclose(east[:2], [0.0, 55660.0])
    np.testing.assert_allclose(north[:2], [0.0, 111320.0])
    assert np.isnan(east[2]) and np.isnan(north[2])
    east, north = to_local_en(np.array([11.0, 12.0]), 22.0, "projected", 10.0, 20.0)
    np.testing.assert_array_equal(east, [1.0, 2.0])
    np.testing.assert_array_equal(north, [2.0, 2.0])


@pytest.mark.parametrize(
    "overrides",
    [
        {"nav_source": "missing"},
        {"coord_kind": "none"},
        {"ground_range_m": -1.0},
        {"ping_x": np.nan},
        {"ping_y": np.inf},
        {"heading_deg": np.nan},
        {"ground_range_m": np.inf},
        {"along_offset_m": np.nan},
        {"sigma_range_m": np.inf},
        {"sigma_along_m": np.nan},
        {"sigma_heading_deg": np.inf},
        {"ground_res_m": np.nan},
        {"coord_kind": "latlon", "ping_y": 90.0},
    ],
)
def test_withdrawal_never_invents_position(overrides):
    position = locate(**overrides)
    assert position.withdrawn
    assert position.reason
    assert np.isnan([position.x, position.y]).all()
    assert np.isnan(position.cov_en_m2).all()
    assert np.isnan(position.ellipse95).all()


@pytest.mark.parametrize(
    "overrides",
    [
        {"side": "left"},
        {"coord_kind": "unknown"},
        {"nav_source": "unknown"},
        {"sigma_range_m": -1.0},
        {"sigma_along_m": -1.0},
        {"sigma_heading_deg": -1.0},
        {"ground_res_m": -1.0},
        {"coord_kind": "latlon", "ping_y": 91.0},
    ],
)
def test_invalid_location_inputs(overrides):
    with pytest.raises(ValueError, match=".+"):
        locate(**overrides)


@pytest.mark.parametrize(
    ("source", "sigma"), [("sensor", 2.0), ("ship_layback", 5.0), ("ship", 15.0)]
)
def test_navigation_only_ellipse(source, sigma):
    position = locate(
        nav_source=source, sigma_range_m=0.0, sigma_along_m=0.0, sigma_heading_deg=0.0
    )
    assert NAV_SIGMA_M[source] == sigma
    assert position.cov_en_m2 == pytest.approx((sigma**2, sigma**2, 0.0))
    # For two degrees of freedom, the 95% quantile is -2 log(0.05).
    exact_axis = sigma * sqrt(-2 * log(0.05))
    assert position.ellipse95 == pytest.approx((exact_axis, exact_axis, 0.0))
    assert position.ellipse95[0] == pytest.approx(sigma * sqrt(5.991), rel=1e-4)


def test_default_uncertainty():
    position = locate(ground_range_m=100.0, sigma_heading_deg=0.0)
    # Across-track sigma=1; along-track sigma=0.5; navigation variance=4.
    assert position.cov_en_m2 == pytest.approx((5.0, 4.25, 0.0))
    assert position.ellipse95 == pytest.approx(
        (sqrt(5.0 * -2 * log(0.05)), sqrt(4.25 * -2 * log(0.05)), 90.0)
    )
    resolved = locate(ground_range_m=0.0, ground_res_m=2.0)
    assert resolved.cov_en_m2 == pytest.approx((8.0, 8.0, 0.0))


def test_rotated_covariance_heading_error_and_orientation():
    # Range variance=9. Along variance=4 + (10*pi/180 * 180/pi)^2=104.
    # At heading 45: along=(1,1)/sqrt(2), across=(1,-1)/sqrt(2).
    position = locate(
        heading_deg=45.0,
        sigma_range_m=3.0,
        sigma_along_m=2.0,
        sigma_heading_deg=180.0 / np.pi,
    )
    assert position.cov_en_m2 == pytest.approx((60.5, 60.5, 47.5))
    # Eigenvalues are nav+along=108 and nav+range=13.
    scale = -2 * log(0.05)
    assert position.ellipse95 == pytest.approx((sqrt(108 * scale), sqrt(13 * scale), 45.0))
    port = locate(
        side="port",
        heading_deg=45.0,
        sigma_range_m=3.0,
        sigma_along_m=2.0,
        sigma_heading_deg=180.0 / np.pi,
    )
    assert port.cov_en_m2 == pytest.approx(position.cov_en_m2)


def test_frozen_position_and_to_dict():
    position = locate()
    data = position.to_dict()
    assert data["x"] == 110.0
    assert data["coord_kind"] == "projected"
    assert data["cov_en_m2"] == position.cov_en_m2
    data["x"] = -1.0
    assert position.x == 110.0
    with pytest.raises(FrozenInstanceError):
        position.x = 0.0


def test_coverage_hand_computed():
    # Cov=diag(4,1): squared distances are 0, 4, 9 and 8.
    true = np.array([[0.0, 0.0], [4.0, 0.0], [0.0, 3.0], [4.0, 2.0]])
    covariance = np.tile(np.diag([4.0, 1.0]), (4, 1, 1))
    result = ellipse_coverage(true, np.zeros((4, 2)), covariance)
    assert result == {"n": 4, "inside": 2, "coverage": 0.5, "expected": 0.95}
    # At level 1-exp(-2.5), the squared-distance threshold is exactly 5.
    level = 1 - np.exp(-2.5)
    assert ellipse_coverage(true, np.zeros((4, 2)), covariance, level)["inside"] == 2


def test_coverage_correlated_covariance():
    # Inverse of [[2,1],[1,2]] is [[2,-1],[-1,2]]/3.
    # (2,2) has d2=8/3 (inside); (3,-3) has d2=18 (outside).
    true = np.array([[2.0, 2.0], [3.0, -3.0]])
    covs = np.tile([[2.0, 1.0], [1.0, 2.0]], (2, 1, 1))
    assert ellipse_coverage(true, np.zeros((2, 2)), covs)["coverage"] == 0.5


def test_simulated_coverage_acceptance():
    rng = np.random.default_rng(0)
    covariance = np.array([[4.0, 1.0], [1.0, 2.0]])
    errors = rng.multivariate_normal(np.zeros(2), covariance, size=4000)
    result = ellipse_coverage(errors, np.zeros_like(errors), np.tile(covariance, (4000, 1, 1)))
    assert result["n"] == 4000
    assert 0.93 <= result["coverage"] <= 0.97
    assert result["expected"] == 0.95


def test_empty_coverage():
    result = ellipse_coverage(np.empty((0, 2)), np.empty((0, 2)), np.empty((0, 2, 2)))
    assert result["n"] == result["inside"] == 0
    assert np.isnan(result["coverage"])


@pytest.mark.parametrize(
    ("true", "est", "covs", "level"),
    [
        (np.zeros(2), np.zeros((1, 2)), np.eye(2)[None], 0.95),
        (np.zeros((1, 2)), np.zeros((2, 2)), np.eye(2)[None], 0.95),
        (np.zeros((1, 2)), np.zeros((1, 2)), np.eye(2), 0.95),
        (np.full((1, 2), np.nan), np.zeros((1, 2)), np.eye(2)[None], 0.95),
        (np.zeros((1, 2)), np.zeros((1, 2)), np.zeros((1, 2, 2)), 0.95),
        (np.zeros((1, 2)), np.zeros((1, 2)), np.array([[[1, 1], [0, 1]]]), 0.95),
        (np.zeros((1, 2)), np.zeros((1, 2)), np.eye(2)[None], 0.0),
        (np.zeros((1, 2)), np.zeros((1, 2)), np.eye(2)[None], 1.0),
        (np.zeros((1, 2)), np.zeros((1, 2)), np.eye(2)[None], np.nan),
    ],
)
def test_invalid_coverage_inputs(true, est, covs, level):
    with pytest.raises(ValueError, match=".+"):
        ellipse_coverage(true, est, covs, level)


@pytest.mark.parametrize(
    ("kind", "ref_x", "ref_y"),
    [("none", 0.0, 0.0), ("projected", np.nan, 0.0), ("latlon", 0.0, 90.0)],
)
def test_invalid_local_reference(kind, ref_x, ref_y):
    with pytest.raises(ValueError, match=".+"):
        to_local_en(0.0, 0.0, kind, ref_x, ref_y)
