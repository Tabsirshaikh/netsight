"""Verification rankings and bounding rectangles for re-survey priorities."""

import math
from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np
from scipy.ndimage import label

from ._common import claim_level, finite_number, position, positive_number, probability
from .raster import _grid


def verification_plan(contacts: Iterable[Mapping[str, Any]], *, top_n: int = 20) -> dict[str, Any]:
    """Rank eligible contacts; totals include unpositioned non-withdrawn contacts.

    Exclusion counts are independent: a withdrawn, unpositioned contact
    contributes to both counts. A tie in probabilities is broken by contact ID.
    """
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 0:
        raise ValueError("top_n must be a nonnegative integer")
    eligible = []
    probabilities = []
    withdrawn = no_position = 0
    for contact in contacts:
        level = claim_level(contact)
        pos = position(contact)
        withdrawn += level == "withdrawn"
        no_position += pos is None
        if level == "withdrawn":
            continue
        p_real = probability(contact)
        probabilities.append(p_real)
        if pos is not None:
            eligible.append((contact, pos, p_real))
    eligible.sort(key=lambda item: (-item[2], item[0]["contact_id"]))
    entries = []
    cumulative = []
    for rank, (contact, pos, p_real) in enumerate(eligible[:top_n], start=1):
        cumulative.append(p_real)
        entries.append(
            {
                "rank": rank,
                "contact_id": contact["contact_id"],
                "lon": pos[0],
                "lat": pos[1],
                "p_real": p_real,
                "ellipse95": contact.get("ellipse95"),
                "claim_level": contact["claim_level"],
                "cumulative_expected_real": math.fsum(cumulative),
            }
        )
    return {
        "entries": entries,
        "expected_real_total": math.fsum(probabilities),
        "excluded_withdrawn": withdrawn,
        "excluded_no_position": no_position,
        "note": (
            "Expected real finds are the sum of calibrated probabilities; "
            "they assume the calibration holds on this survey."
        ),
    }


def resurvey_regions(
    pd_grid_north_up: np.ndarray,
    *,
    origin_ul_x: float,
    origin_ul_y: float,
    cell_size_m: float,
    threshold: float,
) -> list[dict[str, Any]]:
    """Return 8-connected region bounding rectangles, not exact cell outlines.

    Area counts selected cells only, not the bounding rectangle. A strict
    majority of missing cells selects the ``not_searched`` reason; ties do not.
    Equal-area regions are ordered north-to-south, then west-to-east.
    """
    grid = _grid(pd_grid_north_up)
    x = finite_number(origin_ul_x, "origin_ul_x")
    y = finite_number(origin_ul_y, "origin_ul_y")
    size = positive_number(cell_size_m, "cell_size_m")
    cutoff = finite_number(threshold, "threshold")
    missing = np.isnan(grid)
    labels, count = label(missing | (grid < cutoff), structure=np.ones((3, 3), dtype=int))
    regions = []
    for index in range(1, count + 1):
        rows, columns = np.where(labels == index)
        cells = len(rows)
        left, right = x + columns.min() * size, x + (columns.max() + 1) * size
        top, bottom = y - rows.min() * size, y - (rows.max() + 1) * size
        values = grid[rows, columns]
        finite = values[~np.isnan(values)]
        regions.append(
            {
                "ring": [
                    (float(left), float(top)),
                    (float(left), float(bottom)),
                    (float(right), float(bottom)),
                    (float(right), float(top)),
                    (float(left), float(top)),
                ],
                "cells": cells,
                "area_m2": cells * size**2,
                "reason": (
                    "not_searched"
                    if np.count_nonzero(np.isnan(values)) > cells / 2
                    else "pd_below_threshold"
                ),
                "min_pd": float(finite.min()) if finite.size else float("nan"),
            }
        )
    regions.sort(
        key=lambda region: (-region["area_m2"], -region["ring"][0][1], region["ring"][0][0])
    )
    return regions
