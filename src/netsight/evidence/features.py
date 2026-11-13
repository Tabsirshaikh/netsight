"""Compute soft evidence; no feature is a detection gate or penalty.

Angles describe an unoriented line relative to increasing column index:
0 degrees is horizontal, and 90 degrees points along increasing row index.
Thus a line descending to the right has an angle between 0 and 90 degrees.

Boxes are clipped before rasterization, using floor for starts and ceil for
ends. A clipped extent smaller than three pixels on either axis is empty.
Empty features have all numeric values zero, all booleans false, and height,
wavelength, and line orientation None. Insufficient anomaly context likewise
returns score zero and anomaly_valid=False. Missing height geometry returns
None, not NaN. All features are descriptive, including shadow_present.
"""

from dataclasses import asdict, dataclass
from typing import TypedDict, Unpack

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import ndimage, signal

type Box = tuple[float, float, float, float]
type _FloatArray = NDArray[np.float64]
type _BoolArray = NDArray[np.bool_]
type _Bounds = tuple[int, int, int, int]

_EPS = 1e-12


@dataclass(frozen=True)
class EvidenceFeatures:
    """Expert-facing measurements, never gates or penalties."""

    shadow_present: bool = False
    shadow_length_px: float = 0.0
    shadow_contrast: float = 0.0
    height_m: float | None = None
    periodicity_ratio: float = 0.0
    periodicity_wavelength_px: float | None = None
    gabor_energy: float = 0.0
    line_strength: float = 0.0
    line_length_px: float = 0.0
    line_orientation_deg: float | None = None
    ripple_coherence_ring: float = 0.0
    ripple_coherence_box: float = 0.0
    ripple_deviation: float = 0.0
    anomaly_score: float = 0.0
    anomaly_valid: bool = False

    def as_dict(self) -> dict[str, float | bool | None]:
        """Return a fresh dictionary of scalar feature values."""
        return asdict(self)


class _Options(TypedDict, total=False):
    range_sign: int
    metres_per_px: float | None
    altitude_m: float | None
    ground_range_m: float | None
    seed: int
    shadow_ratio: float


def _clip_box(box: Box, shape: tuple[int, ...]) -> _Bounds | None:
    """Clip continuous coordinates before outward rasterization."""
    height, width = shape
    x0, y0, x1, y1 = (float(value) for value in box)
    if not np.all(np.isfinite([x0, y0, x1, y1])):
        raise ValueError("Box coordinates must be finite.")
    x0, x1 = np.clip([x0, x1], 0, width)
    y0, y1 = np.clip([y0, y1], 0, height)
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None
    return int(np.floor(x0)), int(np.floor(y0)), int(np.ceil(x1)), int(np.ceil(y1))


def _context(
    image: _FloatArray, bounds: _Bounds
) -> tuple[_FloatArray, _BoolArray, tuple[slice, slice]]:
    """Return a context crop, its ring mask, and its box slices."""
    x0, y0, x1, y1 = bounds
    margin = int(np.ceil(max(8.0, 0.5 * max(x1 - x0, y1 - y0))))
    left, top = max(0, x0 - margin), max(0, y0 - margin)
    right = min(image.shape[1], x1 + margin)
    bottom = min(image.shape[0], y1 + margin)
    crop = image[top:bottom, left:right]
    inside = (slice(y0 - top, y1 - top), slice(x0 - left, x1 - left))
    ring = np.ones(crop.shape, dtype=bool)
    ring[inside] = False
    return crop, ring, inside


