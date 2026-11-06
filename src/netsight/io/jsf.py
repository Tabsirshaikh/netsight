"""Minimal EdgeTech JSF side-scan reader, written from JSF Rev 1.8 (doc 990-0000048-1000)."""

from __future__ import annotations

import math
import struct
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from netsight import __version__
from netsight.core.hashing import file_sha256
from netsight.core.records import (
    CoordKind,
    NavSource,
    Ping,
    Provenance,
    SensorDescriptor,
    SensorType,
    SonarRecord,
)

HEADER = struct.Struct("<HBBHBBBBHI")
START_MARKER = 0x1601
MSG_SONAR = 80
MSG_NMEA = 2002
SIDESCAN_SUBSYSTEMS = (20, 21)
SONAR_HEADER_BYTES = 240
NMEA_MAX_GAP_MS = 2000
MAX_START_DEPTH_SAMPLES = 10_000_000
NOTE_MSG80 = (
    "JSF message-80 position is the last navigation fix, not time-interpolated; "
    "towfish offset unknown"
)
NOTE_NMEA = "position from nearest NMEA GGA fix within 2 s; towfish offset unknown"
NOTE_WITHDRAWN = "no usable position; position withdrawn"
NOTE_DUPLICATE = "duplicate sonar message ignored (multi-packet pings unsupported)"


class JsfFormatError(ValueError):
    pass


@dataclass
class _SonarMsg:
    subsystem: int
    channel: int
    ping_number: int
    time: np.datetime64
    start_depth: int
    interval_ns: int
    validity: int
    x_raw: int
    y_raw: int
    coord_units: int
    altitude_mm: int
    heading_raw: int
    pitch_raw: int
    roll_raw: int
    samples: np.ndarray


def _u(fmt: str, body: bytes, offset: int):
    return struct.unpack_from(fmt, body, offset)[0]


def _iter_messages(f):
    offset = 0
    while True:
        head = f.read(HEADER.size)
        if not head:
            return
        if len(head) < HEADER.size:
            raise JsfFormatError(f"truncated message header at byte {offset}")
        marker, _ver, _sess, msg_type, _cmd, subsystem, channel, _seq, _res, size = HEADER.unpack(
            head
        )
        if marker != START_MARKER:
            raise JsfFormatError(f"bad start marker 0x{marker:04x} at byte {offset}")
        body = f.read(size)
        if len(body) < size:
            raise JsfFormatError(f"truncated message body at byte {offset}")
        yield msg_type, subsystem, channel, body
        offset += HEADER.size + size


def _parse_sonar(subsystem: int, channel: int, body: bytes) -> _SonarMsg:
    if len(body) < SONAR_HEADER_BYTES:
        raise JsfFormatError("sonar message shorter than its 240-byte header")
    msbs = _u("<H", body, 16)
    n = _u("<H", body, 114) | (((msbs >> 8) & 0xF) << 16)
    data_format = _u("<h", body, 34)
    payload = memoryview(body)[SONAR_HEADER_BYTES:]
    if data_format == 0:
        # JSF Rev 1.8 (p. 11, bytes 34-35) says only "1 short per sample - Envelope Data".
        # NetSight reads envelope as unsigned 16-bit because envelope is a non-negative
        # magnitude; the independent pyjsf 0.0.1 reader reads it as signed. Confirm against
        # the first real EdgeTech JSF file.
        need = n * 2
        if len(payload) < need:
            raise JsfFormatError("sample data shorter than declared")
        samples = np.frombuffer(payload[:need], dtype="<u2").astype(np.float32)
    elif data_format == 1:
        need = n * 4
        if len(payload) < need:
            raise JsfFormatError("sample data shorter than declared")
        iq = np.frombuffer(payload[:need], dtype="<i2").astype(np.float32).reshape(-1, 2)
        samples = np.hypot(iq[:, 0], iq[:, 1]).astype(np.float32)
    else:
        raise JsfFormatError(f"unsupported JSF data format {data_format}")
    weight = _u("<h", body, 168)
    if weight:
        samples = samples * np.float32(2.0**-weight)
    t = np.datetime64(_u("<i", body, 0), "s").astype("datetime64[ms]")
    t = t + np.timedelta64(_u("<I", body, 200) % 1000, "ms")
    return _SonarMsg(
        subsystem=subsystem,
        channel=channel,
        ping_number=_u("<I", body, 8),
        time=t,
        start_depth=_u("<I", body, 4),
        interval_ns=_u("<I", body, 116),
        validity=_u("<H", body, 30),
        x_raw=_u("<i", body, 80),
        y_raw=_u("<i", body, 84),
        coord_units=_u("<h", body, 88),
        altitude_mm=_u("<i", body, 144),
        heading_raw=_u("<H", body, 172),
        pitch_raw=_u("<h", body, 174),
        roll_raw=_u("<h", body, 176),
        samples=samples,
    )


def _coords(msg: _SonarMsg) -> tuple[float, float, CoordKind] | None:
    if not msg.validity & 0x1:
        return None
    if msg.coord_units == 2:
        return msg.x_raw / 600_000.0, msg.y_raw / 600_000.0, CoordKind.LATLON
    if msg.coord_units == 1:
        return msg.x_raw / 1000.0, msg.y_raw / 1000.0, CoordKind.PROJECTED
    if msg.coord_units == 3:
        return msg.x_raw / 10.0, msg.y_raw / 10.0, CoordKind.PROJECTED
    return None


