"""Flat-seabed angular-response correction and local backscatter image formation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from os import PathLike
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from netsight.io.multibeam import MultibeamPing, MultibeamRecord
from netsight.navigation.provenance import METRES_PER_DEG_LAT

FloatArray = NDArray[np.float64]


def incidence_angle_deg(across_track: ArrayLike, depth: ArrayLike) -> FloatArray:
    """Return flat-seabed incidence angles; invalid geometry yields NaN."""
    across, down = np.broadcast_arrays(
        np.asarray(across_track, dtype=float), np.asarray(depth, dtype=float)
    )
    good = np.isfinite(across) & np.isfinite(down) & (down > 0)
    return np.where(good, np.degrees(np.arctan2(np.abs(across), down)), np.nan)


def _bin_indices(angles: ArrayLike, edges: FloatArray) -> NDArray[np.int64]:
    angles = np.asarray(angles, dtype=float)
    indices = np.searchsorted(edges, angles, side="right") - 1
    # Include the final edge, but never extrapolate beyond it.
    indices = np.where(angles == edges[-1], len(edges) - 2, indices)
    return np.where(
        np.isfinite(angles) & (angles >= edges[0]) & (angles <= edges[-1]), indices, -1
    ).astype(np.int64)


def _mean_db(values: FloatArray) -> float:
    """Average powers using a dB offset to avoid overflow."""
    peak = float(np.max(values))
    return float(peak + 10 * np.log10(np.mean(10 ** ((values - peak) / 10))))


@dataclass(frozen=True)
class AngularResponse:
    """Power-averaged bins, with both endpoints of the full range included.

    Interior bins are left-closed and right-open. Counts include samples even
    when their bin fails the minimum-count threshold.
    """

    bin_edges_deg: FloatArray
    mean_db: FloatArray
    count: NDArray[np.int64]
    reference_db: float

    def __post_init__(self) -> None:
        edges = np.array(self.bin_edges_deg, dtype=float, copy=True)
        means = np.array(self.mean_db, dtype=float, copy=True)
        counts = np.array(self.count, copy=True)
        if (
            edges.ndim != 1
            or edges.size < 2
            or not np.all(np.isfinite(edges))
            or not np.all(np.diff(edges) > 0)
        ):
            raise ValueError("bin edges must be finite and strictly increasing")
        if means.shape != (edges.size - 1,) or counts.shape != means.shape:
            raise ValueError("mean_db and count must have one entry per bin")
        if (
            not np.issubdtype(counts.dtype, np.integer)
            or np.any(counts < 0)
            or np.any(np.isinf(means))
            or np.isinf(self.reference_db)
        ):
            raise ValueError("counts must be nonnegative integers and levels finite or NaN")
        for name, value in (
            ("bin_edges_deg", edges),
            ("mean_db", means),
            ("count", counts.astype(np.int64)),
        ):
            value.setflags(write=False)
            object.__setattr__(self, name, value)

    def correction_db(self, angles: ArrayLike) -> FloatArray:
        """Return reference minus bin level, or NaN when no correction exists."""
        indices = _bin_indices(angles, self.bin_edges_deg)
        result = self.reference_db - self.mean_db[np.clip(indices, 0, len(self.mean_db) - 1)]
        return np.where(indices >= 0, result, np.nan)


def _pings(
    records_or_pings: MultibeamRecord | MultibeamPing | Iterable[MultibeamRecord | MultibeamPing],
) -> list[MultibeamPing]:
    if isinstance(records_or_pings, MultibeamRecord):
        return list(records_or_pings.pings)
    if isinstance(records_or_pings, MultibeamPing):
        return [records_or_pings]
    result = []
    for item in records_or_pings:
        if isinstance(item, MultibeamRecord):
            result.extend(item.pings)
        elif isinstance(item, MultibeamPing):
            result.append(item)
        else:
            raise ValueError("expected multibeam records or pings")
    return result


def _beam_arrays(ping: MultibeamPing) -> tuple[FloatArray, ...]:
    arrays = tuple(
        np.asarray(value, dtype=float)
        for value in (ping.across_track, ping.along_track, ping.depth, ping.backscatter)
    )
    if any(a.ndim != 1 or a.shape != arrays[0].shape for a in arrays):
        raise ValueError("beam arrays must be one-dimensional and equally sized")
    if np.asarray(ping.valid).shape != arrays[0].shape:
        raise ValueError("valid must have one entry per beam")
    return arrays


def fit_angular_response(
    records_or_pings: MultibeamRecord | MultibeamPing | Iterable[MultibeamRecord | MultibeamPing],
    *,
    bin_deg: float = 1.0,
    max_angle_deg: float = 75.0,
    min_count: int = 20,
    reference: tuple[float, float] = (30.0, 60.0),
) -> AngularResponse:
    """Fit valid beams by averaging linear powers, not logarithmic dB levels.

    Averaging dB biases the result low relative to mean power. The reference
    is the power mean of individual samples in the inclusive reference window,
    restricted to bins meeting min_count. No reference samples means NaN.
    """
    if (
        not np.isfinite(bin_deg)
        or bin_deg <= 0
        or not np.isfinite(max_angle_deg)
        or not 0 < max_angle_deg <= 90
    ):
        raise ValueError("bin_deg must be positive and max_angle_deg in (0, 90]")
    if not isinstance(min_count, int) or isinstance(min_count, bool) or min_count < 1:
        raise ValueError("min_count must be a positive integer")
    if (
        len(reference) != 2
        or not np.all(np.isfinite(reference))
        or not 0 <= reference[0] < reference[1] <= max_angle_deg
    ):
        raise ValueError("reference must be an increasing window within the fitted range")
    edges = np.concatenate((np.arange(0.0, max_angle_deg, bin_deg), [max_angle_deg]))
    angle_parts, value_parts = [], []
    for ping in _pings(records_or_pings):
        across, _, depth, values = _beam_arrays(ping)
        angles = incidence_angle_deg(across, depth)
        good = np.asarray(ping.valid, dtype=bool) & np.isfinite(values) & np.isfinite(angles)
        angle_parts.append(angles[good])
        value_parts.append(values[good])
    angles = np.concatenate(angle_parts) if angle_parts else np.empty(0)
    values = np.concatenate(value_parts) if value_parts else np.empty(0)
    indices = _bin_indices(angles, edges)
    counts = np.bincount(indices[indices >= 0], minlength=len(edges) - 1)
    means = np.full(len(counts), np.nan)
    for index in np.flatnonzero(counts >= min_count):
        means[index] = _mean_db(values[indices == index])
    eligible = (indices >= 0) & np.isfinite(means[np.maximum(indices, 0)])
    selected = eligible & (angles >= reference[0]) & (angles <= reference[1])
    reference_db = _mean_db(values[selected]) if np.any(selected) else float("nan")
    return AngularResponse(edges, means, counts, reference_db)


def normalise_ping(ping: MultibeamPing, ar: AngularResponse) -> FloatArray:
    """Apply GeoHab-style angle-varying gain (AVG).

    This assumes one seabed type across the fit window. Mixed-seabed surveys
    need moving-window fits, e.g. fit_moving or fit_angular_response on chunks.
    Invalid beams and beams without a supported correction remain NaN.
    """
    across, _, depth, values = _beam_arrays(ping)
    corrected = values + ar.correction_db(incidence_angle_deg(across, depth))
    return np.where(np.asarray(ping.valid, dtype=bool) & np.isfinite(corrected), corrected, np.nan)


def fit_moving(
    pings: Iterable[MultibeamPing], window_pings: int = 200, **kw: Any
) -> list[AngularResponse]:
    """Fit centred clipped windows, reusing each fit for max(1, window//4) pings.

    For even windows the recomputation index has window//2 predecessors and
    window//2 - 1 successors before clipping at the survey ends.
    """
    if not isinstance(window_pings, int) or isinstance(window_pings, bool) or window_pings < 1:
        raise ValueError("window_pings must be a positive integer")
    items = list(pings)
    step = max(1, window_pings // 4)
    result = []
    for index in range(len(items)):
        if index % step == 0:
            start = index - window_pings // 2
            ar = fit_angular_response(items[max(0, start) : start + window_pings], **kw)
        result.append(ar)
    return result


def _validate_ref(ref_lat: float, ref_lon: float) -> None:
    if not np.isfinite(ref_lat) or not -90 < ref_lat < 90:
        raise ValueError("reference latitude must be finite and strictly between -90 and 90")
    if not np.isfinite(ref_lon) or not -180 <= ref_lon <= 180:
        raise ValueError("reference longitude must be finite and within [-180, 180]")


def beam_positions_en(
    ping: MultibeamPing, ref_lat: float, ref_lon: float
) -> tuple[FloatArray, FloatArray]:
    """Return equirectangular local positions plus heading-rotated beam offsets."""
    _validate_ref(ref_lat, ref_lon)
    across, along, _, _ = _beam_arrays(ping)
    if not np.all(np.isfinite([ping.latitude, ping.longitude, ping.heading])):
        return np.full(across.shape, np.nan), np.full(across.shape, np.nan)
    if not -90 <= ping.latitude <= 90 or not -180 <= ping.longitude <= 180:
        raise ValueError("ping latitude or longitude outside geographic bounds")
    h = np.radians(ping.heading)
    east = (ping.longitude - ref_lon) * METRES_PER_DEG_LAT * np.cos(np.radians(ref_lat))
    north = (ping.latitude - ref_lat) * METRES_PER_DEG_LAT
    return (
        east + across * np.cos(h) + along * np.sin(h),
        north - across * np.sin(h) + along * np.cos(h),
    )


@dataclass(frozen=True)
class BackscatterGrid:
    """Local north-up image; empty cells are NaN with zero count."""

    values_db: FloatArray
    count: NDArray[np.int64]
    origin_east_m: float
    origin_north_m: float
    cell_m: float
    ref_lat: float
    ref_lon: float
    notes: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_ref(self.ref_lat, self.ref_lon)
        if not np.isfinite(self.cell_m) or self.cell_m <= 0:
            raise ValueError("cell_m must be finite and positive")
        if not np.all(np.isfinite([self.origin_east_m, self.origin_north_m])):
            raise ValueError("grid origin must be finite")
        values = np.array(self.values_db, dtype=float, copy=True)
        counts = np.array(self.count, copy=True)
        if (
            values.ndim != 2
            or 0 in values.shape
            or counts.shape != values.shape
            or not np.issubdtype(counts.dtype, np.integer)
            or np.any(counts < 0)
            or np.any(np.isinf(values))
            or not np.array_equal(np.isnan(values), counts == 0)
        ):
            raise ValueError("grid needs matching 2D values/counts, with NaN exactly at count zero")
        values.setflags(write=False)
        counts.setflags(write=False)
        object.__setattr__(self, "values_db", values)
        object.__setattr__(self, "count", counts)
        object.__setattr__(self, "notes", tuple(self.notes))

    def to_uint8(self, lo_pct: float = 1, hi_pct: float = 99) -> NDArray[np.uint8]:
        """Percentile-stretch finite values to 1..255; missing is 0, constant is 1."""
        if not 0 <= lo_pct < hi_pct <= 100:
            raise ValueError("percentiles must satisfy 0 <= lo_pct < hi_pct <= 100")
        good = np.isfinite(self.values_db)
        image = np.zeros(self.values_db.shape, dtype=np.uint8)
        if np.any(good):
            lo, hi = np.percentile(self.values_db[good], [lo_pct, hi_pct])
            scaled = np.zeros(np.count_nonzero(good))
            if hi > lo:
                scaled = np.clip((self.values_db[good] - lo) / (hi - lo), 0, 1)
            image[good] = np.rint(1 + 254 * scaled).astype(np.uint8)
        return image

    def transform_local(self) -> tuple[float, float, float, float, float, float]:
        """Return affine coefficients (a, b, c, d, e, f), with negative row scale."""
        return (self.cell_m, 0.0, self.origin_east_m, 0.0, -self.cell_m, self.origin_north_m)


def grid_backscatter(
    pings: Iterable[MultibeamPing],
    values_per_ping: list[ArrayLike],
    *,
    cell_m: float = 0.5,
    ref: tuple[float, float] | None = None,
) -> BackscatterGrid:
    """Power-average finite valid beams into local, metre-aligned cells.

    Both local axes use half-open [lower, upper) cells; row zero is north-most.
    No usable positions/values raises ValueError rather than inventing an extent.
    """
    if not np.isfinite(cell_m) or cell_m <= 0:
        raise ValueError("cell_m must be finite and positive")
    items = list(pings)
    if len(items) != len(values_per_ping):
        raise ValueError("values_per_ping must have one array per ping")
    if ref is None:
        ref = next(
            (
                (p.latitude, p.longitude)
                for p in items
                if np.all(np.isfinite([p.latitude, p.longitude]))
            ),
            None,
        )
    if ref is None:
        raise ValueError("no finite navigation available for a grid reference")
    _validate_ref(*ref)
    east_parts, north_parts, value_parts = [], [], []
    skipped = 0
    for ping, supplied in zip(items, values_per_ping, strict=True):
        arrays = _beam_arrays(ping)
        values = np.asarray(supplied, dtype=float)
        if values.shape != arrays[0].shape:
            raise ValueError("each value array must match its ping's beams")
        if not np.all(np.isfinite([ping.latitude, ping.longitude])):
            skipped += 1
            continue
        east, north = beam_positions_en(ping, *ref)
        good = (
            np.asarray(ping.valid, dtype=bool)
            & np.isfinite(values)
            & np.isfinite(east)
            & np.isfinite(north)
        )
        east_parts.append(east[good])
        north_parts.append(north[good])
        value_parts.append(values[good])
    values = np.concatenate(value_parts) if value_parts else np.empty(0)
    if values.size == 0:
        raise ValueError("no finite geolocated beam values to grid")
    x = np.floor(np.concatenate(east_parts) / cell_m).astype(np.int64)
    y = np.floor(np.concatenate(north_parts) / cell_m).astype(np.int64)
    xmin, xmax, ymin, ymax = int(x.min()), int(x.max()), int(y.min()), int(y.max())
    shape = (ymax - ymin + 1, xmax - xmin + 1)
    flat = (ymax - y) * shape[1] + x - xmin
    count = np.bincount(flat, minlength=shape[0] * shape[1])
    levels = np.full(count.shape, np.nan)
    for index in np.flatnonzero(count):
        levels[index] = _mean_db(values[flat == index])
    notes = (f"{skipped} pings without navigation skipped",) if skipped else ()
    return BackscatterGrid(
        levels.reshape(shape),
        count.reshape(shape),
        xmin * cell_m,
        (ymax + 1) * cell_m,
        cell_m,
        *ref,
        notes,
    )


def write_grid_geotiff(path: str | PathLike[str], grid: BackscatterGrid, utm_epsg: int) -> None:
    """Write float32/NaN UTM GeoTIFF using a translated local grid.

    Project the reference and add local offsets, ignoring projection scale and
    convergence: this is only an approximation over a few kilometres.
    """
    import rasterio
    from pyproj import CRS, Transformer
    from rasterio.transform import from_origin

    if not isinstance(utm_epsg, int) or not (
        32601 <= utm_epsg <= 32660 or 32701 <= utm_epsg <= 32760
    ):
        raise ValueError("utm_epsg must be a WGS84 UTM EPSG code (32601..32660 or 32701..32760)")
    crs = CRS.from_epsg(utm_epsg)
    east, north = Transformer.from_crs(4326, crs, always_xy=True).transform(
        grid.ref_lon, grid.ref_lat
    )
    transform = from_origin(
        east + grid.origin_east_m,
        north + grid.origin_north_m,
        grid.cell_m,
        grid.cell_m,
    )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=grid.values_db.shape[0],
        width=grid.values_db.shape[1],
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=np.nan,
    ) as dataset:
        dataset.write(grid.values_db.astype(np.float32), 1)
        dataset.update_tags(
            NETSIGHT_NOTE=(
                "Local offsets translated onto UTM; ignores projection scale and convergence. "
                "Valid approximation only over a few kilometres."
            )
        )