def _shadow(
    image: _FloatArray,
    bounds: _Bounds,
    background: float,
    range_sign: int,
    shadow_ratio: float,
) -> tuple[bool, float, float]:
    """Measure the first dark run starting within two pixels of the far edge.

    If the detector's box already includes the shadow, this looks beyond it and may miss it.
    """
    x0, y0, x1, y1 = bounds
    limit = 4 * (x1 - x0)
    if range_sign == 1:
        strip = image[y0:y1, x1 : min(image.shape[1], x1 + limit)]
    else:
        strip = image[y0:y1, max(0, x0 - limit) : x0][:, ::-1]
    if strip.shape[1] == 0:
        return False, 0.0, 0.0

    filtered = ndimage.median_filter(strip, size=(1, 3), mode="nearest")
    dark = filtered < shadow_ratio * background
    lengths = np.zeros(strip.shape[0], dtype=np.float64)
    samples: list[_FloatArray] = []
    for row_index, row in enumerate(dark):
        starts = np.flatnonzero(row[:3])
        if starts.size == 0:
            continue
        start = int(starts[0])
        ends = np.flatnonzero(~row[start:])
        end = start + int(ends[0]) if ends.size else row.size
        lengths[row_index] = end - start
        samples.append(strip[row_index, start:end])

    shadowed = lengths >= 3
    # Median over rows that have a shadow run: rows without one must not drag it to zero.
    length = float(np.median(lengths[shadowed])) if shadowed.any() else 0.0
    present = bool(np.mean(shadowed) >= 0.3)
    contrast = 0.0
    if present and abs(background) > _EPS and samples:
        contrast = float(1.0 - np.mean(np.concatenate(samples)) / background)
    return present, length, contrast


def _height(
    present: bool,
    length: float,
    metres_per_px: float | None,
    altitude_m: float | None,
    ground_range_m: float | None,
) -> float | None:
    """Apply flat-seabed geometry only when geometry and shadow are available."""
    if not present or metres_per_px is None or altitude_m is None or ground_range_m is None:
        return None
    values = [metres_per_px, altitude_m, ground_range_m]
    if not np.all(np.isfinite(values)):
        return None
    if metres_per_px <= 0 or altitude_m < 0 or ground_range_m < 0:
        return None
    shadow_m = length * metres_per_px
    return float(altitude_m * shadow_m / (ground_range_m + shadow_m))


def _texture(patch: _FloatArray) -> tuple[float, float | None, float]:
    """Compute spectral peak statistics and normalized real-Gabor energy."""
    height, width = patch.shape
    centered = patch - np.mean(patch)
    window = np.hanning(height)[:, None] * np.hanning(width)[None, :]
    power = np.abs(np.fft.fft2(centered * window)) ** 2
    ky = np.fft.fftfreq(height) * height
    kx = np.fft.fftfreq(width) * width
    eligible = np.hypot(ky[:, None], kx[None, :]) >= 2.0
    ratio = 0.0
    wavelength = None
    if np.any(eligible):
        spectrum = power[eligible]
        peak_index = int(np.argmax(np.where(eligible, power, -np.inf)))
        iy, ix = np.unravel_index(peak_index, power.shape)
        ratio = float(power[iy, ix] / (np.median(spectrum) + _EPS))
        frequency = float(np.hypot(ky[iy] / height, kx[ix] / width))
        if ratio >= 10 and frequency > 0:
            wavelength = 1.0 / frequency

    variance = float(np.var(patch))
    energy = 0.0
    for period in (4.0, 8.0, 16.0):
        sigma = 0.56 * period
        radius = int(np.ceil(3 * sigma))
        yy, xx = np.mgrid[-radius : radius + 1, -radius : radius + 1]
        envelope = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
        for angle in np.arange(4) * np.pi / 4:
            projected = xx * np.cos(angle) + yy * np.sin(angle)
            kernel = envelope * np.cos(2 * np.pi * projected / period)
            kernel -= np.mean(kernel)
            kernel /= np.sqrt(np.sum(kernel**2)) + _EPS
            response = signal.fftconvolve(centered, kernel, mode="same")
            energy = max(energy, float(np.mean(response**2) / (variance + _EPS)))
    return ratio, wavelength, energy


