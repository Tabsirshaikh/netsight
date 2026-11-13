"""Synthetic target injection on real seabed: the measured basis of NetSight's Pd numbers.

A trial pastes one target into a real sonar image at a position where the detector saw nothing
before, runs the detector, and records the best score of any detection overlapping the pasted
target. Whether a trial counts as detected is decided later, at the survey's own operating
threshold, so one set of trials serves every false-alarm budget.

Two target sources:
- transplanted: a real labelled object cut from another image of the same survey (realistic
  appearance, including its own highlight and shadow pattern), contrast-matched to the new place;
- parametric: a simple block (bright face plus acoustic shadow) or flat patch (mesh texture, no
  shadow), sized in pixels by the caller. Parametric targets are reference targets, not replicas.

Pd from injection is only as good as the targets' realism. ``realism_check`` compares injected
Pd with the detector's recall on real labelled objects of the same survey at the same threshold.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import NDArray

type FloatArray = NDArray[np.float64]
type Predictor = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]

TEXTURE_STRATA = ("smooth", "medium", "rough")


@dataclass(frozen=True)
class TargetTemplate:
    """Target pixels relative to their own background (1.0 = background level) with an alpha."""

    relative: FloatArray  # (h, w) intensity ratio to local background
    alpha: FloatArray  # (h, w) in [0, 1]
    box: tuple[float, float, float, float]  # object box inside the template (x0, y0, x1, y1)
    kind: str
    source: str

    @property
    def shape(self) -> tuple[int, int]:
        return self.relative.shape  # type: ignore[return-value]


@dataclass(frozen=True)
class Trial:
    """One injected target and the detector's response to it."""

    image_index: int
    group: str
    kind: str
    source: str
    box: tuple[float, float, float, float]
    texture: float
    stratum: str
    rel_x: float  # box centre / image width, 0..1 (across-track position in a waterfall)
    size_px: float  # sqrt(box area)
    score: float  # best overlapping detection score, 0 if none

    def detected(self, threshold: float) -> bool:
        return self.score > 0 and self.score >= threshold

    def to_dict(self) -> dict:
        return asdict(self)


