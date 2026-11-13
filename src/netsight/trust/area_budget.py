"""False-alarm budget per km2 of searched seabed (plan: FA per km2, not per image).

The label-free count rule flags at most floor(budget x units) detections. With km2 as the unit,
the units are the insonified seabed area of the survey (water column, lost far range and blank
borders excluded by ``coverage.not_searched_mask``), so the budget needs a metric pixel
size for every image.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def searched_area_km2(images: Sequence[np.ndarray], pixel_m: Sequence[float]) -> float:
    """Insonified seabed area of ``images`` in km2, each with its own square pixel size (m)."""
    from netsight.trust.coverage import not_searched_mask

    if len(images) != len(pixel_m) or not images:
        raise ValueError("one pixel size per image is required")
    area = 0.0
    for image, size in zip(images, pixel_m, strict=True):
        if not (np.isfinite(size) and size > 0):
            raise ValueError("pixel size must be a finite number > 0 m")
        searched = ~not_searched_mask(image, waterfall=False)  # georeferenced = mosaic
        area += float(np.count_nonzero(searched)) * size * size
    return area / 1e6


def equivalent_image_budget(budget_per_km2: float, area_km2: float, n_images: int) -> float:
    """Flagged-contact allowance per image implied by a per-km2 budget over ``area_km2``."""
    if n_images <= 0:
        raise ValueError("n_images must be positive")
    return budget_per_km2 * area_km2 / n_images