def _ridge_response(crop: _FloatArray) -> _FloatArray:
    """Compute sign-symmetric, scale-normalized Frangi-style ridge responses."""
    centered = crop - np.mean(crop)
    result = np.zeros_like(crop)
    for sigma in (1.0, 2.0, 3.0):
        xx = ndimage.gaussian_filter(centered, sigma, order=(0, 2)) * sigma**2
        yy = ndimage.gaussian_filter(centered, sigma, order=(2, 0)) * sigma**2
        xy = ndimage.gaussian_filter(centered, sigma, order=(1, 1)) * sigma**2
        delta = np.hypot(xx - yy, 2 * xy)
        eigen_a = 0.5 * (xx + yy + delta)
        eigen_b = 0.5 * (xx + yy - delta)
        small = np.minimum(np.abs(eigen_a), np.abs(eigen_b))
        large = np.maximum(np.abs(eigen_a), np.abs(eigen_b))
        magnitude = np.hypot(small, large)
        scale = float(np.max(magnitude)) * 0.5
        if scale <= _EPS:
            continue
        ratio = small / (large + _EPS)
        response = np.exp(-(ratio**2) / 0.5)
        response *= -np.expm1(-(magnitude**2) / (2 * scale**2))
        result = np.maximum(result, response)
    return result


def _line(
    crop: _FloatArray, ring: _BoolArray, inside: tuple[slice, slice]
) -> tuple[float, float, float | None]:
    """Hough-search ridge pixels; angles run from columns toward rows."""
    response = _ridge_response(crop)
    ring_values = response[ring]
    threshold = float(np.percentile(ring_values, 95)) if ring_values.size else 0.0
    box_response = response[inside]
    # Also require half the box's peak: on a flat background the ring threshold is near zero and
    # the blurred ridge becomes a thick band whose longest chord is the box diagonal.
    threshold = max(threshold, 0.5 * float(np.max(box_response, initial=0.0)))
    yy, xx = np.nonzero(box_response > max(threshold, _EPS))
    if xx.size < 2:
        return 0.0, 0.0, None

    # A tangent at theta has normal (-sin(theta), cos(theta)).
    diagonal = int(np.ceil(np.hypot(*box_response.shape)))
    best_votes = 0
    best_angle = 0
    best_rho = 0
    for angle in range(180):
        theta = np.deg2rad(angle)
        rho = np.rint(-xx * np.sin(theta) + yy * np.cos(theta)).astype(np.int64)
        votes = np.bincount(rho + diagonal, minlength=2 * diagonal + 1)
        index = int(np.argmax(votes))
        if int(votes[index]) > best_votes:
            best_votes = int(votes[index])
            best_angle = angle
            best_rho = index - diagonal

    theta = np.deg2rad(best_angle)
    distances = -xx * np.sin(theta) + yy * np.cos(theta)
    inliers = np.abs(distances - best_rho) <= 1.0
    if np.count_nonzero(inliers) < 2:
        return 0.0, 0.0, None
    along = xx[inliers] * np.cos(theta) + yy[inliers] * np.sin(theta)
    length = float(np.max(along) - np.min(along))
    background = float(np.mean(ring_values)) if ring_values.size else 0.0
    strength = float(np.mean(box_response[yy[inliers], xx[inliers]]) / (background + _EPS))
    return strength, length, float(best_angle)


