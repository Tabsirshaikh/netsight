"""Locate sonar contacts and describe their horizontal position uncertainty."""

from dataclasses import asdict, dataclass
from math import atan2, cos, degrees, isfinite, radians, sin, sqrt
from typing import Any

import numpy as np
from scipy.stats import chi2

from netsight.navigation.provenance import METRES_PER_DEG_LAT

NAV_SIGMA_M: dict[str, float] = {"sensor": 2.0, "ship_layback": 5.0, "ship": 15.0}
_METHOD = "flat-seabed ground range, first-order covariance"


@dataclass(frozen=True)
class ContactPosition:
    """A contact position with covariance expressed in local east/north metres."""

    x: float
    y: float
    coord_kind: str
    nav_source: str
    ground_range_m: float
    side: str
    cov_en_m2: tuple[float, float, float]
    ellipse95: tuple[float, float, float]
    withdrawn: bool
    reason: str | None
    method: str

    def to_dict(self) -> dict[str, Any]:
        """Return a detached dictionary, preserving NaN missing values."""
        return asdict(self)


def locate_contact(
    *,
    ping_x: float,
    ping_y: float,
    coord_kind: str,
    nav_source: str,
    heading_deg: float,
    side: str,
    ground_range_m: float,
    along_offset_m: float = 0.0,
    sigma_range_m: float | None = None,
    sigma_heading_deg: float = 1.0,
    sigma_along_m: float | None = None,
    ground_res_m: float = 0.1,
) -> ContactPosition:
    """Offset a ping position and propagate independent first-order errors.

    The heading-error contribution uses the ground range only. Longitude
    offsets use the ping latitude, not the resulting contact latitude.
    """
    if side not in {"port", "stbd"}:
        raise ValueError("side must be 'port' or 'stbd'")
    if coord_kind not in {"latlon", "projected", "none"}:
        raise ValueError("coord_kind must be 'latlon', 'projected', or 'none'")
    if nav_source not in {*NAV_SIGMA_M, "missing"}:
        raise ValueError("nav_source must be sensor, ship_layback, ship, or missing")

    def withdrawn(reason: str) -> ContactPosition:
        nan = float("nan")
        return ContactPosition(
            x=nan,
            y=nan,
            coord_kind=coord_kind,
            nav_source=nav_source,
            ground_range_m=ground_range_m,
            side=side,
            cov_en_m2=(nan, nan, nan),
            ellipse95=(nan, nan, nan),
            withdrawn=True,
            reason=reason,
            method=_METHOD,
        )

    if nav_source == "missing":
        return withdrawn("navigation source is missing")
    if coord_kind == "none":
        return withdrawn("coordinate kind has no position")

    numeric_inputs = [
        ping_x,
        ping_y,
        heading_deg,
        ground_range_m,
        along_offset_m,
        sigma_heading_deg,
        ground_res_m,
    ]
    numeric_inputs.extend(value for value in (sigma_range_m, sigma_along_m) if value is not None)
    if not all(isfinite(value) for value in numeric_inputs):
        return withdrawn("a numeric input is non-finite")
    if ground_range_m < 0:
        return withdrawn("ground_range_m must be non-negative")

    for name, value in (
        ("sigma_range_m", sigma_range_m),
        ("sigma_heading_deg", sigma_heading_deg),
        ("sigma_along_m", sigma_along_m),
        ("ground_res_m", ground_res_m),
    ):
        if value is not None and value < 0:
            raise ValueError(f"{name} must be non-negative")

    if coord_kind == "latlon":
        if not -90 <= ping_y <= 90:
            raise ValueError("ping latitude must be between -90 and 90 degrees")
        if abs(ping_y) == 90:
            return withdrawn("longitude offset is undefined at a geographic pole")

    heading = radians(heading_deg % 360)
    across_heading = heading + (np.pi / 2 if side == "stbd" else -np.pi / 2)
    along = np.array([sin(heading), cos(heading)])
    across = np.array([sin(across_heading), cos(across_heading)])
    offset = ground_range_m * across + along_offset_m * along

    if coord_kind == "projected":
        x, y = ping_x + float(offset[0]), ping_y + float(offset[1])
    else:
        x = ping_x + float(offset[0]) / (METRES_PER_DEG_LAT * cos(radians(ping_y)))
        y = ping_y + float(offset[1]) / METRES_PER_DEG_LAT

    range_sigma = (
        max(ground_res_m, 0.01 * ground_range_m) if sigma_range_m is None else sigma_range_m
    )
    along_sigma = max(ground_res_m, 0.5) if sigma_along_m is None else sigma_along_m
    heading_sigma_m = ground_range_m * radians(sigma_heading_deg)
    with np.errstate(over="ignore", invalid="ignore"):
        covariance = (
            np.eye(2) * np.square(NAV_SIGMA_M[nav_source])
            + np.square(range_sigma) * np.outer(across, across)
            + (np.square(along_sigma) + np.square(heading_sigma_m)) * np.outer(along, along)
        )
    if not np.isfinite(covariance).all() or not all(isfinite(v) for v in (x, y)):
        return withdrawn("position or covariance is non-finite after propagation")

    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    scale = float(chi2.ppf(0.95, 2))
    minor, major = (sqrt(float(value) * scale) for value in eigenvalues)
    if eigenvalues[0] == eigenvalues[1]:
        orientation = 0.0
    else:
        major_axis = eigenvectors[:, 1]
        orientation = degrees(atan2(float(major_axis[0]), float(major_axis[1]))) % 180

    return ContactPosition(
        x=x,
        y=y,
        coord_kind=coord_kind,
        nav_source=nav_source,
        ground_range_m=ground_range_m,
        side=side,
        cov_en_m2=(
            float(covariance[0, 0]),
            float(covariance[1, 1]),
            float(covariance[0, 1]),
        ),
        ellipse95=(major, minor, orientation),
        withdrawn=False,
        reason=None,
        method=_METHOD,
    )


