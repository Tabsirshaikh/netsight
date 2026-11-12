"""North-up metric grids and single-band probability GeoTIFF exports."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

from ._common import finite_number, positive_number


def _grid(value: Any) -> np.ndarray:
    try:
        grid = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("grid must be a two-dimensional numeric array") from exc
    if grid.ndim != 2 or 0 in grid.shape or np.isinf(grid).any():
        raise ValueError("grid must be nonempty, two-dimensional, and contain no infinities")
    return grid


def grid_from_cells(
    cells: Iterable[Any],
    stratum: Any,
    *,
    cell_size_m: float,
    origin: tuple[float, float] = (0.0, 0.0),
    field: str = "pd_lower",
) -> tuple[np.ndarray, float, float]:
    """Rasterize one stratum over its inclusive index bounding box."""
    size = positive_number(cell_size_m, "cell_size_m")
    if len(origin) != 2:
        raise ValueError("origin must contain x and y")
    ox, oy = (finite_number(value, "origin") for value in origin)
    selected = [cell for cell in cells if cell.stratum == stratum]
    if not selected:
        raise ValueError(f"unknown or empty stratum: {stratum!r}")
    values = {}
    for cell in selected:
        ix, iy = cell.ix, cell.iy
        if any(isinstance(v, bool) or not isinstance(v, (int, np.integer)) for v in (ix, iy)):
            raise ValueError("cell indices must be integers")
        if (ix, iy) in values:
            raise ValueError("duplicate cell indices within stratum")
        try:
            value = float(getattr(cell, field))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(f"cell field {field!r} must be numeric (NaN for missing)") from exc
        if np.isinf(value):
            raise ValueError("cell values must not be infinite")
        values[ix, iy] = value
    xmin, xmax = min(x for x, _ in values), max(x for x, _ in values)
    ymin, ymax = min(y for _, y in values), max(y for _, y in values)
    grid = np.full((ymax - ymin + 1, xmax - xmin + 1), np.nan, dtype=np.float64)
    for (ix, iy), value in values.items():
        grid[ymax - iy, ix - xmin] = value
    return grid, ox + xmin * size, oy + (ymax + 1) * size


def write_pd_geotiff(
    path: str | Path,
    grid_north_up: np.ndarray,
    *,
    origin_ul_x: float,
    origin_ul_y: float,
    cell_size_m: float,
    crs: str,
    nodata: float = -1.0,
    description: str,
    banner: str,
) -> Path:
    """Write a float32 LZW GeoTIFF, replacing missing values with nodata."""
    grid = _grid(grid_north_up)
    size = positive_number(cell_size_m, "cell_size_m")
    x = finite_number(origin_ul_x, "origin_ul_x")
    y = finite_number(origin_ul_y, "origin_ul_y")
    sentinel = finite_number(nodata, "nodata")
    limit = np.finfo(np.float32).max
    if abs(sentinel) > limit or np.any(np.abs(grid[np.isfinite(grid)]) > limit):
        raise ValueError("grid and nodata must fit in float32")
    sentinel32 = np.float32(sentinel)
    converted = grid.astype(np.float32)
    if np.any(converted[np.isfinite(grid)] == sentinel32):
        raise ValueError("nodata must not collide with a valid grid value")
    try:
        parsed_crs = CRS.from_user_input(crs)
    except (ValueError, TypeError, rasterio.errors.CRSError) as exc:
        raise ValueError("crs must be a valid coordinate reference system") from exc
    destination = Path(path)
    with rasterio.open(
        destination,
        "w",
        driver="GTiff",
        height=grid.shape[0],
        width=grid.shape[1],
        count=1,
        dtype="float32",
        crs=parsed_crs,
        transform=from_origin(x, y, size, size),
        nodata=float(sentinel32),
        compress="LZW",
    ) as dataset:
        dataset.write(np.where(np.isnan(grid), sentinel32, converted), 1)
        dataset.set_band_description(1, description)
        dataset.update_tags(NETSIGHT_BANNER=banner)
    return destination