def _ripple(
    crop: _FloatArray, ring: _BoolArray, inside: tuple[slice, slice]
) -> tuple[float, float, float]:
    """Compare tensor coherences and coherence-weighted doubled-angle means."""
    centered = crop - np.mean(crop)
    gx = ndimage.gaussian_filter(centered, 1.0, order=(0, 1))
    gy = ndimage.gaussian_filter(centered, 1.0, order=(1, 0))
    xx = ndimage.gaussian_filter(gx * gx, 4.0)
    yy = ndimage.gaussian_filter(gy * gy, 4.0)
    xy = ndimage.gaussian_filter(gx * gy, 4.0)
    delta = np.hypot(xx - yy, 2 * xy)
    coherence = (delta / (xx + yy + _EPS)) ** 2
    angle2 = np.arctan2(2 * xy, xx - yy)

    def summarize(mask: _BoolArray) -> tuple[float, float]:
        if not np.any(mask):
            return 0.0, 0.0
        weights = coherence[mask]
        orientation = 0.5 * np.arctan2(
            np.mean(weights * np.sin(angle2[mask])),
            np.mean(weights * np.cos(angle2[mask])),
        )
        return float(np.mean(weights)), float(orientation)

    box_mask = np.zeros(crop.shape, dtype=bool)
    box_mask[inside] = True
    ring_coherence, ring_orientation = summarize(ring)
    box_coherence, box_orientation = summarize(box_mask)
    deviation = abs(ring_coherence - box_coherence)
    deviation += ring_coherence * np.sin(ring_orientation - box_orientation) ** 2
    return ring_coherence, box_coherence, float(deviation)


def _patch_vector(patch: _FloatArray, histogram_range: tuple[float, float]) -> _FloatArray:
    """Summarize intensity, gradients, and fixed-range histogram entropy."""
    gy, gx = np.gradient(patch)
    low, high = histogram_range
    # Clipping includes tail pixels in the end bins rather than discarding them.
    counts, _ = np.histogram(np.clip(patch, low, high), bins=32, range=histogram_range)
    probabilities = counts[counts > 0] / patch.size
    entropy = -np.sum(probabilities * np.log(probabilities))
    q10, q90 = np.percentile(patch, [10, 90])
    return np.asarray(
        [
            np.mean(patch),
            np.std(patch),
            q10,
            q90,
            np.mean(np.hypot(gx, gy)),
            entropy,
        ],
        dtype=np.float64,
    )


def _anomaly(image: _FloatArray, bounds: _Bounds, seed: int) -> tuple[float, bool]:
    """Sample up to 64 distinct non-overlapping-with-box patch origins."""
    x0, y0, x1, y1 = bounds
    height, width = y1 - y0, x1 - x0
    nx, ny = image.shape[1] - width + 1, image.shape[0] - height + 1
    # Four disjoint rectangles tile all legal origins. Background patches may
    # overlap one another, but cannot overlap the target box.
    middle_start = max(0, y0 - height + 1)
    middle_end = min(ny, y1)
    rectangles = [
        (0, nx, 0, middle_start),
        (0, nx, middle_end, ny),
        (0, max(0, x0 - width + 1), middle_start, middle_end),
        (min(nx, x1), nx, middle_start, middle_end),
    ]
    sizes = [(right - left) * (bottom - top) for left, right, top, bottom in rectangles]
    total = sum(sizes)
    if total < 8:
        return 0.0, False

    low, high = (float(value) for value in np.percentile(image, [1, 99]))
    if high <= low:
        high = low + max(1.0, abs(low) * 1e-6)
    histogram_range = (low, high)
    rng = np.random.default_rng(seed)
    indices = rng.choice(total, size=min(64, total), replace=False)
    vectors: list[_FloatArray] = []
    for sampled_index in indices:
        index = int(sampled_index)
        for (left, right, top, _bottom), size in zip(rectangles, sizes, strict=True):
            if index < size:
                y = top + index // (right - left)
                x = left + index % (right - left)
                vectors.append(_patch_vector(image[y : y + height, x : x + width], histogram_range))
                break
            index -= size

    features = np.stack(vectors)
    median = np.median(features, axis=0)
    mad = np.median(np.abs(features - median), axis=0)
    target = _patch_vector(image[y0:y1, x0:x1], histogram_range)
    z = (target - median) / (1.4826 * mad + _EPS)
    return float(np.sqrt(np.mean(z**2))), True


