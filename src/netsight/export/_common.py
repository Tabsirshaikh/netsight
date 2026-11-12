"""Shared validation and missing-value handling for exports."""

import math
from collections.abc import Mapping
from numbers import Real
from typing import Any


def finite_number(value: Any, name: str) -> float:
    """Return a finite numeric value or raise a descriptive ValueError."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def positive_number(value: Any, name: str) -> float:
    """Return a finite, strictly positive number."""
    result = finite_number(value, name)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def position(contact: Mapping[str, Any]) -> tuple[float, float] | None:
    """Return a geographic position, without inventing missing coordinates."""
    values = (contact.get("lon"), contact.get("lat"))
    missing = False
    for value in values:
        if value is None:
            missing = True
        elif isinstance(value, Real) and math.isnan(float(value)):
            missing = True
        else:
            finite_number(value, "coordinate")
    if missing:
        return None
    lon, lat = (float(value) for value in values)
    if not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise ValueError("coordinates must be within geographic longitude/latitude bounds")
    return lon, lat


def ellipse(value: Any) -> tuple[float, float, float] | None:
    """Return valid ellipse parameters; unavailable or invalid ellipses are omitted."""
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    try:
        major = positive_number(value[0], "semi_major_m")
        minor = positive_number(value[1], "semi_minor_m")
        angle = finite_number(value[2], "orientation_deg")
    except ValueError:
        return None
    if minor > major:
        return None
    return major, minor, angle


def json_safe(value: Any) -> Any:
    """Recursively replace non-finite numbers with JSON null."""
    if isinstance(value, Mapping):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_safe(item) for item in value]
    if isinstance(value, Real) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            return None
    return value


def claim_level(contact: Mapping[str, Any]) -> str:
    """Validate and return a contact's claim level."""
    level = contact.get("claim_level")
    if level not in ("calibrated", "indicative", "withdrawn"):
        raise ValueError("claim_level must be calibrated, indicative, or withdrawn")
    return level


def probability(contact: Mapping[str, Any]) -> float:
    """Validate and return a contact's real-contact probability."""
    value = finite_number(contact.get("p_real"), "p_real")
    if not 0 <= value <= 1:
        raise ValueError("p_real must be between 0 and 1")
    return value
