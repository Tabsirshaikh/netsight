"""Choose a ping position and record where it came from. Never invent positions."""

from __future__ import annotations

import math
from dataclasses import dataclass

from netsight.core.records import CoordKind, NavSource

METRES_PER_DEG_LAT = 111_320.0
NOTE_LAYBACK = (
    "towfish position = vessel position moved back by layback along heading (catenary ignored)"
)
NOTE_SHIP_ONLY = "vessel position only; towfish offset unknown"
NOTE_WITHDRAWN = "no usable position; position withdrawn"


@dataclass(frozen=True)
class PositionFix:
    x: float
    y: float
    source: NavSource
    notes: tuple[str, ...] = ()


def _valid(x: float, y: float, kind: CoordKind) -> bool:
    if not (math.isfinite(x) and math.isfinite(y)):
        return False
    if x == 0.0 and y == 0.0:
        return False
    if kind == CoordKind.LATLON:
        return abs(y) <= 90.0 and abs(x) <= 180.0
    return True


def offset_behind(
    x: float, y: float, distance_m: float, heading_deg: float, kind: CoordKind
) -> tuple[float, float]:
    """Move a point `distance_m` metres opposite to `heading_deg` (degrees clockwise from north)."""
    h = math.radians(heading_deg)
    d_east = -distance_m * math.sin(h)
    d_north = -distance_m * math.cos(h)
    if kind == CoordKind.LATLON:
        dlon = d_east / (METRES_PER_DEG_LAT * math.cos(math.radians(y)))
        return x + dlon, y + d_north / METRES_PER_DEG_LAT
    return x + d_east, y + d_north


def select_position(
    *,
    sensor_x: float,
    sensor_y: float,
    ship_x: float,
    ship_y: float,
    layback_m: float,
    heading_deg: float,
    coord_kind: CoordKind,
) -> PositionFix:
    if _valid(sensor_x, sensor_y, coord_kind):
        return PositionFix(sensor_x, sensor_y, NavSource.SENSOR)
    if _valid(ship_x, ship_y, coord_kind):
        if math.isfinite(layback_m) and layback_m > 0 and math.isfinite(heading_deg):
            x, y = offset_behind(ship_x, ship_y, layback_m, heading_deg, coord_kind)
            return PositionFix(x, y, NavSource.SHIP_LAYBACK, (NOTE_LAYBACK,))
        return PositionFix(ship_x, ship_y, NavSource.SHIP, (NOTE_SHIP_ONLY,))
    return PositionFix(math.nan, math.nan, NavSource.MISSING, (NOTE_WITHDRAWN,))
