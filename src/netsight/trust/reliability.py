"""Reliability diagram on held-out surveys: NetSight vs raw score (B0) vs temperature (B1).

Plan section 16 item 3. Calibrators are fitted on validation surveys only; every bin is
measured on held-out test surveys, with a Wilson interval on the observed real rate.
"""

from __future__ import annotations

from html import escape
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

METHODS = ("NetSight (beta)", "B1 temperature", "B0 raw score")
COLOURS = {"NetSight (beta)": "#2bb59a", "B1 temperature": "#d9a441", "B0 raw score": "#8a97a6"}


def reliability_comparison(
    val_scores: ArrayLike,
    val_real: ArrayLike,
    test_scores: ArrayLike,
    test_real: ArrayLike,
    calibrator: Any,
    *,
    n_bins: int = 10,
) -> dict[str, Any]:
    """Equal-count bins of each method's probability against the held-out real rate."""
    from netsight.trust.calibration_metrics import (
        brier_score,
        expected_calibration_error,
        reliability_table,
    )
    from netsight.trust.calibrators import TemperatureScaling

    vs = np.asarray(val_scores, float)
    vy = np.asarray(val_real, float)
    ts = np.asarray(test_scores, float)
    ty = np.asarray(test_real, float)
    temperature = TemperatureScaling().fit(vs, vy)
    probabilities = {
        "NetSight (beta)": np.asarray(calibrator.predict(ts), float),
        "B1 temperature": np.asarray(temperature.predict(ts), float),
        "B0 raw score": np.clip(ts, 0, 1),
    }
    methods = {}
    for name in METHODS:
        p = probabilities[name]
        methods[name] = {
            "ece": expected_calibration_error(p, ty),
            "brier": brier_score(p, ty),
            "bins": [
                {
                    "mean_predicted": b.mean_predicted,
                    "observed_rate": b.observed_rate,
                    "ci_low": b.ci_low,
                    "ci_high": b.ci_high,
                    "count": b.count,
                }
                for b in reliability_table(p, ty, n_bins=n_bins, strategy="quantile")
            ],
        }
    return {
        "held_out": "test surveys never used for training or calibration",
        "n_test": int(ts.size),
        "positives_test": int(ty.sum()),
        "methods": methods,
    }


def reliability_svg(result: dict[str, Any], size: int = 320) -> str:
    """Self-contained SVG: diagonal, one line per method, interval whiskers, legend with ECE."""
    pad, plot = 44, size - 64

    def xy(p: float, r: float) -> tuple[float, float]:
        return pad + p * plot, pad - 24 + (1 - r) * plot

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size + 66}" '
        f'width="{size}" height="{size + 66}" role="img" '
        'aria-label="Reliability diagram on held-out surveys" font-family="sans-serif" '
        'font-size="11">',
        f'<rect x="{pad}" y="{pad - 24}" width="{plot}" height="{plot}" fill="none" '
        'stroke="#9aa5b1" stroke-width="1"/>',
    ]
    x0, y0 = xy(0, 0)
    x1, y1 = xy(1, 1)
    parts.append(
        f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="#9aa5b1" '
        'stroke-dasharray="4 3"><title>Perfect calibration</title></line>'
    )
    for tick in (0, 0.5, 1):
        tx, ty = xy(tick, 0)
        parts.append(f'<text x="{tx}" y="{ty + 14}" text-anchor="middle">{tick:g}</text>')
        lx, ly = xy(0, tick)
        parts.append(f'<text x="{lx - 6}" y="{ly + 4}" text-anchor="end">{tick:g}</text>')
    bx, by = xy(0.5, 0)
    parts.append(f'<text x="{bx}" y="{by + 28}" text-anchor="middle">Shown P(real)</text>')
    parts.append(
        f'<text x="12" y="{pad - 24 + plot / 2}" text-anchor="middle" '
        f'transform="rotate(-90 12 {pad - 24 + plot / 2})">Observed real rate</text>'
    )
    for i, name in enumerate(METHODS):
        method = result["methods"][name]
        colour = COLOURS[name]
        points = [xy(b["mean_predicted"], b["observed_rate"]) for b in method["bins"]]
        for b in method["bins"]:
            wx, lo = xy(b["mean_predicted"], b["ci_low"])
            _, hi = xy(b["mean_predicted"], b["ci_high"])
            parts.append(
                f'<line x1="{wx:.1f}" y1="{lo:.1f}" x2="{wx:.1f}" y2="{hi:.1f}" '
                f'stroke="{colour}" stroke-opacity="0.45"/>'
            )
        parts.append(
            f'<polyline fill="none" stroke="{colour}" stroke-width="2" points="'
            + " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
            + f'"><title>{escape(name)}</title></polyline>'
        )
        parts.extend(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.5" fill="{colour}"/>' for px, py in points
        )
        ly = size + 14 + i * 16
        parts.append(
            f'<rect x="{pad}" y="{ly - 9}" width="12" height="3" fill="{colour}"/>'
            f'<text x="{pad + 18}" y="{ly - 5}">{escape(name)}: ECE {method["ece"]:.3f}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)