def ellipse_coverage(
    true_en: np.ndarray,
    est_en: np.ndarray,
    covs: np.ndarray,
    level: float = 0.95,
) -> dict[str, int | float]:
    """Measure coverage of positive-definite east/north covariance ellipses.

    Empty input has zero counts and NaN coverage. Non-finite observations are
    rejected rather than silently removed from the denominator.
    """
    if not isfinite(level) or not 0 < level < 1:
        raise ValueError("level must be finite and strictly between 0 and 1")
    true_en = np.asarray(true_en, dtype=float)
    est_en = np.asarray(est_en, dtype=float)
    covs = np.asarray(covs, dtype=float)
    if true_en.ndim != 2 or true_en.shape[1] != 2:
        raise ValueError("true_en must have shape (N, 2)")
    n = len(true_en)
    if est_en.shape != (n, 2) or covs.shape != (n, 2, 2):
        raise ValueError("est_en and covs must have shapes (N, 2) and (N, 2, 2)")
    if not all(np.isfinite(array).all() for array in (true_en, est_en, covs)):
        raise ValueError("positions and covariances must be finite")
    if not np.allclose(covs, covs.swapaxes(1, 2), rtol=1e-12, atol=1e-12):
        raise ValueError("covariances must be symmetric")
    covs = (covs + covs.swapaxes(1, 2)) / 2
    if np.any(np.linalg.eigvalsh(covs) <= 0):
        raise ValueError("covariances must be positive definite")
    if n == 0:
        return {"n": 0, "inside": 0, "coverage": float("nan"), "expected": level}

    residual = true_en - est_en
    solved = np.linalg.solve(covs, residual[..., None])[..., 0]
    d2 = np.einsum("ni,ni->n", residual, solved)
    inside = int(np.count_nonzero(d2 <= chi2.ppf(level, 2)))
    return {"n": n, "inside": inside, "coverage": inside / n, "expected": level}


def to_local_en(
    x: float | np.ndarray,
    y: float | np.ndarray,
    coord_kind: str,
    ref_x: float,
    ref_y: float,
) -> tuple[float | np.ndarray, float | np.ndarray]:
    """Convert coordinates to local metres, preserving NaN missing positions.

    Arrays broadcast normally. Lat/lon conversion is equirectangular at the
    reference latitude; longitudes are used as supplied, without wrapping.
    """
    if coord_kind not in {"projected", "latlon"}:
        raise ValueError("coord_kind must be 'projected' or 'latlon' for local coordinates")
    if not isfinite(ref_x) or not isfinite(ref_y):
        raise ValueError("reference coordinates must be finite")
    if coord_kind == "latlon" and not -90 < ref_y < 90:
        raise ValueError("reference latitude must be strictly between -90 and 90 degrees")
    try:
        xs, ys = np.broadcast_arrays(np.asarray(x, dtype=float), np.asarray(y, dtype=float))
    except ValueError as exc:
        raise ValueError("x and y must be numeric and have broadcastable shapes") from exc

    east = xs - ref_x
    north = ys - ref_y
    if coord_kind == "latlon":
        east = east * METRES_PER_DEG_LAT * cos(radians(ref_y))
        north = north * METRES_PER_DEG_LAT
    if east.ndim == 0:
        return float(east), float(north)
    return east, north
