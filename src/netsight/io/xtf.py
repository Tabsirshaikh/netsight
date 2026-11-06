"""XTF side-scan reader. Wraps pyxtf (MIT) and contains its known hazards."""

from __future__ import annotations

import math
from collections import Counter
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pyxtf

from netsight.core.hashing import file_sha256
from netsight.core.records import (
    CoordKind,
    Ping,
    Provenance,
    SensorDescriptor,
    SensorType,
    SonarRecord,
)
from netsight.navigation.provenance import select_position

PORT_CHANNEL_TYPE = 1
STBD_CHANNEL_TYPE = 2
LATLON_NAV_UNITS = 3


class UnsafeIndexFileError(RuntimeError):
    """A .pyxtf_idx file would be unpickled by pyxtf (arbitrary code execution)."""


class XtfFormatError(ValueError):
    pass


def _finite_or_nan(value: float) -> float:
    value = float(value)
    return value if math.isfinite(value) else math.nan


def _sound_velocity(raw: float) -> float:
    """XTF writers differ: some store one-way speed (~1500), some half of it (~750)."""
    sv = float(raw)
    if 1300.0 <= sv <= 1700.0:
        return sv
    if 650.0 <= sv <= 850.0:
        return 2.0 * sv
    return 1500.0


def read_xtf(path: str | Path) -> SonarRecord:
    p = Path(path)
    index_file = p.with_suffix(".pyxtf_idx")
    if index_file.exists():
        raise UnsafeIndexFileError(
            f"{index_file} exists; pyxtf would unpickle it. Delete it before reading {p.name}."
        )
    gen = pyxtf.xtf_read_gen(str(p), types=[pyxtf.XTFHeaderType.sonar])
    fh = next(gen)
    n_sonar = int(fh.NumberOfSonarChannels)
    # pyxtf filters sonar_info to sonar-type channels, so it can be shorter than n_sonar
    channel_types = [int(ci.TypeOfChannel) for ci in fh.sonar_info]
    try:
        port_i = channel_types.index(PORT_CHANNEL_TYPE)
        stbd_i = channel_types.index(STBD_CHANNEL_TYPE)
    except ValueError as exc:
        raise XtfFormatError(
            f"no port/starboard side-scan channel pair in {p.name} (channel types {channel_types})"
        ) from exc
    kind = CoordKind.LATLON if int(fh.NavUnits) == LATLON_NAV_UNITS else CoordKind.PROJECTED
    frequency = float(fh.sonar_info[port_i].Frequency) or None
    model = fh.SonarName.decode("ascii", errors="replace").strip("\x00 ") or None

    rows = []
    notes: Counter[str] = Counter()
    for pk in gen:
        if len(pk.data) <= max(port_i, stbd_i):
            notes["ping skipped: missing side-scan channel data"] += 1
            continue
        chans = pk.ping_chan_headers
        slant = float(chans[port_i].SlantRange)
        if not slant > 0:
            notes["ping skipped: non-positive slant range"] += 1
            continue
        port = pk.data[port_i].astype(np.float32)
        stbd = pk.data[stbd_i].astype(np.float32)
        if int(chans[port_i].Weight):
            port *= np.float32(2.0 ** -int(chans[port_i].Weight))
        if int(chans[stbd_i].Weight):
            stbd *= np.float32(2.0 ** -int(chans[stbd_i].Weight))
        if port.size != stbd.size:
            n = min(port.size, stbd.size)
            port, stbd = port[:n], stbd[:n]
            notes["ping truncated: unequal port/starboard sample counts"] += 1
        fix = select_position(
            sensor_x=float(pk.SensorXcoordinate),
            sensor_y=float(pk.SensorYcoordinate),
            ship_x=float(pk.ShipXcoordinate),
            ship_y=float(pk.ShipYcoordinate),
            layback_m=float(pk.Layback),
            heading_deg=float(pk.SensorHeading),
            coord_kind=kind,
        )
        for note in fix.notes:
            notes[note] += 1
        altitude = float(pk.SensorPrimaryAltitude)
        rows.append(
            dict(
                time=pk.get_time(),
                ping_number=int(pk.PingNumber),
                x=fix.x,
                y=fix.y,
                coord_kind=kind if fix.source != "missing" else CoordKind.NONE,
                nav_source=fix.source,
                heading_deg=_finite_or_nan(pk.SensorHeading),
                pitch_deg=_finite_or_nan(pk.SensorPitch),
                roll_deg=_finite_or_nan(pk.SensorRoll),
                altitude_m=altitude if math.isfinite(altitude) and altitude > 0 else math.nan,
                slant_range_m=slant,
                port=port,
                stbd=stbd,
                sound_velocity_ms=_sound_velocity(pk.SoundVelocity),
            )
        )
    rows.sort(key=lambda r: (r["time"], r["ping_number"]))
    pings = [Ping(index=i, **row) for i, row in enumerate(rows)]
    provenance = Provenance(
        source_path=str(p),
        sha256=file_sha256(p),
        reader="netsight.io.xtf",
        reader_version=f"pyxtf {version('pyxtf')}",
        notes=[f"{msg} ({count} pings)" for msg, count in sorted(notes.items())],
    )
    sensor = SensorDescriptor(
        sensor_type=SensorType.SIDESCAN,
        source_format="xtf",
        model=model,
        frequency_khz=frequency,
        n_channels=n_sonar,
    )
    return SonarRecord(sensor=sensor, pings=pings, provenance=provenance)