def _feather(h: int, w: int, inner: tuple[int, int, int, int], ramp: int) -> FloatArray:
    """Alpha 1 inside ``inner`` (x0, y0, x1, y1), falling linearly to 0 over ``ramp`` pixels."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    x0, y0, x1, y1 = inner
    dx = np.maximum(np.maximum(x0 - xx, xx - (x1 - 1)), 0)
    dy = np.maximum(np.maximum(y0 - yy, yy - (y1 - 1)), 0)
    d = np.hypot(dx, dy)
    return np.clip(1 - d / max(ramp, 1), 0, 1)


def background_level(image: np.ndarray, box: Sequence[float], ring: int) -> float:
    """Median intensity of a ring of ``ring`` pixels around ``box`` (image clipped)."""
    h, w = image.shape[:2]
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    X0, Y0 = max(x0 - ring, 0), max(y0 - ring, 0)
    X1, Y1 = min(x1 + ring, w), min(y1 + ring, h)
    patch = image[Y0:Y1, X0:X1].astype(np.float64)
    mask = np.ones(patch.shape, bool)
    mask[max(y0 - Y0, 0) : max(y1 - Y0, 0), max(x0 - X0, 0) : max(x1 - X0, 0)] = False
    values = patch[mask]
    if values.size == 0:
        values = image.astype(np.float64).ravel()
    return float(max(np.median(values), 1.0))


def local_texture(image: np.ndarray, box: Sequence[float], ring: int = 16) -> float:
    """Coefficient of variation (std / mean) of the seabed around ``box``: speckle + relief."""
    h, w = image.shape[:2]
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    patch = image[max(y0 - ring, 0) : min(y1 + ring, h), max(x0 - ring, 0) : min(x1 + ring, w)]
    patch = patch.astype(np.float64)
    mean = patch.mean() if patch.size else 0.0
    return float(patch.std() / mean) if mean > 0 else float("nan")


def template_from_box(
    image: np.ndarray,
    box: Sequence[float],
    *,
    pad: float = 0.35,
    kind: str = "transplant",
    source: str = "",
) -> TargetTemplate:
    """Cut a real object (plus a padded, feathered margin that keeps its shadow) from an image."""
    h, w = image.shape[:2]
    x0, y0, x1, y1 = (float(v) for v in box)
    bw, bh = x1 - x0, y1 - y0
    if bw < 2 or bh < 2:
        raise ValueError("box too small to transplant")
    px, py = int(np.ceil(bw * pad)), int(np.ceil(bh * pad))
    X0, Y0 = max(int(np.floor(x0)) - px, 0), max(int(np.floor(y0)) - py, 0)
    X1, Y1 = min(int(np.ceil(x1)) + px, w), min(int(np.ceil(y1)) + py, h)
    chip = image[Y0:Y1, X0:X1].astype(np.float64)
    level = background_level(image, box, ring=max(px, py, 4))
    inner = (int(x0) - X0, int(y0) - Y0, int(np.ceil(x1)) - X0, int(np.ceil(y1)) - Y0)
    alpha = _feather(chip.shape[0], chip.shape[1], inner, ramp=max(min(px, py), 2))
    return TargetTemplate(
        relative=chip / level,
        alpha=alpha,
        box=(x0 - X0, y0 - Y0, x1 - X0, y1 - Y0),
        kind=kind,
        source=source,
    )


def parametric_target(
    kind: str,
    size_px: int,
    *,
    shadow_px: int = 0,
    shadow_side: str = "right",
    highlight: float = 2.5,
    shadow_level: float = 0.15,
    mesh_period_px: float = 4.0,
) -> TargetTemplate:
    """Reference targets: ``block`` (bright face + shadow away from the sonar) or ``flat_patch``.

    ``shadow_side`` is the far-range side of the target in the image ("left" or "right").
    """
    if size_px < 3:
        raise ValueError("size_px must be at least 3")
    if shadow_side not in ("left", "right"):
        raise ValueError("shadow_side must be 'left' or 'right'")
    margin = max(2, size_px // 4)
    if kind == "block":
        w = size_px + shadow_px + 2 * margin
        h = size_px + 2 * margin
        rel = np.ones((h, w))
        ox = margin if shadow_side == "right" else margin + shadow_px
        rel[margin : margin + size_px, ox : ox + size_px] = highlight
        if shadow_px > 0:
            sx = ox + size_px if shadow_side == "right" else margin
            rel[margin : margin + size_px, sx : sx + shadow_px] = shadow_level
        x0, x1 = ox, ox + size_px
    elif kind == "flat_patch":
        w = h = size_px + 2 * margin
        yy, xx = np.mgrid[0:size_px, 0:size_px]
        mesh = 0.5 * (
            np.cos(2 * np.pi * xx / mesh_period_px) + np.cos(2 * np.pi * yy / mesh_period_px)
        )
        rel = np.ones((h, w))
        rel[margin : margin + size_px, margin : margin + size_px] = 1.4 + 0.5 * mesh
        x0, x1 = margin, margin + size_px
    else:
        raise ValueError(f"unknown parametric kind {kind!r}")
    alpha = _feather(h, w, (margin, margin, w - margin, h - margin), ramp=margin)
    return TargetTemplate(
        relative=rel,
        alpha=alpha,
        box=(float(x0), float(margin), float(x1), float(margin + size_px)),
        kind=kind,
        source="parametric",
    )


def insert_target(
    image: np.ndarray,
    template: TargetTemplate,
    x: int,
    y: int,
    rng: np.random.Generator,
    *,
    speckle_looks: float = 4.0,
) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    """Paste ``template`` with its top-left at (x, y), scaled to the local seabed level.

    Parametric targets get multiplicative gamma speckle (``speckle_looks`` looks) so they carry
    the same grain as the seabed; transplanted targets already carry real speckle.
    """
    th, tw = template.shape
    h, w = image.shape[:2]
    if x < 0 or y < 0 or x + tw > w or y + th > h:
        raise ValueError("template does not fit at this position")
    bx0, by0, bx1, by1 = template.box
    obj_box = (x + bx0, y + by0, x + bx1, y + by1)
    level = background_level(image, (x, y, x + tw, y + th), ring=max(4, min(th, tw) // 2))
    rel = template.relative
    if template.source == "parametric" and speckle_looks > 0:
        rel = rel * rng.gamma(speckle_looks, 1 / speckle_looks, size=rel.shape)
    patch = image[y : y + th, x : x + tw].astype(np.float64)
    new = (1 - template.alpha) * patch + template.alpha * (rel * level)
    out = image.copy()
    out[y : y + th, x : x + tw] = np.clip(np.rint(new), 0, 255).astype(image.dtype)
    return out, obj_box


def _iou_one(box: Sequence[float], boxes: np.ndarray) -> np.ndarray:
    if boxes.size == 0:
        return np.zeros(0)
    b = np.asarray(boxes, float).reshape(-1, 4)
    ix = np.clip(np.minimum(box[2], b[:, 2]) - np.maximum(box[0], b[:, 0]), 0, None)
    iy = np.clip(np.minimum(box[3], b[:, 3]) - np.maximum(box[1], b[:, 1]), 0, None)
    inter = ix * iy
    area = (box[2] - box[0]) * (box[3] - box[1])
    areas = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / np.maximum(area + areas - inter, 1e-9)


def _overlaps_any(box: Sequence[float], boxes: np.ndarray, pad: float) -> bool:
    if boxes.size == 0:
        return False
    b = np.asarray(boxes, float).reshape(-1, 4)
    return bool(
        np.any(
            (b[:, 0] - pad < box[2])
            & (b[:, 2] + pad > box[0])
            & (b[:, 1] - pad < box[3])
            & (b[:, 3] + pad > box[1])
        )
    )


def seabed_mask(
    image: np.ndarray,
    *,
    window: int = 31,
    quantile: float = 75.0,
    frac: float = 0.5,
    min_level: float = 20.0,
) -> np.ndarray:
    """Pixels that look like insonified seabed: local mean brightness at least ``frac`` of the
    image's ``quantile`` brightness (and ``min_level``). Excludes the water column at nadir,
    lost far range and blank borders, where no object could be seen and none is injected."""
    from scipy.ndimage import uniform_filter

    img = np.asarray(image, dtype=np.float64)
    local = uniform_filter(img, size=window, mode="nearest")
    level = max(frac * float(np.percentile(img, quantile)), min_level)
    return local >= level


def free_positions(
    shape: tuple[int, int],
    template: TargetTemplate,
    n: int,
    rng: np.random.Generator,
    *,
    avoid: np.ndarray,
    margin: int = 8,
    max_tries: int = 400,
    allowed: np.ndarray | None = None,
) -> list[tuple[int, int]]:
    """Up to ``n`` top-left positions whose template footprint avoids ``avoid`` boxes and the
    other chosen positions."""
    h, w = shape
    th, tw = template.shape
    if th + 2 * margin > h or tw + 2 * margin > w:
        return []
    taken = [np.asarray(b, float) for b in np.asarray(avoid, float).reshape(-1, 4)]
    out: list[tuple[int, int]] = []
    for _ in range(max_tries):
        if len(out) >= n:
            break
        x = int(rng.integers(margin, w - tw - margin + 1))
        y = int(rng.integers(margin, h - th - margin + 1))
        box = (x, y, x + tw, y + th)
        if allowed is not None and not allowed[y : y + th, x : x + tw].all():
            continue
        if _overlaps_any(box, np.array(taken).reshape(-1, 4), pad=margin):
            continue
        taken.append(np.array(box, float))
        out.append((x, y))
    return out


def texture_cuts(textures: Sequence[float]) -> tuple[float, float]:
    """Tertile cut points of seabed texture, fixed per experiment before any detection."""
    t = np.asarray([v for v in textures if np.isfinite(v)], float)
    if t.size < 3:
        raise ValueError("need at least 3 finite texture values")
    lo, hi = np.quantile(t, [1 / 3, 2 / 3])
    return float(lo), float(hi)


def texture_stratum(value: float, cuts: tuple[float, float]) -> str:
    if not np.isfinite(value):
        return "unknown"
    return (
        TEXTURE_STRATA[0]
        if value < cuts[0]
        else TEXTURE_STRATA[1]
        if value < cuts[1]
        else (TEXTURE_STRATA[2])
    )


def run_trials(
    images: Sequence[np.ndarray],
    groups: Sequence[str],
    labelled: Sequence[np.ndarray],
    base_predictions: Sequence[tuple[np.ndarray, np.ndarray]],
    templates: Callable[[int, np.random.Generator], list[TargetTemplate]],
    predict: Predictor,
    *,
    rng: np.random.Generator,
    min_base_score: float = 0.05,
    match_iou: float = 0.3,
    seabed_only: bool = True,
) -> list[Trial]:
    """Inject the templates chosen for each image, re-run the detector once per image.

    Insertion avoids labelled objects and base detections scoring >= ``min_base_score``, so a
    pre-existing object or false alarm is never credited as a detection of the injected target.
    ``templates(i, rng)`` returns the targets to place in image ``i`` (any number).
    """
    if not (len(images) == len(groups) == len(labelled) == len(base_predictions)):
        raise ValueError("images, groups, labelled and base_predictions must align")
    trials: list[Trial] = []
    for i, image in enumerate(images):
        base_boxes, base_scores = base_predictions[i]
        base_boxes = np.asarray(base_boxes, float).reshape(-1, 4)
        keep = np.asarray(base_scores, float).reshape(-1) >= min_base_score
        avoid = np.concatenate([np.asarray(labelled[i], float).reshape(-1, 4), base_boxes[keep]])
        placed: list[tuple[TargetTemplate, tuple[float, float, float, float], float]] = []
        current = image
        allowed = seabed_mask(image) if seabed_only else None
        for tmpl in templates(i, rng):
            pos = free_positions(image.shape[:2], tmpl, 1, rng, avoid=avoid, allowed=allowed)
            if not pos:
                continue
            x, y = pos[0]
            texture = local_texture(image, (x, y, x + tmpl.shape[1], y + tmpl.shape[0]))
            current, obj = insert_target(current, tmpl, x, y, rng)
            avoid = np.vstack([avoid, [x, y, x + tmpl.shape[1], y + tmpl.shape[0]]])
            placed.append((tmpl, obj, texture))
        if not placed:
            continue
        boxes, scores = predict(current)
        boxes = np.asarray(boxes, float).reshape(-1, 4)
        scores = np.asarray(scores, float).reshape(-1)
        w = image.shape[1]
        for tmpl, obj, texture in placed:
            iou = _iou_one(obj, boxes)
            hit = scores[iou >= match_iou]
            trials.append(
                Trial(
                    image_index=i,
                    group=str(groups[i]),
                    kind=tmpl.kind,
                    source=tmpl.source,
                    box=tuple(float(v) for v in obj),  # type: ignore[arg-type]
                    texture=texture,
                    stratum="unknown",
                    rel_x=float(((obj[0] + obj[2]) / 2) / w),
                    size_px=float(np.sqrt((obj[2] - obj[0]) * (obj[3] - obj[1]))),
                    score=float(hit.max()) if hit.size else 0.0,
                )
            )
    return trials


def with_strata(trials: Sequence[Trial], cuts: tuple[float, float]) -> list[Trial]:
    """Return trials with their texture stratum filled from fixed cut points."""
    from dataclasses import replace

    return [replace(t, stratum=texture_stratum(t.texture, cuts)) for t in trials]


@dataclass(frozen=True)
class CompletenessCell:
    """Pd for one block of one image, from injected reference targets."""

    image_index: int
    row: int
    col: int
    box: tuple[float, float, float, float]
    n_trials: int
    n_detected: int
    pd: float
    pd_lower: float
    status: str  # "ok", "insufficient_trials" or "not_searched"
    # share of the cell the sonar actually searched (netsight.trust.coverage), and the Pd
    # lower bound for an object anywhere in the cell: unsearched area finds nothing
    searched_fraction: float = 1.0
    pd_lower_area: float = float("nan")

    def to_dict(self) -> dict:
        return asdict(self)


def completeness_map(
    images: Sequence[np.ndarray],
    base_predictions: Sequence[tuple[np.ndarray, np.ndarray]],
    predict: Predictor,
    threshold: float,
    *,
    library: Sequence[TargetTemplate],
    rng: np.random.Generator,
    passes: int = 4,
    per_pass: int = 6,
    grid: tuple[int, int] = (3, 3),
    alpha: float = 0.10,
    min_trials: int = 5,
    not_searched: Sequence[np.ndarray] | None = None,
) -> list[CompletenessCell]:
    """Per-image grid of Pd (with one-sided lower bounds) for targets drawn from ``library``.

    Use real objects transplanted from labelled surveys the detector did not train on: simple
    parametric shapes are not detected by a detector trained on real objects (WP6 finding), so
    they would report Pd 0 everywhere. Each pass pastes ``per_pass`` random library targets at
    free seabed places and re-runs the detector once. A target counts as detected when an
    overlapping detection scores at or above the survey's operating ``threshold``. Cells under
    ``min_trials`` are marked insufficient, never filled in. With ``not_searched`` masks (one
    per image), each cell reports its searched fraction; cells under 5% searched are
    "not_searched" with Pd 0, and ``pd_lower_area`` = lower bound x searched fraction.
    """
    from netsight.trust.bounds import one_sided_lower
    from netsight.trust.coverage import NOT_SEARCHED_CELL, searched_fraction

    if not library:
        raise ValueError("library must contain at least one target")
    rows, cols = grid
    out: list[CompletenessCell] = []
    if not_searched is not None and len(not_searched) != len(images):
        raise ValueError("one not_searched mask per image is required")
    for i, image in enumerate(images):
        h, w = image.shape[:2]
        fractions = (
            searched_fraction(np.asarray(not_searched[i], bool), grid)
            if not_searched is not None
            else np.ones(grid)
        )
        counts = np.zeros((rows, cols, 2), int)
        for _p in range(passes):

            def templates(_k: int, r: np.random.Generator) -> list[TargetTemplate]:
                return [library[int(j)] for j in r.integers(len(library), size=per_pass)]

            trials = run_trials(
                [image],
                ["survey"],
                [np.zeros((0, 4))],
                [base_predictions[i]],
                templates,
                predict,
                rng=rng,
            )
            for t in trials:
                cx, cy = (t.box[0] + t.box[2]) / 2, (t.box[1] + t.box[3]) / 2
                r_, c_ = min(int(cy / h * rows), rows - 1), min(int(cx / w * cols), cols - 1)
                counts[r_, c_, 0] += int(t.detected(threshold))
                counts[r_, c_, 1] += 1
        for r_ in range(rows):
            for c_ in range(cols):
                k, n = (int(v) for v in counts[r_, c_])
                frac = float(fractions[r_, c_])
                lower = one_sided_lower(k, n, alpha=alpha) if n else float("nan")
                if frac < NOT_SEARCHED_CELL:
                    status = "not_searched"
                else:
                    status = "ok" if n >= min_trials else "insufficient_trials"
                out.append(
                    CompletenessCell(
                        image_index=i,
                        row=r_,
                        col=c_,
                        box=(
                            c_ * w / cols,
                            r_ * h / rows,
                            (c_ + 1) * w / cols,
                            (r_ + 1) * h / rows,
                        ),
                        n_trials=n,
                        n_detected=k,
                        pd=k / n if n else float("nan"),
                        pd_lower=lower,
                        status=status,
                        searched_fraction=frac,
                        pd_lower_area=(0.0 if status == "not_searched" else lower * frac),
                    )
                )
    return out