def _nmea_degrees(field: str, degree_digits: int) -> float:
    return float(field[:degree_digits]) + float(field[degree_digits:]) / 60.0


def _parse_gga(text: str) -> tuple[float, float] | None:
    parts = text.strip().split("*")[0].split(",")
    if len(parts) < 7 or not parts[0].endswith("GGA") or parts[6] in ("", "0"):
        return None
    try:
        lat = _nmea_degrees(parts[2], 2)
        lon = _nmea_degrees(parts[4], 3)
    except ValueError:
        return None
    if parts[3] == "S":
        lat = -lat
    if parts[5] == "W":
        lon = -lon
    return lon, lat


def _with_start_depth(msg: _SonarMsg) -> np.ndarray:
    if msg.start_depth == 0:
        return msg.samples
    if msg.start_depth > MAX_START_DEPTH_SAMPLES:
        raise JsfFormatError(
            f"implausible start depth {msg.start_depth} samples in ping {msg.ping_number}"
        )
    return np.concatenate([np.full(msg.start_depth, np.nan, dtype=np.float32), msg.samples])


def read_jsf(
    path: str | Path, *, subsystem: int | None = None, sound_velocity_ms: float = 1500.0
) -> SonarRecord:
    p = Path(path)
    sonar: list[_SonarMsg] = []
    gga: list[tuple[int, float, float]] = []
    with open(p, "rb") as f:
        for msg_type, subsys, channel, body in _iter_messages(f):
            if msg_type == MSG_SONAR and subsys in SIDESCAN_SUBSYSTEMS and channel in (0, 1):
                sonar.append(_parse_sonar(subsys, channel, body))
            elif msg_type == MSG_NMEA and len(body) > 12:
                fix = _parse_gga(body[12:].decode("ascii", "replace").strip("\x00\r\n "))
                if fix:
                    t_ms = _u("<i", body, 0) * 1000 + _u("<i", body, 4)
                    gga.append((t_ms, fix[0], fix[1]))
    if not sonar:
        raise JsfFormatError(f"no side-scan sonar messages (type 80, subsystem 20/21) in {p.name}")
    notes: Counter[str] = Counter()
    subsystems = sorted({m.subsystem for m in sonar})
    chosen = subsystem if subsystem is not None else subsystems[0]
    if len(subsystems) > 1:
        notes[f"subsystems present {subsystems}; using {chosen}"] += 1
    by_ping: dict[int, dict[int, _SonarMsg]] = {}
    for m in sonar:
        if m.subsystem == chosen:
            sides = by_ping.setdefault(m.ping_number, {})
            if m.channel in sides:
                notes[NOTE_DUPLICATE] += 1
            else:
                sides[m.channel] = m
    gga.sort()
    gga_times = np.array([g[0] for g in gga], dtype=np.int64)

    rows = []
    for ping_number in sorted(by_ping):
        sides = by_ping[ping_number]
        if 0 not in sides or 1 not in sides:
            notes["ping skipped: one side only"] += 1
            continue
        pm, sm = sides[0], sides[1]
        port, stbd = _with_start_depth(pm), _with_start_depth(sm)
        n = min(port.size, stbd.size)
        port, stbd = port[:n], stbd[:n]
        coords = _coords(pm)
        if coords:
            x, y, kind = coords
            source = NavSource.SHIP
            notes[NOTE_MSG80] += 1
        else:
            x = y = math.nan
            kind, source = CoordKind.NONE, NavSource.MISSING
            if gga:
                t_ms = int(pm.time.astype("datetime64[ms]").astype(np.int64))
                j = int(np.argmin(np.abs(gga_times - t_ms)))
                if abs(int(gga_times[j]) - t_ms) <= NMEA_MAX_GAP_MS:
                    x, y = gga[j][1], gga[j][2]
                    kind, source = CoordKind.LATLON, NavSource.SHIP
                    notes[NOTE_NMEA] += 1
            if source == NavSource.MISSING:
                notes[NOTE_WITHDRAWN] += 1
        rows.append(
            dict(
                time=pm.time,
                ping_number=ping_number,
                x=x,
                y=y,
                coord_kind=kind,
                nav_source=source,
                heading_deg=pm.heading_raw / 100.0 if pm.validity & 0x8 else math.nan,
                pitch_deg=pm.pitch_raw * 180.0 / 32768.0 if pm.validity & 0x20 else math.nan,
                roll_deg=pm.roll_raw * 180.0 / 32768.0 if pm.validity & 0x20 else math.nan,
                altitude_m=pm.altitude_mm / 1000.0
                if pm.validity & 0x40 and pm.altitude_mm > 0
                else math.nan,
                slant_range_m=n * pm.interval_ns * 1e-9 * sound_velocity_ms / 2.0,
                port=port,
                stbd=stbd,
                sound_velocity_ms=sound_velocity_ms,
            )
        )
    rows.sort(key=lambda r: (r["time"], r["ping_number"]))
    pings = [Ping(index=i, **row) for i, row in enumerate(rows)]
    provenance = Provenance(
        source_path=str(p),
        sha256=file_sha256(p),
        reader="netsight.io.jsf",
        reader_version=f"netsight {__version__} (JSF Rev 1.8)",
        notes=[f"{msg} ({count} pings)" for msg, count in sorted(notes.items())],
    )
    sensor = SensorDescriptor(SensorType.SIDESCAN, "jsf", model="EdgeTech JSF", n_channels=2)
    return SonarRecord(sensor=sensor, pings=pings, provenance=provenance)
