"""UXO mode (WP16): size attributes, the pick rule and pUXO wording for offshore target lists.

Rules (plan section 8.4 and WP16):
- "cylinder_like" and sizes are attributes, never classes; a contact can only become a
  *pUXO candidate* (potential UXO), never an identified UXO.
- Pick rule: longest horizontal dimension >= ``min_pick_size_m`` (default 1.0 m), or a
  magnetometer anomaly.
- Boulders are rank-only: kept and ranked, never promoted by size alone; only a magnetometer
  anomaly promotes them.
- Unknown size without a magnetometer flag is "not assessable", never dropped.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

from netsight.trust.wording import check_wording

STATUS_ORDER = ("pUXO_candidate", "not_assessable", "rank_only", "below_pick_size")
BOULDER_CLASSES = {"rock_boulder"}
BOULDER_SEABEDS = {"boulder_field"}


def _clean(value: float | None, name: str) -> float | None:
    if value is None:
        return None
    v = float(value)
    if math.isnan(v):
        return None
    if v < 0 or math.isinf(v):
        raise ValueError(f"{name} must be a finite, non-negative number")
    return v


@dataclass(frozen=True)
class UxoAttributes:
    length_m: float | None
    width_m: float | None
    height_m: float | None
    aspect: float | None
    cylinder_like: bool | None
    mag_anomaly: bool | None


def uxo_attributes(
    length_m: float | None,
    width_m: float | None,
    height_m: float | None = None,
    mag_anomaly: bool | None = None,
) -> UxoAttributes:
    """Size attributes; length is the longer horizontal side (swapped if needed)."""
    length, width = _clean(length_m, "length_m"), _clean(width_m, "width_m")
    if length is not None and width is not None and width > length:
        length, width = width, length
    aspect = length / width if length is not None and width else None
    return UxoAttributes(
        length_m=length,
        width_m=width,
        height_m=_clean(height_m, "height_m"),
        aspect=aspect,
        cylinder_like=None if aspect is None else aspect >= 2.0,
        mag_anomaly=mag_anomaly,
    )


@dataclass(frozen=True)
class UxoAssessment:
    status: str
    reasons: tuple[str, ...]
    rank_only: bool
    statement: str


def assess_uxo(
    attrs: UxoAttributes,
    *,
    contact_class: str = "unknown",
    seabed_class: str | None = None,
    min_pick_size_m: float = 1.0,
) -> UxoAssessment:
    """Apply the pick rule in priority order: magnetometer, boulder, unknown size, size."""
    if not math.isfinite(min_pick_size_m) or min_pick_size_m <= 0:
        raise ValueError("min_pick_size_m must be positive")
    boulder = contact_class in BOULDER_CLASSES or seabed_class in BOULDER_SEABEDS
    if attrs.mag_anomaly:
        reasons = ("magnetometer anomaly",) + (("boulder setting",) if boulder else ())
        status = "pUXO_candidate"
        statement = "pUXO candidate: a magnetometer anomaly is recorded at this contact."
    elif boulder:
        reasons = ("boulder class or boulder field; size alone cannot promote",)
        status = "rank_only"
        statement = "Rank only: boulder setting, kept in the list but not a pUXO candidate by size."
    elif attrs.length_m is None:
        reasons = ("size not measured",)
        status = "not_assessable"
        statement = "Not assessable: size could not be measured; the contact stays in the list."
    elif attrs.length_m >= min_pick_size_m:
        reasons = (f"length {attrs.length_m:.2f} m >= pick size {min_pick_size_m:.2f} m",)
        status = "pUXO_candidate"
        statement = (
            f"pUXO candidate by the {min_pick_size_m:.1f} m pick rule; identity is not established."
        )
    else:
        reasons = (f"length {attrs.length_m:.2f} m < pick size {min_pick_size_m:.2f} m",)
        status = "below_pick_size"
        statement = "Below the pick size; recorded and ranked, not a pUXO candidate."
    if check_wording(statement):
        raise AssertionError(f"banned wording in UXO statement: {statement}")
    return UxoAssessment(status, reasons, status == "rank_only", statement)


def uxo_target_list(contacts: Sequence[Mapping], **kw: float) -> list[dict]:
    """Assess and order contacts: pUXO by P(real), then not assessable, rank only, below size."""
    rows = []
    for c in contacts:
        attrs = uxo_attributes(
            c.get("length_m"), c.get("width_m"), c.get("height_m"), c.get("mag_anomaly")
        )
        a = assess_uxo(
            attrs,
            contact_class=c.get("contact_class", "unknown"),
            seabed_class=c.get("seabed_class"),
            **kw,
        )
        rows.append(
            {
                "contact_id": c["contact_id"],
                "p_real": float(c.get("p_real", float("nan"))),
                **asdict(attrs),
                "status": a.status,
                "reasons": list(a.reasons),
                "rank_only": a.rank_only,
                "statement": a.statement,
            }
        )

    def key(r: dict) -> tuple:
        p = r["p_real"]
        return (STATUS_ORDER.index(r["status"]), -(p if math.isfinite(p) else -1), r["contact_id"])

    return sorted(rows, key=key)
