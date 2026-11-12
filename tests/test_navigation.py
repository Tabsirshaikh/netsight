import math

import pytest

from netsight.core.records import CoordKind, NavSource
from netsight.navigation.provenance import (
    NOTE_LAYBACK,
    NOTE_SHIP_ONLY,
    NOTE_WITHDRAWN,
    offset_behind,
    select_position,
)

BASE = dict(sensor_x=0.0, sensor_y=0.0, ship_x=0.0, ship_y=0.0, layback_m=0.0, heading_deg=0.0)


def test_sensor_position_preferred():
    fix = select_position(
        **{**BASE, "sensor_x": 72.8, "sensor_y": 18.9, "ship_x": 72.9, "ship_y": 19.0},
        coord_kind=CoordKind.LATLON,
    )
    assert (fix.x, fix.y, fix.source) == (72.8, 18.9, NavSource.SENSOR)
    assert fix.notes == ()


def test_ship_with_layback_moves_position_behind_heading():
    fix = select_position(
        **{**BASE, "ship_x": 0.0, "ship_y": 10.0, "layback_m": 100.0, "heading_deg": 0.0},
        coord_kind=CoordKind.LATLON,
    )
    assert fix.source == NavSource.SHIP_LAYBACK
    assert fix.y == pytest.approx(10.0 - 100.0 / 111_320.0)
    assert fix.x == pytest.approx(0.0)
    assert NOTE_LAYBACK in fix.notes


def test_ship_without_layback_is_flagged():
    fix = select_position(**{**BASE, "ship_x": 72.8, "ship_y": 18.9}, coord_kind=CoordKind.LATLON)
    assert fix.source == NavSource.SHIP
    assert NOTE_SHIP_ONLY in fix.notes


def test_missing_position_is_withdrawn_not_defaulted():
    fix = select_position(**BASE, coord_kind=CoordKind.LATLON)
    assert fix.source == NavSource.MISSING
    assert math.isnan(fix.x) and math.isnan(fix.y)
    assert NOTE_WITHDRAWN in fix.notes


def test_out_of_range_latlon_is_invalid():
    fix = select_position(
        **{**BASE, "sensor_x": 500.0, "sensor_y": 18.9}, coord_kind=CoordKind.LATLON
    )
    assert fix.source == NavSource.MISSING


def test_projected_offset_in_metres():
    x, y = offset_behind(1000.0, 2000.0, 10.0, 90.0, CoordKind.PROJECTED)
    assert x == pytest.approx(990.0)
    assert y == pytest.approx(2000.0)