def evidence_features(
    image: ArrayLike,
    box: Box,
    *,
    range_sign: int = 1,
    metres_per_px: float | None = None,
    altitude_m: float | None = None,
    ground_range_m: float | None = None,
    seed: int = 0,
    shadow_ratio: float = 0.5,
) -> EvidenceFeatures:
    """Measure soft L3 evidence for one clipped box.

    The range axis is columns; shadow search starts outside the far-range
    edge, to the right for +1 and left for -1. Ground range refers to that
    edge. Context is a rectangular ring with margin max(8, half the larger
    box dimension). When no ring exists, box median supplies the shadow
    background; line and ripple ring summaries default to zero.

    Spectral wavelength uses physical pixel frequencies, including for
    rectangular boxes. Raw peak/median noise ratios are not calibrated
    significance scores and depend on the number of Fourier bins.
    """
    array = np.asarray(image, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("image must be two-dimensional.")
    if not np.all(np.isfinite(array)):
        raise ValueError("image must contain finite values.")
    if range_sign not in (-1, 1):
        raise ValueError("range_sign must be +1 or -1.")
    if not np.isfinite(shadow_ratio) or shadow_ratio <= 0:
        raise ValueError("shadow_ratio must be finite and positive.")
    bounds = _clip_box(box, array.shape)
    if bounds is None:
        return EvidenceFeatures()

    crop, ring, inside = _context(array, bounds)
    patch = crop[inside]
    background = float(np.median(crop[ring])) if np.any(ring) else float(np.median(patch))
    present, length, contrast = _shadow(array, bounds, background, range_sign, shadow_ratio)
    height = _height(present, length, metres_per_px, altitude_m, ground_range_m)
    periodicity, wavelength, gabor = _texture(patch)
    strength, line_length, orientation = _line(crop, ring, inside)
    ring_coherence, box_coherence, deviation = _ripple(crop, ring, inside)
    anomaly, valid = _anomaly(array, bounds, seed)
    return EvidenceFeatures(
        shadow_present=present,
        shadow_length_px=length,
        shadow_contrast=contrast,
        height_m=height,
        periodicity_ratio=periodicity,
        periodicity_wavelength_px=wavelength,
        gabor_energy=gabor,
        line_strength=strength,
        line_length_px=line_length,
        line_orientation_deg=orientation,
        ripple_coherence_ring=ring_coherence,
        ripple_coherence_box=box_coherence,
        ripple_deviation=deviation,
        anomaly_score=anomaly,
        anomaly_valid=valid,
    )


def evidence_table(
    image: ArrayLike,
    boxes: list[Box],
    **kwargs: Unpack[_Options],
) -> list[dict[str, float | bool | None | int]]:
    """Return feature dictionaries with stable, zero-based box indices."""
    rows: list[dict[str, float | bool | None | int]] = []
    for index, box in enumerate(boxes):
        row: dict[str, float | bool | None | int] = {
            **evidence_features(image, box, **kwargs).as_dict(),
            "box_index": index,
        }
        rows.append(row)
    return rows


def evidence_both_sides(image: ArrayLike, box: Box, **kwargs: object) -> dict:
    """Evidence with the shadow searched on both sides of the box (side not known).

    On a centre-nadir waterfall the far-range side, where the shadow falls, is right for
    starboard objects and left for port objects. Re-check 2026-11-13: searching only to the
    right missed most left-side shadows. The side with the longer shadow run is reported.
    """
    right = evidence_features(image, box, range_sign=1, **kwargs).as_dict()  # type: ignore[arg-type]
    left = evidence_features(image, box, range_sign=-1, **kwargs).as_dict()  # type: ignore[arg-type]
    candidates = [
        (d, side) for d, side in ((right, "right"), (left, "left")) if d["shadow_present"]
    ]
    if not candidates:
        return {**right, "shadow_side": None}
    best, side = max(candidates, key=lambda c: c[0]["shadow_length_px"])
    return {**best, "shadow_side": side}
